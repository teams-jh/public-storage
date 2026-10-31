"""Ctrl+D로 현재 업로드 프로세스와 브라우저를 종료해요."""

import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys
from threading import Event, Lock, Thread


class BulkUploadControl:
    def __init__(self, settings):
        self.settings = settings["skip_hotkey"]
        self.completion_wait = settings["youtube_completion_wait_seconds"]
        self.skip = Event()
        self.ready = Event()
        self.lock = Lock()
        self.active = False
        self.error = None
        self.thread_id = None

    def request_skip(self):
        with self.lock:
            if self.active:
                self.skip.set()

    def _watch(self):
        from config import UPLOAD_PAUSE_HOTKEY_MESSAGE, UPLOAD_PAUSE_QUIT_MESSAGE

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        registered = False
        try:
            self.thread_id = ctypes.WinDLL("kernel32").GetCurrentThreadId()
            registered = bool(user32.RegisterHotKey(None, self.settings["id"], self.settings["modifiers"], self.settings["virtual_key"]))
            if not registered:
                raise ctypes.WinError(ctypes.get_last_error())
            self.ready.set()
            message = wintypes.MSG()
            while True:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result <= 0 or message.message == UPLOAD_PAUSE_QUIT_MESSAGE:
                    break
                if message.message == UPLOAD_PAUSE_HOTKEY_MESSAGE and message.wParam == self.settings["id"]:
                    self.request_skip()
        except Exception as error:
            self.error = error
            self.ready.set()
        finally:
            if registered:
                user32.UnregisterHotKey(None, self.settings["id"])

    def __enter__(self):
        if sys.platform != "win32":
            raise RuntimeError("Ctrl+D 건너뛰기는 Windows에서 사용할 수 있어요.")
        self.thread = Thread(target=self._watch, daemon=True)
        self.thread.start()
        self.ready.wait()
        if self.error:
            self.thread.join()
            raise RuntimeError(f"Ctrl+D 단축키를 등록하지 못했어요: {self.error}")
        print("업로드 중 Ctrl+D: 현재 업로드 종료 후 다음 파일 / ESC: 일시정지·재개", flush=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        from config import UPLOAD_PAUSE_QUIT_MESSAGE

        ctypes.WinDLL("user32").PostThreadMessageW(self.thread_id, UPLOAD_PAUSE_QUIT_MESSAGE, 0, 0)
        self.thread.join()

    def _stop(self, process):
        """이 실행에서 만든 자식 프로세스의 트리만 종료해요."""
        if process.poll() is None:
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if result.returncode and process.poll() is None:
                raise RuntimeError("현재 업로드를 종료하지 못했어요. 브라우저를 확인해 주세요.")
        process.wait()

    def run(self, platform, path, metadata):
        """성공은 True, 실패는 False, 사용자 건너뛰기는 None을 반환해요."""
        import json

        payload = dict(metadata)
        payload.pop("scheduled_at", None)
        command = [sys.executable, "-u", "-B", str(Path(__file__).with_name("bulk_upload_worker.py")),
                   platform, str(path.resolve()), str(self.completion_wait), json.dumps(payload, ensure_ascii=True)]
        process = subprocess.Popen(command)
        with self.lock:
            self.skip.clear()
            self.active = True
        try:
            while True:
                if self.skip.is_set():
                    self._stop(process)
                    return None
                try:
                    return process.wait(timeout=self.settings["poll_seconds"]) == 0
                except subprocess.TimeoutExpired:
                    pass
        finally:
            with self.lock:
                self.active = False
                self.skip.clear()
            if process.poll() is None:
                self._stop(process)
