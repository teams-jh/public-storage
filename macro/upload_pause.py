"""Windows 전역 ESC 단축키로 업로드 자동화를 일시정지하거나 재개합니다."""

import ctypes
from ctypes import wintypes
from functools import wraps
import os
from pathlib import Path
import sys
from threading import Event, Lock, Thread
import time

from config import (
    UPLOAD_PAUSE_HOTKEY_ID,
    UPLOAD_PAUSE_HOTKEY_MESSAGE,
    UPLOAD_PAUSE_NO_REPEAT_FLAG,
    UPLOAD_PAUSE_QUIT_MESSAGE,
    UPLOAD_PAUSE_VIRTUAL_KEY,
)


class _Message(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("lPrivate", wintypes.DWORD),
    ]


_active_controller = None


def upload_monotonic():
    """일시정지 시간을 뺀 업로드용 경과 시각을 반환합니다."""
    controller = _active_controller
    return time.monotonic() - controller.paused_seconds() if controller else time.monotonic()


def upload_time():
    """일시정지 시간을 뺀 업로드용 현재 시각을 반환합니다."""
    controller = _active_controller
    return time.time() - controller.paused_seconds() if controller else time.time()


class EscapePause:
    """메인 스레드의 다음 Python 실행 지점에서 멈추고 ESC로 다시 깨웁니다."""

    def __init__(self):
        self._running = Event()
        self._running.set()
        self._lock = Lock()
        self._paused_at = None
        self._paused_total = 0.0
        self._ready = Event()
        self._error = None
        self._thread_id = None
        self._thread = None
        self._previous_trace = None
        self._macro_root = os.path.normcase(str(Path(__file__).resolve().parent)) + os.sep
        self._own_file = os.path.normcase(os.path.abspath(__file__))

    def _toggle(self):
        with self._lock:
            if self._running.is_set():
                self._paused_at = time.monotonic()
                self._running.clear()
                message = "업로드를 잠시 멈췄어요. 다시 ESC를 누르면 이어서 진행해요."
            else:
                self._paused_total += time.monotonic() - self._paused_at
                self._paused_at = None
                self._running.set()
                message = "업로드를 다시 진행해요."
        print(message, flush=True)

    def paused_seconds(self):
        with self._lock:
            current_pause = time.monotonic() - self._paused_at if self._paused_at is not None else 0.0
            return self._paused_total + current_pause

    def _watch_hotkey(self):
        registered = False
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._thread_id = kernel32.GetCurrentThreadId()
            registered = bool(user32.RegisterHotKey(
                None, UPLOAD_PAUSE_HOTKEY_ID, UPLOAD_PAUSE_NO_REPEAT_FLAG, UPLOAD_PAUSE_VIRTUAL_KEY
            ))
            if not registered:
                raise ctypes.WinError(ctypes.get_last_error())
            self._ready.set()
            message = _Message()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == UPLOAD_PAUSE_HOTKEY_MESSAGE:
                    self._toggle()
        except Exception as error:
            self._error = error
            self._ready.set()
        finally:
            if registered:
                user32.UnregisterHotKey(None, UPLOAD_PAUSE_HOTKEY_ID)

    def _trace(self, frame, event, arg):
        if event == "call":
            filename = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
            if not filename.startswith(self._macro_root) or filename == self._own_file:
                return None
        elif event == "line":
            self._running.wait()
        return self._trace

    def __enter__(self):
        global _active_controller
        if sys.platform != "win32":
            raise RuntimeError("ESC 일시정지는 Windows에서만 사용할 수 있어요.")
        self._thread = Thread(target=self._watch_hotkey, daemon=True)
        self._thread.start()
        self._ready.wait()
        if self._error is not None:
            raise RuntimeError(f"ESC 단축키를 등록하지 못했어요: {self._error}") from self._error
        _active_controller = self
        self._previous_trace = sys.gettrace()
        sys.settrace(self._trace)
        print("업로드 중 ESC: 일시정지 / 다시 ESC: 재개", flush=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        global _active_controller
        sys.settrace(self._previous_trace)
        self._running.set()
        _active_controller = None
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.PostThreadMessageW(self._thread_id, UPLOAD_PAUSE_QUIT_MESSAGE, 0, 0)
        self._thread.join()


def pause_on_escape(function):
    """업로드 진입점을 ESC 일시정지 범위로 감쌉니다."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        with EscapePause():
            return function(*args, **kwargs)

    return wrapped
