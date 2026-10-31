"""게시물 연결, 계정 격리, 업로드 중단과 유튜브 대기를 검증해요."""

from contextlib import redirect_stdout
import io
from datetime import datetime, timedelta
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import auto_bulk_upload as bulk


class BulkUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input_file = self.root / "input.txt"
        self.settings = bulk.load_settings()
        self.log = io.StringIO()
        self.output = redirect_stdout(self.log)
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def prepare(self, names=("2.mp4", "1.mp4"), text=None):
        for name in names:
            (self.root / name).touch()
        if text is None:
            text = "\n---\n".join(
                f"[TITLE]\n{title}\n[CONTENT]\nline one\nline two\n[TAGS]\n#tag\n[RATIO]\n1:1\n[TIME]\n"
                for title in ("first", "second")
            )
        self.input_file.write_text(text, encoding="utf-8-sig")
        return bulk.build_upload_plan(self.input_file, self.root, self.settings)

    def test_natural_order_and_metadata(self):
        plan = self.prepare(("10.mp4", "2.JPG", "ignore.txt"))
        self.assertEqual([p.name for p, _ in plan], ["2.JPG", "10.mp4"])
        self.assertEqual([m["title"] for _, m in plan], ["first", "second"])
        self.assertEqual(plan[0][1]["full_caption"], "first\n\nline one\nline two\n\n#tag")
        self.assertEqual(plan[0][1]["ratio"], "1:1")
        self.assertIsNone(plan[0][1]["scheduled_at"])

    def test_less_than_two_media_rejected(self):
        with self.assertRaisesRegex(ValueError, "2개 이상"):
            self.prepare(("1.mp4",))

    def test_count_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "개수를 맞춰"):
            self.prepare(text="[TITLE]\nonly one")

    def test_missing_separator_rejected(self):
        with self.assertRaises(ValueError):
            self.prepare(text="[TITLE]\none\n[TITLE]\ntwo")

    def test_invalid_and_past_time_rejected(self):
        for value in ("bad date", "2000-01-01 00:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.prepare(text=f"[TITLE]\none\n[TIME]\n{value}\n---\n[TITLE]\ntwo")

    @patch.object(bulk.time, "sleep")
    def test_youtube_interval_and_internal_wait(self, sleep):
        plan = self.prepare()
        uploader = Mock()
        uploader.upload.return_value = True
        factory = Mock(return_value=uploader)
        self.assertTrue(bulk.upload_plan(plan, ["youtube"], {"youtube": factory}, self.settings))
        factory.assert_called_once_with(completion_wait_seconds=0, post_submit_wait_seconds=10)
        self.assertEqual(uploader.upload.call_count, 2)
        sleep.assert_not_called()

    @patch.object(bulk.time, "sleep")
    def test_failure_continues_to_next_file_and_lists_both(self, sleep):
        plan = self.prepare()
        uploader = Mock()
        uploader.upload.return_value = False
        self.assertFalse(bulk.upload_plan(plan, ["youtube"], {"youtube": Mock(return_value=uploader)}, self.settings))
        self.assertEqual(uploader.upload.call_count, 2)
        summary = self.log.getvalue().split("실패한 업로드 목록이에요.")[1]
        self.assertIn("[youtube] 1.mp4 | 제목: first", summary)
        self.assertIn("[youtube] 2.mp4 | 제목: second", summary)
        sleep.assert_not_called()

    def test_images_skipped_for_video_platform(self):
        plan = self.prepare(("1.jpg", "2.png"))
        factory = Mock()
        self.assertTrue(bulk.upload_plan(plan, ["youtube", "naver", "facebook"], {}, self.settings))
        factory.assert_not_called()

    @patch.object(bulk.time, "sleep")
    def test_ctrl_d_skip_continues_without_youtube_delay(self, sleep):
        plan = self.prepare()
        runner = Mock(side_effect=[None, True])
        self.assertTrue(bulk.upload_plan(plan, ["youtube"], {}, self.settings, runner=runner))
        self.assertEqual([call.args[1].name for call in runner.call_args_list], ["1.mp4", "2.mp4"])
        sleep.assert_not_called()

    def test_skip_last_file_continues_to_next_platform(self):
        plan = self.prepare()
        runner = Mock(side_effect=[True, None, True, True])
        self.assertTrue(bulk.upload_plan(plan, ["instagram", "threads"], {}, self.settings, runner=runner))
        self.assertEqual([call.args[0] for call in runner.call_args_list], ["instagram", "instagram", "threads", "threads"])

    def test_worker_failures_continue_through_all_platforms(self):
        runner = Mock(return_value=False)
        self.assertFalse(bulk.upload_plan(self.prepare(), ["instagram", "threads"], {}, self.settings, runner=runner))
        self.assertEqual(runner.call_count, 4)
        summary = self.log.getvalue().split("실패한 업로드 목록이에요.")[1]
        for platform in ("instagram", "threads"):
            for filename in ("1.mp4", "2.mp4"):
                self.assertIn(f"[{platform}] {filename}", summary)

    def test_exception_and_skip_do_not_prevent_later_success(self):
        runner = Mock(side_effect=[ValueError("browser error"), None, True, True])
        self.assertFalse(bulk.upload_plan(self.prepare(), ["instagram", "threads"], {}, self.settings, runner=runner))
        self.assertEqual(runner.call_count, 4)
        output = self.log.getvalue()
        self.assertIn("완료 2개 / 실패 1개 / 사용자 건너뛰기 1개", output)
        failure_summary, skip_summary = output.split("실패한 업로드 목록이에요.")[1].split("Ctrl+D로 건너뛴 업로드 목록이에요.")
        self.assertIn("[instagram] 1.mp4 | 제목: first | 이유: browser error", failure_summary)
        self.assertNotIn("2.mp4", failure_summary)
        self.assertIn("[instagram] 2.mp4 | 제목: second", skip_summary)

    def test_expired_schedule_continues_to_next_file(self):
        plan = self.prepare()
        plan[0][1]["scheduled_at"] = datetime.now() - timedelta(seconds=1)
        runner = Mock(return_value=True)
        self.assertFalse(bulk.upload_plan(plan, ["instagram"], {}, self.settings, runner=runner))
        runner.assert_called_once()
        self.assertEqual(runner.call_args.args[1].name, "2.mp4")
        summary = self.log.getvalue().split("실패한 업로드 목록이에요.")[1]
        self.assertIn("[instagram] 1.mp4", summary)
        self.assertIn("예약 시각이 지났어요", summary)

    def test_uploader_initialization_failure_continues(self):
        uploader = Mock()
        uploader.upload.return_value = True
        factory = Mock(side_effect=[RuntimeError("initialization error"), uploader])
        self.assertFalse(bulk.upload_plan(self.prepare(), ["instagram"], {"instagram": factory}, self.settings))
        self.assertEqual(factory.call_count, 2)
        self.assertEqual(uploader.upload.call_args.args[0].name, "2.mp4")
        self.assertIn("initialization error", self.log.getvalue().split("실패한 업로드 목록이에요.")[1])

    def test_second_account_paths_and_flags(self):
        with patch.dict(os.environ, {}, clear=True):
            input_file, directory = bulk.configure_account("second", self.settings)
            self.assertEqual(input_file.name, "input_bulk2.txt")
            self.assertEqual(directory.name, "upload2")
            self.assertEqual(Path(os.environ["MACRO_SESSION_DIR"]).name, "sessions2")
            self.assertEqual(Path(os.environ["MACRO_SCREENSHOT_DIR"]).name, "screenshot2")
            self.assertEqual(os.environ["MACRO_FORCE_BROWSER_UPLOAD"], "1")
            self.assertEqual(os.environ["MACRO_DISABLE_AUTO_LOGIN"], "1")


if __name__ == "__main__":
    unittest.main()
