"""실제 게시 없이 Ctrl+D의 범위와 자식 프로세스 종료를 검증해요."""

import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from auto_bulk_upload import load_settings
from bulk_upload_control import BulkUploadControl


class BulkControlTests(unittest.TestCase):
    def setUp(self):
        self.control = BulkUploadControl(load_settings())

    def test_idle_key_does_not_skip_next_upload(self):
        self.control.request_skip()
        self.assertFalse(self.control.skip.is_set())
        self.control.active = True
        self.control.request_skip()
        self.assertTrue(self.control.skip.is_set())

    def test_skip_stops_worker_and_returns_skip_status(self):
        from pathlib import Path

        process = Mock()
        process.poll.return_value = None
        def wait(timeout=None):
            if timeout is not None:
                self.control.request_skip()
                raise subprocess.TimeoutExpired("worker", timeout)
            return 1
        process.wait.side_effect = wait
        with patch("bulk_upload_control.subprocess.Popen", return_value=process), patch.object(self.control, "_stop") as stop:
            self.assertIsNone(self.control.run("youtube", Path("1.mp4"), {"time": "", "scheduled_at": None}))
        self.assertTrue(stop.called)
        self.assertFalse(self.control.active)
        self.assertFalse(self.control.skip.is_set())

    def test_worker_failure_is_not_treated_as_user_skip(self):
        from pathlib import Path

        process = Mock()
        process.wait.return_value = 1
        process.poll.return_value = 1
        with patch("bulk_upload_control.subprocess.Popen", return_value=process), patch.object(self.control, "_stop") as stop:
            self.assertFalse(self.control.run("threads", Path("1.mp4"), {"time": ""}))
        stop.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "Windows process tree termination")
    def test_stop_terminates_real_worker(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            self.control._stop(process)
            self.assertIsNotNone(process.poll())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_stop_does_not_kill_already_finished_worker(self):
        process = Mock()
        process.poll.return_value = 0
        with patch("bulk_upload_control.subprocess.run") as kill:
            self.control._stop(process)
        kill.assert_not_called()
        process.wait.assert_called_once()

    @unittest.skipUnless(sys.platform == "win32", "Windows hotkey registration")
    def test_global_hotkey_registers_and_unregisters(self):
        # Register the real hotkey only for this brief context; no keys are sent.
        with self.control:
            self.assertIsNotNone(self.control.thread_id)
        self.assertFalse(self.control.thread.is_alive())


if __name__ == "__main__":
    unittest.main()
