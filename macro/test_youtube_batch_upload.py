"""브라우저와 네트워크 없이 일괄 업로드의 연결·중단 조건을 검증해요."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import youtube_batch_upload as batch
import youtube_batch_upload2 as batch2


class YouTubeBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = batch.load_settings()
        self.input_file = self.root / self.settings["input_file"]
        self.videos = self.root / self.settings["upload_directory"]
        self.videos.mkdir()
        sleep_patch = patch.object(batch.time, "sleep")
        self.sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def prepare(self, text, names=("1.mp4",)):
        self.input_file.write_text(text, encoding="utf-8-sig")
        for name in names:
            (self.videos / name).touch()

    def plan(self):
        return batch.build_upload_plan(self.input_file, self.videos, self.settings)

    def entry(self, title="제목", time=""):
        return f"[TITLE]\n{title}\n[CONTENT]\n본문 첫 줄\n본문 둘째 줄\n[TIME]\n{time}\n"

    def test_natural_order_and_multiline_metadata(self):
        future = (datetime.now() + timedelta(days=1)).strftime(self.settings["time_format"])
        self.prepare(
            "\n---\n".join(self.entry(title, future) for title in ("첫째", "둘째", "셋째")),
            ("10.mp4", "2.MP4", "1.mp4", "ignore.txt"),
        )
        (self.videos / "nested.mp4").mkdir()
        plan = self.plan()
        self.assertEqual([path.name for path, _ in plan], ["1.mp4", "2.MP4", "10.mp4"])
        self.assertEqual([item["title"] for _, item in plan], ["첫째", "둘째", "셋째"])
        self.assertEqual(plan[0][1]["content"], "본문 첫 줄\n본문 둘째 줄")
        self.assertEqual(plan[0][1]["scheduled_at"], datetime.strptime(future, self.settings["time_format"]))

    def test_each_section_count_must_match(self):
        for section in self.settings["sections"]:
            with self.subTest(section=section):
                self.prepare(self.entry().replace(section, ""))
                with self.assertRaisesRegex(ValueError, "파일 개수가 달라요"):
                    self.plan()

    def test_extra_video_rejected(self):
        self.prepare(self.entry(), ("1.mp4", "2.mp4"))
        with self.assertRaisesRegex(ValueError, "MP4 2개"):
            self.plan()

    def test_empty_input_and_folder_rejected(self):
        self.prepare("", ())
        with self.assertRaisesRegex(ValueError, "MP4가 없어요"):
            self.plan()

    def test_equal_counts_with_wrong_order_rejected(self):
        self.prepare("[CONTENT]\n본문\n[TITLE]\n제목\n[TIME]\n")
        with self.assertRaisesRegex(ValueError, "태그 순서"):
            self.plan()

    def test_blank_title_rejected(self):
        self.prepare(self.entry(title=""))
        with self.assertRaisesRegex(ValueError, "제목을 적어"):
            self.plan()

    def test_invalid_or_past_time_rejected(self):
        for time in ("잘못된 시간", "2026-99-01 20:30", "2000-01-01 20:30"):
            with self.subTest(time=time):
                self.prepare(self.entry(time=time))
                with self.assertRaises(ValueError):
                    self.plan()

    def test_without_separators_and_empty_time(self):
        self.prepare(self.entry("첫째") + self.entry("둘째"), ("1.mp4", "2.mp4"))
        self.assertEqual(len(self.plan()), 2)
        self.assertIsNone(self.plan()[0][1]["scheduled_at"])

    def test_uploads_in_order_and_stops_on_failure_or_exception(self):
        self.prepare(self.entry() * 3, ("1.mp4", "2.mp4", "3.mp4"))
        plan = self.plan()
        for results in ([True, False, False], [True, RuntimeError("연결 오류"), RuntimeError("연결 오류")]):
            self.sleep.reset_mock()
            uploader = Mock()
            uploader.upload.side_effect = results
            with redirect_stdout(io.StringIO()):
                self.assertFalse(batch.upload_plan(plan, uploader))
            self.assertEqual([call.args[0].name for call in uploader.upload.call_args_list], ["1.mp4", "2.mp4", "2.mp4"])
            self.sleep.assert_called_once_with(20)

    def test_retry_success_continues_to_next_video(self):
        self.prepare(self.entry() * 2, ("1.mp4", "2.mp4"))
        uploader = Mock()
        uploader.upload.side_effect = [False, True, True]
        with redirect_stdout(io.StringIO()):
            self.assertTrue(batch.upload_plan(self.plan(), uploader))
        self.assertEqual([call.args[0].name for call in uploader.upload.call_args_list], ["1.mp4", "1.mp4", "2.mp4"])
        self.sleep.assert_called_once_with(20)

    def test_time_expires_during_retry_wait(self):
        self.prepare(self.entry())
        plan = self.plan()
        plan[0][1]["scheduled_at"] = datetime.now() + timedelta(minutes=1)
        self.sleep.side_effect = lambda delay: plan[0][1].update(
            scheduled_at=datetime.now() - timedelta(minutes=1)
        )
        uploader = Mock()
        uploader.upload.return_value = False
        with redirect_stdout(io.StringIO()):
            self.assertFalse(batch.upload_plan(plan, uploader))
        uploader.upload.assert_called_once()
        self.sleep.assert_called_once_with(20)

    def test_success_processes_every_video(self):
        self.prepare(self.entry() * 2, ("1.mp4", "2.mp4"))
        uploader = Mock()
        uploader.upload.return_value = True
        with redirect_stdout(io.StringIO()):
            self.assertTrue(batch.upload_plan(self.plan(), uploader))
        self.assertEqual(uploader.upload.call_count, 2)
        self.sleep.assert_not_called()

    def test_time_expires_before_next_upload(self):
        self.prepare(self.entry())
        plan = self.plan()
        plan[0][1]["scheduled_at"] = datetime.now() - timedelta(minutes=1)
        uploader = Mock()
        with redirect_stdout(io.StringIO()):
            self.assertFalse(batch.upload_plan(plan, uploader))
        uploader.upload.assert_not_called()

    def test_main_mismatch_and_dry_run_do_not_import_uploaders(self):
        def no_uploader_import(name, *args, **kwargs):
            if name.startswith(("platforms", "upload_pause")):
                raise AssertionError("업로드 관련 모듈을 불러오면 안 돼요")
            return original_import(name, *args, **kwargs)

        import builtins
        original_import = builtins.__import__
        for arguments, expected_result, error in (([], 1, ValueError("파일 개수가 달라요")), (["--dry-run"], 0, None)):
            with self.subTest(arguments=arguments):
                with patch.object(batch, "build_upload_plan", return_value=[], side_effect=error):
                    with patch("builtins.__import__", side_effect=no_uploader_import):
                        with redirect_stdout(io.StringIO()):
                            self.assertEqual(batch.main(arguments), expected_result)

    def test_second_account_sets_session_before_running_shared_batch(self):
        base_dir = Path(batch2.__file__).resolve().parent

        def check_environment(*args, **kwargs):
            self.assertEqual(args, (str(base_dir / "youtube_batch_upload.py"),))
            self.assertEqual(kwargs, {"run_name": "__main__"})
            self.assertEqual(os.environ["MACRO_SESSION_DIR"], str(base_dir / "sessions2"))
            self.assertEqual(os.environ["MACRO_SCREENSHOT_DIR"], str(base_dir / "screenshot2"))
            self.assertEqual(os.environ["MACRO_INPUT_FILE"], str(base_dir / "youtube_input.txt"))
            self.assertEqual(os.environ["MACRO_UPLOAD_DIR"], str(base_dir / "youtube_upload"))
            self.assertEqual(os.environ["MACRO_FORCE_BROWSER_UPLOAD"], "1")
            self.assertEqual(os.environ["MACRO_DISABLE_AUTO_LOGIN"], "1")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(batch2.runpy, "run_path", side_effect=check_environment) as run:
                batch2.main()
            run.assert_called_once()

    def test_batch_uses_ten_second_server_wait_without_extra_delay(self):
        with patch.object(batch, "build_upload_plan", return_value=[]):
            with patch("platforms.youtube.YouTubeUploader") as uploader:
                with patch("upload_pause.pause_on_escape", side_effect=lambda function: function):
                    with patch.object(batch, "upload_plan", return_value=True):
                        with redirect_stdout(io.StringIO()):
                            self.assertEqual(batch.main([]), 0)
        uploader.assert_called_once_with(completion_wait_seconds=0, post_submit_wait_seconds=10)

    def test_completion_close_wait_and_finish_order(self):
        from platforms.youtube import YouTubeUploader

        uploader = YouTubeUploader(completion_wait_seconds=self.settings["completion_wait_seconds"])
        events = Mock()
        uploader._close_completion_dialog = events.close
        events.close.return_value = True
        uploader.wait_with_countdown = events.wait
        uploader.save_result_screenshot = events.screenshot
        page = Mock()
        state = {"succeeded": False}
        with patch("platforms.youtube.get_dynamic_sync_buffer") as dynamic_wait:
            self.assertTrue(uploader._finish_browser_upload(page, state, Path("video.mp4"), None))
        dynamic_wait.assert_not_called()
        self.assertEqual([call[0] for call in events.mock_calls], ["close", "wait", "screenshot"])
        events.wait.assert_called_once_with(page, 0, "YouTube 업로드 완료 후 대기")
        self.assertTrue(state["succeeded"])

    def test_unconfirmed_submission_moves_on_without_retry(self):
        self.prepare("\n---\n".join(self.entry(title) for title in ("one", "two")), ("1.mp4", "2.mp4"))
        uploader = Mock()
        def upload(video, metadata):
            uploader.submission_unconfirmed = video.name == "1.mp4"
            return not uploader.submission_unconfirmed
        uploader.upload.side_effect = upload
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertFalse(batch.upload_plan(self.plan(), uploader, self.settings))
        self.assertEqual(uploader.upload.call_count, 2)
        self.sleep.assert_not_called()
        self.assertIn("1.mp4 | 제목: one", output.getvalue())
        self.assertIn("완료 1개 / 완료 미확인 1개", output.getvalue())

    def test_bulk_server_wait_is_ten_seconds_without_extra_wait_or_close(self):
        from platforms.youtube import YouTubeUploader

        uploader = YouTubeUploader(completion_wait_seconds=0, post_submit_wait_seconds=10)
        page = Mock()
        page.locator.return_value.count.return_value = 1
        page.locator.return_value.nth.return_value.is_visible.return_value = True
        state = {"succeeded": False}
        with patch.object(uploader, "wait_with_countdown") as wait, patch.object(uploader, "_close_completion_dialog") as close:
            self.assertTrue(uploader._finish_after_submission(page, state))
        wait.assert_called_once_with(page, 10, "YouTube 서버 처리 완료 확인")
        close.assert_not_called()
        self.assertTrue(state["succeeded"])
        self.assertTrue(state["skip_failure_hold"])

    def test_bulk_unconfirmed_upload_is_failed_without_failure_hold(self):
        from platforms.youtube import YouTubeUploader

        uploader = YouTubeUploader(completion_wait_seconds=0, post_submit_wait_seconds=10)
        page = Mock()
        page.locator.return_value.count.return_value = 0
        state = {"succeeded": False}
        with patch.object(uploader, "wait_with_countdown") as wait:
            self.assertFalse(uploader._finish_after_submission(page, state))
        wait.assert_called_once_with(page, 10, "YouTube 서버 처리 완료 확인")
        self.assertFalse(state["succeeded"])
        self.assertTrue(state["skip_failure_hold"])

    def test_failed_close_does_not_wait_or_mark_success(self):
        from platforms.youtube import YouTubeUploader

        uploader = YouTubeUploader(completion_wait_seconds=self.settings["completion_wait_seconds"])
        uploader._close_completion_dialog = Mock(return_value=False)
        uploader.wait_with_countdown = Mock()
        state = {"succeeded": False}
        self.assertFalse(uploader._finish_browser_upload(Mock(), state, Path("video.mp4"), None))
        uploader.wait_with_countdown.assert_not_called()
        self.assertFalse(state["succeeded"])


if __name__ == "__main__":
    unittest.main()
