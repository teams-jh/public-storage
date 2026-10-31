"""외부 번역·모델 다운로드 없이 가사 렌더링과 동기화를 검증해요."""

import argparse
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageChops, ImageStat

import lyrics_video as video


class LyricsTests(unittest.TestCase):
    def test_google_failure_reports_rate_limit_and_actual_error(self):
        config = dict(video.settings(), translation_backend="google")
        for stderr, expected in [("deep_translator.exceptions.TooManyRequests: blocked", "429"),
                                 ("Traceback\nrequests.exceptions.ConnectionError: connection failed", "connection failed")]:
            with self.subTest(stderr=stderr), \
                    patch.object(video.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", stderr)):
                with self.assertRaisesRegex(RuntimeError, expected):
                    video.translate_text("테스트", config)

    def test_google_timeout_reports_local_translation_option(self):
        config = dict(video.settings(), translation_backend="google")
        with patch.object(video.subprocess, "run", side_effect=subprocess.TimeoutExpired("worker", 30)):
            with self.assertRaisesRegex(RuntimeError, "--translation-backend local"):
                video.translate_text("테스트", config)

    def test_transcription_decodes_mp3_to_pcm_without_pyav(self):
        import numpy as np

        ffmpeg = video.find_ffmpeg()
        with tempfile.TemporaryDirectory() as directory:
            mp3 = Path(directory) / "한글 파일 이름.mp3"
            # 스테레오·44.1kHz 입력을 모델 요구 형식(모노·16kHz)으로 바꿔요.
            subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=1", "-ac", "2", "-ar", "44100", str(mp3)], check=True)
            word = SimpleNamespace(start=0.1, end=0.5, word="테스트")
            segment = SimpleNamespace(words=[word])
            model = SimpleNamespace(feature_extractor=SimpleNamespace(sampling_rate=16000),
                                    transcribe=Mock(return_value=(iter([segment]), None)))
            whisper = SimpleNamespace(WhisperModel=Mock(return_value=model))
            args = argparse.Namespace(model="test", device="cpu", compute_type="int8")
            with patch.dict(sys.modules, {"faster_whisper": whisper}), \
                    patch("av.open", side_effect=TypeError("open() got an unexpected keyword argument 'metadata_errors'")) as av_open:
                cues = video.transcribe(mp3, video.settings(), args)
                av_open.assert_not_called()
            audio = model.transcribe.call_args.args[0]
            self.assertIsInstance(audio, np.ndarray)
            self.assertEqual(audio.dtype, np.float32)
            self.assertEqual(audio.shape, (16000,))
            self.assertGreater(float(np.max(np.abs(audio))), 0)
            self.assertTrue(np.isfinite(audio).all())
            self.assertEqual(cues, [dict(start=0.1, end=0.5, ko="테스트", en="")])

    def test_decode_reports_invalid_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.mp3"
            invalid.write_bytes(b"not audio")
            with self.assertRaisesRegex(RuntimeError, "음원을 읽지 못했어요"):
                video.decode_for_whisper(invalid, 16000)

    def test_validation_rejects_overlap_and_invalid_times(self):
        for start, end in [(float("nan"), 1), (0, float("inf")), (True, 1), (-1, 1), (1, 1), (1, 4)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                video.validate_cues([dict(start=start, end=end, ko="가사", en="Lyrics")], 3)
        with self.assertRaises(ValueError):
            video.validate_cues([dict(start=0, end=2, ko="가사", en="Lyrics"),
                                 dict(start=1, end=3, ko="가사", en="Lyrics")], 3)

    def test_rect_rejects_outside_image_and_non_numbers(self):
        for text in ["0,0,2,1", "0,0,0,1", "nan,0,1,1", "x,y,w,h", "0,1"]:
            with self.subTest(text=text), self.assertRaises(argparse.ArgumentTypeError):
                video.parse_rect(text)

    def test_offline_requires_complete_translation_and_checks_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "song.lyrics.json"
            mp3 = Path(directory) / "song.mp3"
            mp3.write_bytes(b"test audio")
            args = argparse.Namespace(offline=True)
            data = dict(cues=[dict(start=0, end=1, ko="가사", en="")])
            video.save_json(path, data)
            with self.assertRaisesRegex(ValueError, "영어"):
                video.load_lyrics(path, mp3, 3, args, video.settings())
            data["cues"][0]["en"] = "Lyrics"
            video.save_json(path, data)
            self.assertEqual(video.load_lyrics(path, mp3, 3, args, video.settings()), data["cues"])
            data["source_sha256"] = "different audio"
            video.save_json(path, data)
            with self.assertRaisesRegex(ValueError, "음원이 바뀌었어요"):
                video.load_lyrics(path, mp3, 3, args, video.settings())

    def test_mp4_cue_changes_gaps_repeat_boundary_and_audio(self):
        ffmpeg = video.find_ffmpeg()
        config = video.settings()
        font = video.find_font(config, None)
        with tempfile.TemporaryDirectory(prefix="lyrics_test_") as directory:
            folder = Path(directory)
            mp3 = folder / "테스트 곡.mp3"
            image = folder / "테스트 곡.PNG"
            output = folder / "테스트 곡.mp4"
            Image.new("RGB", (640, 360), "#facddd").save(image)
            subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=3", str(mp3)], check=True)
            cues = [dict(start=0.5, end=1, ko="오늘도 함께 걸어요", en="Let's walk together"),
                    dict(start=1.5, end=2.2, ko="햇살을 따라가요", en="Follow the sunlight")]
            video.save_json(mp3.with_suffix(".lyrics.json"), dict(cues=cues))
            args = argparse.Namespace(offline=True, single_pass=False, prepare_only=False)
            original_number = video.global_number
            # 두 번 반복해 실제 인코딩 결과에서 반복 경계까지 검사해요.
            with patch.object(video, "global_number", side_effect=lambda name:
                              Decimal(4) if name == "MAKE_MP4_MIN_DURATION_SECONDS" else original_number(name)):
                video.render_video(ffmpeg, mp3, image, output, args, config, config["rect"], font)
            self.assertTrue(output.exists())
            self.assertFalse(output.with_suffix(".partial.mp4").exists())
            self.assertTrue(output.with_suffix(".preview.png").exists())
            self.assertAlmostEqual(float(video.audio_duration_seconds(ffmpeg, output)), 6, delta=0.05)
            info = subprocess.run([ffmpeg, "-i", str(output)], capture_output=True, text=True, errors="replace")
            self.assertIn("Audio: aac", info.stderr)
            self.assertIn("Video: h264", info.stderr)
            import imageio_ffmpeg
            decoded = imageio_ffmpeg.read_frames(str(output), pix_fmt="rgb24")
            next(decoded)
            self.assertEqual(sum(1 for _ in decoded), 180)

            def frame_at(seconds):
                raw = subprocess.run([ffmpeg, "-v", "error", "-ss", str(seconds), "-i", str(output),
                                      "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                     capture_output=True, check=True).stdout
                return Image.frombytes("RGB", (640, 360), raw)

            blank = frame_at(0.2)
            for seconds, visible in [(0.46, False), (0.54, True), (1.04, False),
                                     (0.7, True), (1.2, False), (1.7, True), (2.5, False),
                                     (3.2, False), (3.7, True), (4.2, False), (4.7, True), (5.5, False)]:
                with self.subTest(seconds=seconds):
                    frame = frame_at(seconds)
                    difference = ImageChops.difference(blank, frame)
                    right = sum(ImageStat.Stat(difference.crop((340, 0, 640, 360))).mean)
                    left = sum(ImageStat.Stat(difference.crop((0, 0, 330, 360))).mean)
                    self.assertLess(left, 1)
                    if visible:
                        self.assertGreater(right, 1)
                    else:
                        self.assertLess(right, 1)

    def test_translation_failure_saves_progress_and_resumes(self):
        config = video.settings()
        args = argparse.Namespace(offline=False, model="test")
        with tempfile.TemporaryDirectory() as directory:
            mp3 = Path(directory) / "song.mp3"
            mp3.write_bytes(b"test audio")
            path = mp3.with_suffix(".lyrics.json")
            cues = [dict(start=0, end=1, ko="첫 문장", en=""),
                    dict(start=2, end=3, ko="둘째 문장", en="")]
            with patch.object(video, "transcribe", return_value=cues) as recognition, \
                    patch.object(video.importlib.util, "find_spec", return_value=True), \
                    patch.object(video, "translate_text", side_effect=["First line", RuntimeError("network")]):
                with self.assertRaisesRegex(RuntimeError, "2번째 번역"):
                    video.load_lyrics(path, mp3, 4, args, config)
                recognition.assert_called_once()
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["cues"][0]["en"], "First line")
            self.assertEqual(saved["cues"][1]["en"], "")
            with patch.object(video, "transcribe") as recognition, \
                    patch.object(video.importlib.util, "find_spec", return_value=True), \
                    patch.object(video, "translate_text", return_value="Second line") as translation:
                result = video.load_lyrics(path, mp3, 4, args, config)
                recognition.assert_not_called()
                translation.assert_called_once_with("둘째 문장", config)
            self.assertEqual([cue["en"] for cue in result], ["First line", "Second line"])


if __name__ == "__main__":
    unittest.main()
