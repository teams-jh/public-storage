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
    def test_long_middle_line_does_not_shrink_other_cues_or_languages(self):
        from PIL import ImageDraw

        background = Image.new("RGB", (1200, 600), "#facddd")
        original = ImageDraw.ImageDraw.text
        for profile in ("k_pop", "eng_pop"):
            config = video.settings(profile)
            font = video.find_font(config, None)
            cues = [dict(ko=f"가사 {letter}", en=f"Line {letter}") for letter in ("A", "B", "C")]

            def sizes_for(rows):
                sizes = {}
                def track(drawer, position, text, **options):
                    sizes[text] = options["font"].size
                    return original(drawer, position, text, **options)
                with patch.object(ImageDraw.ImageDraw, "text", new=track):
                    video.lyric_frame(background, rows, 1, config, font, config["rect"])
                return sizes

            normal = sizes_for(cues)
            for language in ("ko", "en"):
                with self.subTest(profile=profile, long_language=language):
                    changed = [dict(cue) for cue in cues]
                    changed[1][language] = ("아주 긴 가사 " if language == "ko" else "A very long lyric ") * 20
                    actual = sizes_for(changed)
                    long_text = " ".join(changed[1][language].split())
                    self.assertLess(actual[long_text], normal[cues[1][language]])
                    for text, size in normal.items():
                        if text != cues[1][language]:
                            self.assertEqual(actual[text], size)

    def test_option_three_skips_existing_json_even_with_force(self):
        with tempfile.TemporaryDirectory() as directory:
            mp3 = Path(directory) / "song.mp3"
            path = mp3.with_suffix(".lyrics.json")
            original = b"user-edited JSON, do not touch"
            path.write_bytes(original)
            args = argparse.Namespace(output_option="3", force=True, dry_run=False)
            with patch.object(video, "find_ffmpeg") as ffmpeg, \
                    patch.object(video, "load_lyrics") as lyrics, \
                    patch.object(video, "render_video") as render:
                video.create_outputs(None, mp3, None, Path(directory) / "result", args, video.settings(), None)
            ffmpeg.assert_not_called()
            lyrics.assert_not_called()
            render.assert_not_called()
            self.assertEqual(path.read_bytes(), original)

    def test_option_three_builds_json_without_image_font_or_result_folder(self):
        for profile, option in [("k_pop", ["3"]), ("eng_pop", ["--option", "3"])]:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                mp3 = folder / "song.MP3"
                mp3.write_bytes(b"audio")
                config = dict(video.settings(profile), output_folder=str(folder / "result"))
                def build(path, source, duration, args, selected_config):
                    video.save_json(path, dict(cues=[dict(start=0, end=1, ko="가사", en="Lyrics")]))
                with patch.object(sys, "argv", ["script", *option, "--folder", str(folder)]), \
                        patch.object(video, "settings", return_value=config), \
                        patch.object(video, "find_ffmpeg", return_value="ffmpeg"), \
                        patch.object(video, "decode_wav", return_value=Decimal(1)), \
                        patch.object(video, "load_lyrics", side_effect=build) as lyrics, \
                        patch.object(video, "find_font") as font, \
                        patch.object(video, "render_video") as render:
                    self.assertEqual(video.main(profile), 0)
                self.assertTrue(mp3.with_suffix(".lyrics.json").exists())
                self.assertFalse((folder / "result").exists())
                self.assertFalse(list(folder.glob("*.mp4")))
                font.assert_not_called()
                render.assert_not_called()
                lyrics.assert_called_once()

    def test_translation_model_missing_tokenizer_downloads_before_loading(self):
        tokenizer = object()
        model = Mock()
        transformers = SimpleNamespace(
            MarianTokenizer=SimpleNamespace(from_pretrained=Mock(return_value=tokenizer)),
            MarianMTModel=SimpleNamespace(from_pretrained=Mock(return_value=model)))
        def download(**options):
            if options["local_files_only"]:
                raise FileNotFoundError("no tokenizer cache")
            return "downloaded"
        video.local_translator.cache_clear()
        with patch.dict(sys.modules, {"transformers": transformers}), \
                patch("huggingface_hub.hf_hub_download", side_effect=download) as files:
            self.assertEqual(video.local_translator("test-en-ko-model"), (tokenizer, model))
        self.assertTrue(files.call_args_list[0].kwargs["local_files_only"])
        self.assertTrue(all(not call.kwargs["local_files_only"] for call in files.call_args_list[1:]))
        transformers.MarianTokenizer.from_pretrained.assert_called_once_with("test-en-ko-model", local_files_only=False)
        model.eval.assert_called_once()
        video.local_translator.cache_clear()

    def test_eng_pop_recognizes_english_and_translates_into_korean(self):
        config = video.settings("eng_pop")
        word = SimpleNamespace(start=0.1, end=0.8, word="Hello world")
        model = SimpleNamespace(feature_extractor=SimpleNamespace(sampling_rate=16000),
                                transcribe=Mock(return_value=(iter([SimpleNamespace(words=[word])]), None)))
        args = argparse.Namespace(model="test", device="cpu", compute_type="int8", offline=False)
        with patch.object(video, "speech_model", return_value=model), \
                patch.object(video, "decode_for_whisper", return_value=object()):
            cues = video.transcribe(Path("song.mp3"), config, args)
        self.assertEqual(model.transcribe.call_args.kwargs["language"], "en")
        self.assertEqual(cues, [dict(start=0.1, end=0.8, ko="", en="Hello world")])
        with tempfile.TemporaryDirectory() as directory:
            mp3 = Path(directory) / "song.mp3"
            mp3.write_bytes(b"audio")
            path = mp3.with_suffix(".lyrics.json")
            with patch.object(video, "transcribe", return_value=cues), \
                    patch.object(video.importlib.util, "find_spec", return_value=True), \
                    patch.object(video, "translate_text", return_value="안녕하세요") as translation:
                result = video.load_lyrics(path, mp3, 1, args, config)
            translation.assert_called_once_with("Hello world", config)
            self.assertEqual(result[0]["en"], "Hello world")
            self.assertEqual(result[0]["ko"], "안녕하세요")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["source_language"], "en")

    def test_eng_pop_places_smaller_korean_below_english(self):
        from PIL import ImageDraw

        config = video.settings("eng_pop")
        font = video.find_font(config, None)
        background = Image.new("RGB", (1200, 600), "#facddd")
        calls = []
        original = ImageDraw.ImageDraw.text
        def track(drawer, position, text, **kwargs):
            calls.append((position, text, kwargs["font"].size))
            return original(drawer, position, text, **kwargs)
        with patch.object(ImageDraw.ImageDraw, "text", new=track):
            video.lyric_frame(background, [dict(en="Hello world", ko="안녕하세요")], 0,
                              config, font, config["rect"])
        self.assertEqual([text for _, text, _ in calls], ["Hello world", "Hello world", "안녕하세요", "안녕하세요"])
        self.assertGreater(calls[0][2], calls[2][2])
        self.assertLess(calls[0][0][1], calls[2][0][1])
        self.assertEqual(config["input_folder"], "eng_pop")
        self.assertEqual(config["output_folder"], "result/eng_pop")

    def test_eng_pop_mp4_sync_and_silent_repeat(self):
        config = video.settings("eng_pop")
        with patch.object(video, "settings", return_value=config):
            self.test_mp4_cue_changes_gaps_repeat_boundary_and_audio()

    def test_long_korean_and_english_shrink_without_wrapping(self):
        from PIL import ImageDraw

        config = video.settings()
        font = video.find_font(config, None)
        background = Image.new("RGB", (1200, 600), "#facddd")
        cue = dict(ko="가나다라마바사아자차카타파하" * 5,
                   en="A very long English lyric without a line break " * 4)
        calls = []
        original = ImageDraw.ImageDraw.text

        def track(drawer, position, text, **kwargs):
            calls.append((text, kwargs))
            return original(drawer, position, text, **kwargs)

        with patch.object(ImageDraw.ImageDraw, "text", new=track):
            video.lyric_frame(background, [cue] * 3, 1, config, font, config["rect"])
        expected = {" ".join(cue[key].split()) for key in ("ko", "en")}
        self.assertEqual(len(calls), 12)  # 3묶음 × 2언어 × 테두리/본문
        self.assertEqual({text for text, _ in calls}, expected)
        for text, options in calls:
            self.assertNotIn("\n", text)
            self.assertLessEqual(options["font"].getlength(text) + options["stroke_width"] * 2,
                                 background.width * config["rect"][2])
            self.assertLess(options["font"].size, round(background.height * config["font_ratio"]))

    def test_one_wrapped_language_uses_spare_space_without_shrinking_fonts(self):
        from PIL import ImageDraw

        for profile in ("k_pop", "eng_pop"):
            with self.subTest(profile=profile):
                config = video.settings(profile)
                font = video.find_font(config, None)
                background = Image.new("RGB", (1200, 600), "#facddd")
                cues = [dict(ko=f"가사 {letter}", en=f"Line {letter}") for letter in ("A", "B", "C")]
                original = ImageDraw.ImageDraw.text

                def inspect(rows):
                    sizes, boxes = {}, []
                    def track(drawer, position, text, **options):
                        sizes[text] = options["font"].size
                        boxes.append(drawer.textbbox(position, text, font=options["font"],
                                                     anchor=options["anchor"], stroke_width=options["stroke_width"]))
                        return original(drawer, position, text, **options)
                    with patch.object(ImageDraw.ImageDraw, "text", new=track):
                        video.lyric_frame(background, rows, 1, config, font, config["rect"])
                    return sizes, boxes

                baseline, _ = inspect(cues)
                for language, extra in (("ko", "두 번째 줄"), ("en", "Second line")):
                    changed = [dict(cue) for cue in cues]
                    changed[1][language] += "\n" + extra
                    actual, boxes = inspect(changed)
                    for line, size in baseline.items():
                        self.assertEqual(actual[line], size)
                    self.assertEqual(actual[extra], baseline[cues[1][language]])
                    x, y, width, height = [value * dimension for value, dimension in
                                          zip(config["rect"], (1200, 600, 1200, 600))]
                    for left, top, right, bottom in boxes:
                        self.assertGreaterEqual(left, x)
                        self.assertLessEqual(right, x + width)
                        self.assertGreaterEqual(top, y)
                        self.assertLessEqual(bottom, y + height)
                    # Four draw calls per one-line cue; the middle cue has six.
                    self.assertLessEqual(max(box[3] for box in boxes[:4]), min(box[1] for box in boxes[4:10]))
                    self.assertLessEqual(max(box[3] for box in boxes[4:10]), min(box[1] for box in boxes[10:]))

    def test_explicit_line_breaks_preserve_both_languages_and_fit_each_slot(self):
        from PIL import ImageDraw

        for profile in ("k_pop", "eng_pop"):
            with self.subTest(profile=profile):
                config = video.settings(profile)
                font = video.find_font(config, None)
                background = Image.new("RGB", (1200, 600), "#facddd")
                cue = dict(ko="이 수를 사랑해\n너도 그렇지 않니",
                           en="I love this number.\nDon't you feel the same?")
                calls = []
                original = ImageDraw.ImageDraw.text

                def track(drawer, position, text, **options):
                    bounds = drawer.textbbox(position, text, font=options["font"],
                                             anchor=options["anchor"], stroke_width=options["stroke_width"])
                    calls.append((text, bounds))
                    return original(drawer, position, text, **options)

                with patch.object(ImageDraw.ImageDraw, "text", new=track):
                    video.lyric_frame(background, [cue] * 3, 1, config, font, config["rect"])
                languages = (config["source_language"], config["target_language"])
                expected = [line for language in languages for line in cue[language].splitlines()
                            for _ in range(2)]
                self.assertEqual([text for text, _ in calls], expected * 3)
                x, y, width, height = [value * dimension for value, dimension in
                                      zip(config["rect"], (1200, 600, 1200, 600))]
                slot_height = height / 3
                for slot in range(3):
                    for _, (left, top, right, bottom) in calls[slot * len(expected):(slot + 1) * len(expected)]:
                        self.assertGreaterEqual(left, x)
                        self.assertLessEqual(right, x + width)
                        self.assertGreaterEqual(top, y + slot * slot_height)
                        self.assertLessEqual(bottom, y + (slot + 1) * slot_height)

    def test_lyric_window_first_middle_and_last(self):
        cues = [dict(ko=str(index), en=str(index)) for index in range(4)]
        self.assertEqual([cue["ko"] for _, cue in video.lyric_window(cues, 0, 1)], ["0", "1"])
        self.assertEqual([cue["ko"] for _, cue in video.lyric_window(cues, 1, 1)], ["0", "1", "2"])
        self.assertEqual([cue["ko"] for _, cue in video.lyric_window(cues, 2, 1)], ["1", "2", "3"])
        self.assertEqual([cue["ko"] for _, cue in video.lyric_window(cues, 3, 1)], ["2", "3"])

    def test_context_opacity_and_empty_first_slot(self):
        config = video.settings()
        font = video.find_font(config, None)
        background = Image.new("RGB", (1200, 600), "#facddd")
        cues = [dict(ko="가나다", en="ABC") for _ in range(3)]
        frame = video.lyric_frame(background, cues, 1, config, font, config["rect"])
        diff = ImageChops.difference(background, frame)
        x, y, width, height = [round(value * dimension) for value, dimension in
                                zip(config["rect"], (1200, 600, 1200, 600))]
        slot = height // 3
        strengths = [sum(ImageStat.Stat(diff.crop((x, y + row * slot, x + width, y + (row + 1) * slot))).mean)
                     for row in range(3)]
        self.assertGreater(strengths[1], 0)
        self.assertAlmostEqual(strengths[0] / strengths[1], config["context_opacity"], delta=0.03)
        self.assertAlmostEqual(strengths[2] / strengths[1], config["context_opacity"], delta=0.03)
        first = video.lyric_frame(background, cues, 0, config, font, config["rect"])
        self.assertIsNone(ImageChops.difference(background, first).crop((x, y, x + width, y + slot)).getbbox())

    def test_cached_model_is_loaded_without_network(self):
        model = object()
        loader = Mock(return_value=model)
        self.assertIs(video.load_model_with_cache(loader, "테스트 모델"), model)
        loader.assert_called_once_with(local_files_only=True)

    def test_model_downloads_only_when_cache_is_missing(self):
        model = object()
        loader = Mock(side_effect=[FileNotFoundError("not cached"), model])
        self.assertIs(video.load_model_with_cache(loader, "테스트 모델"), model)
        self.assertEqual([call.kwargs for call in loader.call_args_list],
                         [{"local_files_only": True}, {"local_files_only": False}])

    def test_output_modes_and_existing_single_reuse(self):
        for mode, existing_single, expected in [(None, False, {"song.mp4", "song_1hour.mp4"}),
                                                 ("1", False, {"song.mp4"}),
                                                 ("2", False, {"song_1hour.mp4"}),
                                                 (None, True, {"song.mp4", "song_1hour.mp4"})]:
            with self.subTest(mode=mode, existing_single=existing_single), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = root / "result"
                result.mkdir()
                if existing_single:
                    (result / "song.mp4").write_bytes(b"existing")
                args = argparse.Namespace(output_option=mode, force=False, prepare_only=False, dry_run=False, rect=())

                def render(ffmpeg, mp3, image, output, *positional, **kwargs):
                    output.write_bytes(b"single")

                def repeat(ffmpeg, source, output, duration, config=None):
                    self.assertTrue(source.is_file())
                    output.write_bytes(b"hour")

                with patch.object(video, "render_video", side_effect=render) as renderer, \
                        patch.object(video, "repeat_video", side_effect=repeat) as repeater:
                    video.create_outputs("ffmpeg", root / "song.mp3", root / "song.png", result,
                                         args, video.settings(), "font")
                self.assertEqual({p.name for p in result.glob("*.mp4")}, expected)
                self.assertEqual(renderer.call_count, 0 if existing_single else 1)
                self.assertEqual(repeater.call_count, 0 if mode == "1" else 1)

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
            video.speech_model.cache_clear()
            with patch.dict(sys.modules, {"faster_whisper": whisper}), \
                    patch("av.open", side_effect=TypeError("open() got an unexpected keyword argument 'metadata_errors'")) as av_open:
                cues = video.transcribe(mp3, video.settings(), args)
                av_open.assert_not_called()
            video.speech_model.cache_clear()
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
            single = folder / "한 곡.mp4"
            Image.new("RGB", (640, 360), "#facddd").save(image)
            subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=3", str(mp3)], check=True)
            cues = [dict(start=0.5, end=1, ko="오늘도 함께 걸어요", en="Let's walk together"),
                    dict(start=1.5, end=2.2, ko="햇살을 따라가요", en="Follow the sunlight")]
            video.save_json(mp3.with_suffix(".lyrics.json"), dict(cues=cues))
            args = argparse.Namespace(offline=True, single_pass=False, prepare_only=False)
            video.render_video(ffmpeg, mp3, image, single, args, config, config["rect"], font)
            # 3초 곡 + 3초 무음 + 3초 곡으로 6초 기준을 초과해요.
            video.repeat_video(ffmpeg, single, output, 6)
            self.assertTrue(output.exists())
            self.assertFalse(output.with_suffix(".partial.mp4").exists())
            self.assertFalse(list(folder.glob("*.preview.png")))
            self.assertAlmostEqual(float(video.audio_duration_seconds(ffmpeg, output)), 9, delta=0.15)
            info = subprocess.run([ffmpeg, "-i", str(output)], capture_output=True, text=True, errors="replace")
            self.assertIn("Audio: aac", info.stderr)
            self.assertIn("Video: h264", info.stderr)
            import imageio_ffmpeg
            decoded = imageio_ffmpeg.read_frames(str(output), pix_fmt="rgb24")
            next(decoded)
            self.assertLessEqual(abs(sum(1 for _ in decoded) - 270), 3)

            def frame_at(seconds):
                raw = subprocess.run([ffmpeg, "-v", "error", "-ss", str(seconds), "-i", str(output),
                                      "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                     capture_output=True, check=True).stdout
                return Image.frombytes("RGB", (640, 360), raw)

            blank = frame_at(0.2)
            for seconds, visible in [(0.46, False), (0.54, True), (1.04, True),
                                     (0.7, True), (1.2, True), (1.7, True), (2.5, True),
                                     (3.2, True), (3.7, True), (4.2, True), (4.7, True), (5.5, True),
                                     (6.2, False), (6.7, True), (7.2, True), (7.7, True), (8.8, True)]:
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

            def text_difference(first, second):
                difference = ImageChops.difference(frame_at(first), frame_at(second)).crop((340, 0, 640, 360))
                return sum(ImageStat.Stat(difference).mean)

            # 첫 가사는 1초에 끝나지만 다음 발화가 시작되는 1.5초까지 유지돼요.
            self.assertLess(text_difference(0.7, 1.2), 1)
            self.assertLess(text_difference(0.7, 1.46), 1)
            self.assertGreater(text_difference(0.7, 1.54), 1)
            self.assertLess(text_difference(1.7, 2.8), 1)

            import numpy as np
            audio = video.decode_for_whisper(output, 16000)
            # 무음 양끝의 AAC 경계 오차를 피해서 무음 내부와 양쪽 곡의 소리를 확인해요.
            self.assertLess(float(np.max(np.abs(audio[int(3.15 * 16000):int(5.85 * 16000)]))), 0.001)
            for start, end in [(0.2, 2.8), (6.2, 8.8)]:
                self.assertGreater(float(np.max(np.abs(audio[int(start * 16000):int(end * 16000)]))), 0.01)

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
