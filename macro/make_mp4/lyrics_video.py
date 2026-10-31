"""로컬 가사 인식, 영어 번역, 이미지 배치와 시간별 영상 렌더링."""

import argparse
from decimal import Decimal
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import wave

from make_mp4 import audio_duration_seconds, find_ffmpeg, global_number, matching_pairs, repeat_count


def settings():
    source = (Path(__file__).resolve().parents[2] / "src/constants/global_constants.ts").read_text(encoding="utf-8")
    match = re.search(r"export const MAKE_K_POP_LYRICS_CONFIG\s*=\s*(.*?);", source, re.S)
    if not match:
        raise ValueError("MAKE_K_POP_LYRICS_CONFIG 설정을 찾을 수 없어요.")
    return json.loads(match.group(1))


def save_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_cues(cues, duration, bilingual=True):
    if not isinstance(cues, list) or not cues:
        raise ValueError("가사가 비어 있어요. lyrics.json에 가사와 시간을 넣어 주세요.")
    previous_end = 0
    for index, cue in enumerate(cues, start=1):
        if not isinstance(cue, dict):
            raise ValueError(f"{index}번째 가사는 객체여야 해요.")
        start, end = cue.get("start"), cue.get("end")
        if (isinstance(start, bool) or isinstance(end, bool)
                or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                or not math.isfinite(start) or not math.isfinite(end)
                or not previous_end <= start < end <= duration):
            raise ValueError(f"{index}번째 시간을 확인해 주세요. 0~{duration:.3f}초 안에서 순서대로 겹치지 않아야 해요.")
        for language in (("ko", "en") if bilingual else ("ko",)):
            if not isinstance(cue.get(language), str) or not cue[language].strip():
                raise ValueError(f"{index}번째 가사의 {language} 문장을 채워 주세요.")
        previous_end = end
    return cues


def decode_for_whisper(audio_path, sampling_rate):
    """FFmpeg로 모노 float32 파형을 읽어 PyAV 버전별 디코더 차이를 피해요."""
    import numpy as np

    result = subprocess.run([
        find_ffmpeg(), "-nostdin", "-v", "error", "-i", str(audio_path),
        "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(sampling_rate),
        "-c:a", "pcm_f32le", "-f", "f32le", "pipe:1",
    ], capture_output=True)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"음원을 읽지 못했어요: {audio_path.name}\n{detail}")
    audio = np.frombuffer(result.stdout, dtype="<f4").astype(np.float32, copy=True)
    if not audio.size:
        raise ValueError(f"음원에 소리가 없어요: {audio_path.name}")
    return audio


def transcribe(mp3, config, args):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("음성 인식 패키지가 없어요. requirements.txt를 설치해 주세요.") from exc
    print(f"한글 가사를 인식해요: {args.model} ({args.device}). 첫 실행에는 모델을 내려받아요.", flush=True)
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    audio = decode_for_whisper(mp3, model.feature_extractor.sampling_rate)
    segments, _ = model.transcribe(audio, language="ko", word_timestamps=True,
                                   beam_size=config["beam_size"], vad_filter=False,
                                   condition_on_previous_text=False)
    cues = []
    for segment in segments:
        if not segment.words:
            if segment.text.strip() and segment.end > segment.start:
                cues.append(dict(start=segment.start, end=segment.end, ko=segment.text.strip(), en=""))
            continue
        group = []
        for word in segment.words:
            if word.end <= word.start:
                continue
            if group and (len("".join(w.word for w in group)) + len(word.word) > config["max_chars"]
                          or word.end - group[0].start > config["max_cue_seconds"]):
                cues.append(dict(start=group[0].start, end=group[-1].end,
                                 ko="".join(w.word for w in group).strip(), en=""))
                group = []
            group.append(word)
        if group:
            cues.append(dict(start=group[0].start, end=group[-1].end,
                             ko="".join(w.word for w in group).strip(), en=""))
    return cues


def load_lyrics(path, mp3, duration, args, config):
    with mp3.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            data = {"cues": data}
        if not isinstance(data, dict):
            raise ValueError("가사 JSON은 cues 목록이 있는 객체 또는 목록이어야 해요.")
        if data.get("source_sha256", digest) != digest:
            raise ValueError(f"음원이 바뀌었어요. {path.name}을 다른 이름으로 보관하고 다시 실행해 주세요.")
    else:
        if args.offline:
            raise ValueError(f"{path.name}이 없어요. --offline을 빼거나 한영 가사 JSON을 만들어 주세요.")
        cues = transcribe(mp3, config, args)
        previous_end = 0
        for cue in cues:
            cue["start"] = max(previous_end, cue["start"])
            cue["end"] = min(duration, cue["end"])
            previous_end = cue["end"]
        cues = [cue for cue in cues if cue["start"] < cue["end"] and cue["ko"]]
        data = {"source_sha256": digest, "recognition_model": args.model,
                "review_required": True, "cues": cues}
        validate_cues(cues, duration, bilingual=False)
        save_json(path, data)
    cues = validate_cues(data.get("cues"), duration, bilingual=False)
    missing = [cue for cue in cues if not isinstance(cue.get("en"), str) or not cue["en"].strip()]
    if missing and args.offline:
        raise ValueError(f"영어 가사가 비어 있어요. {path.name}의 en 문장을 채워 주세요.")
    if missing:
        dependencies = ("torch", "transformers", "sentencepiece") if config["translation_backend"] == "local" else ("deep_translator",)
        if any(importlib.util.find_spec(name) is None for name in dependencies):
            raise RuntimeError("번역 패키지가 없어요. python -m pip install -r requirements.txt를 실행해 주세요.")
        translated = {cue["ko"]: cue["en"] for cue in cues if cue.get("en")}
        if config["translation_backend"] == "local":
            print("PC에서 영어로 번역해요. 첫 실행에는 번역 모델을 내려받아요.", flush=True)
        else:
            print("영어로 번역해요. 가사 문장을 Google 번역으로 보내요.", flush=True)
        for index, cue in enumerate(cues, start=1):
            if cue in missing:
                try:
                    text = translated.get(cue["ko"]) or translate_text(cue["ko"], config)
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError("빈 번역 결과예요.")
                    cue["en"] = text.strip()
                    translated[cue["ko"]] = cue["en"]
                    save_json(path, data)
                    print(f"영어 가사를 저장했어요: {index}/{len(cues)}", flush=True)
                except Exception as exc:
                    raise RuntimeError(f"{index}번째 번역을 받지 못했어요. 다시 실행하면 이어서 번역해요: {exc}") from exc
    return validate_cues(cues, duration)


@lru_cache(maxsize=None)
def local_translator(model_name):
    from transformers import MarianMTModel, MarianTokenizer

    print(f"번역 모델을 준비해요: {model_name}", flush=True)
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


def translate_text(text, config):
    if config["translation_backend"] == "local":
        import torch

        tokenizer, model = local_translator(config["translation_model"])
        inputs = tokenizer(text, return_tensors="pt", truncation=False)
        if inputs["input_ids"].shape[-1] > model.config.max_position_embeddings:
            raise ValueError("번역할 가사가 너무 길어요. JSON에서 짧은 문장으로 나눠 주세요.")
        with torch.inference_mode():
            output = model.generate(**inputs, num_beams=config["beam_size"], do_sample=False,
                                    max_new_tokens=config["translation_max_new_tokens"])
        return tokenizer.decode(output[0], skip_special_tokens=True)

    # deep-translator는 요청 timeout을 전달하지 않아 별도 프로세스로 실행 시간을 제한해요.
    worker = (
        "import json,sys; from deep_translator import GoogleTranslator; "
        "text=json.loads(sys.stdin.read()); "
        "print(json.dumps(GoogleTranslator(source='ko', target='en').translate(text)))"
    )
    try:
        result = subprocess.run([sys.executable, "-c", worker], input=json.dumps(text),
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=config["translation_timeout_seconds"])
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Google 번역 응답이 늦어요. --translation-backend local로 PC에서 번역해 주세요.") from exc
    if result.returncode:
        if "TooManyRequests" in result.stderr:
            raise RuntimeError("Google 번역 요청이 제한됐어요(429). --translation-backend local로 PC에서 번역해 주세요.")
        detail = next((line.strip() for line in reversed(result.stderr.splitlines()) if line.strip()), "오류 내용을 받지 못했어요.")
        raise RuntimeError(f"Google 번역을 받지 못했어요: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Google 번역 결과를 읽지 못했어요. --translation-backend local로 실행해 주세요.") from exc


def find_font(config, supplied):
    for candidate in ([str(supplied)] if supplied else config["font_candidates"]):
        if Path(candidate).is_file():
            return candidate
    raise ValueError("한글 폰트가 없어요. --font로 한글 TTF/OTF 파일을 지정해 주세요.")


def wrap_text(text, font, max_width):
    lines = []
    for paragraph in text.splitlines():
        line = ""
        for char in paragraph:
            if line and font.getlength(line + char) > max_width:
                split = line.rfind(" ")
                if char != " " and split > 0:
                    lines.append(line[:split].strip())
                    line = line[split + 1:] + char
                else:
                    lines.append(line.strip())
                    line = char.lstrip()
            else:
                line += char
        if line.strip():
            lines.append(line.strip())
    return lines


def lyric_frame(background, cue, config, font_path, rect):
    from PIL import ImageDraw, ImageFont
    image = background.copy()
    draw = ImageDraw.Draw(image)
    x, y, width, height = [value * dimension for value, dimension in
                            zip(rect, (image.width, image.height, image.width, image.height))]
    maximum = max(1, round(image.height * config["font_ratio"]))
    minimum = max(1, round(image.height * config["min_font_ratio"]))
    for size in range(maximum, minimum - 1, -1):
        font = ImageFont.truetype(font_path, size)
        stroke = max(1, round(size * config["stroke_ratio"]))
        ko, en = [wrap_text(cue[key], font, width - stroke * 2) for key in ("ko", "en")]
        ascent, descent = font.getmetrics()
        line_height = ascent + descent + stroke * 2
        line_gap = size * config["line_gap_ratio"]
        language_gap = size * config["language_gap_ratio"]
        total = (len(ko) + len(en)) * line_height + (len(ko) + len(en) - 2) * line_gap + language_gap
        if total <= height and all(font.getlength(line) + stroke * 2 <= width for line in ko + en):
            break
    else:
        raise ValueError("가사가 영역보다 길어요. JSON에서 짧은 구간으로 나누거나 --rect를 넓혀 주세요.")
    top = y + (height - total) / 2
    for lines, color in ((ko, config["ko_color"]), (en, config["en_color"])):
        for line in lines:
            draw.text((x + width / 2, top + stroke), line, font=font, anchor="mt", fill=color,
                      stroke_width=stroke, stroke_fill=config["stroke_color"])
            top += line_height + line_gap
        top += language_gap - line_gap
    return image


def render_video(ffmpeg, mp3, image_path, output, args, config, rect, font_path):
    from PIL import Image, ImageOps
    with tempfile.TemporaryDirectory(prefix="make_mp4_") as directory:
        work = Path(directory)
        wav = work / "audio.wav"
        # PCM 반복으로 MP3 인코더 지연이 반복 경계마다 누적되지 않게 해요.
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(mp3), "-vn", "-c:a", "pcm_s16le", str(wav)], check=True)
        with wave.open(str(wav), "rb") as audio:
            duration_decimal = Decimal(audio.getnframes()) / Decimal(audio.getframerate())
        duration = float(duration_decimal)
        cues = load_lyrics(mp3.with_suffix(".lyrics.json"), mp3, duration, args, config)
        with Image.open(image_path) as opened:
            background = ImageOps.exif_transpose(opened).convert("RGB")
        background.save(work / "blank.png")
        timeline = []
        cursor = 0
        for index, cue in enumerate(cues):
            if cue["start"] > cursor:
                timeline.append(("blank.png", cue["start"] - cursor))
            name = f"cue_{index}.png"
            frame = lyric_frame(background, cue, config, font_path, rect)
            frame.save(work / name)
            if index == 0:
                frame.save(output.with_suffix(".preview.png"))
            timeline.append((name, cue["end"] - cue["start"]))
            cursor = cue["end"]
        if cursor < duration:
            timeline.append(("blank.png", duration - cursor))
        print(f"가사 {len(cues)}구간을 준비했어요: {mp3.stem}", flush=True)
        if args.prepare_only:
            return
        loops = 1 if args.single_pass else repeat_count(duration_decimal, global_number("MAKE_MP4_MIN_DURATION_SECONDS"), Decimal(0))
        fps = int(global_number("MAKE_K_POP_VIDEO_FPS"))
        entries = []
        for loop in range(loops):
            cursor = duration_decimal * loop
            for name, length in timeline:
                end = cursor + Decimal(str(length))
                frames = round(end * fps) - round(cursor * fps)
                if frames > 0:
                    entries.extend([f"file '{name}'", f"option framerate {fps}", f"duration {Decimal(frames) / fps:.12f}"])
                cursor = end
        entries.append(f"file '{timeline[-1][0]}'")
        entries.append(f"option framerate {fps}")
        (work / "frames.txt").write_text("\n".join(entries) + "\n", encoding="utf-8")
        temporary = output.with_suffix(".partial.mp4")
        print(f"MP4를 만들어요: {mp3.stem} / {loops}회 / 약 {duration * loops / 60:.1f}분", flush=True)
        try:
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-stats", "-y",
                "-f", "concat", "-safe", "0", "-i", "frames.txt",
                "-stream_loop", str(loops - 1), "-i", str(wav),
                "-map", "0:v:0", "-map", "1:a:0", "-t", str(duration_decimal * loops),
                "-vf", f"pad=ceil(iw/2)*2:ceil(ih/2)*2,fps={fps},tpad=stop_mode=clone:stop=-1", "-r", str(fps),
                "-c:v", "libx264", "-preset", config["encoder_preset"], "-crf", str(config["crf"]),
                "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a",
                f"{int(global_number('MAKE_MP4_AUDIO_BITRATE_KBPS'))}k", "-movflags", "+faststart", str(temporary)
            ], cwd=work, check=True)
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)


def parse_rect(text):
    try:
        values = tuple(map(float, text.split(",")))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("x,y,너비,높이를 숫자로 넣어 주세요.") from exc
    if (len(values) != 4 or not all(math.isfinite(value) for value in values)
            or min(values) < 0 or min(values[2:]) <= 0
            or values[0] + values[2] > 1 or values[1] + values[3] > 1):
        raise argparse.ArgumentTypeError("x,y,너비,높이를 0~1 비율로 넣어 주세요. 영역은 이미지 안에 있어야 해요.")
    return values


def main():
    config = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=Path(__file__).resolve().parent, help="음원과 이미지가 있는 폴더")
    parser.add_argument("--dry-run", action="store_true", help="파일과 길이만 확인해요. 다운로드·번역·파일 저장은 하지 않아요")
    parser.add_argument("--prepare-only", action="store_true", help="가사 JSON과 미리보기만 만들어요")
    length = parser.add_mutually_exclusive_group()
    length.add_argument("--single-pass", action="store_true", dest="single_pass", help="한 곡 길이로 만들어요 (기본)")
    length.add_argument("--repeat-hour", action="store_false", dest="single_pass", help="가사와 곡을 1시간 넘게 반복해요")
    parser.set_defaults(single_pass=True)
    parser.add_argument("--force", action="store_true", help="기존 MP4를 새로 만들어요. 가사 JSON은 재사용해요")
    parser.add_argument("--offline", action="store_true", help="기존 한영 가사 JSON만 사용해요")
    parser.add_argument("--font", type=Path, help="한글 TTF/OTF 폰트 경로")
    parser.add_argument("--rect", type=parse_rect, default=tuple(config["rect"]), help="가사 영역 x,y,너비,높이 비율")
    parser.add_argument("--model", default=config["model"], help="Whisper 모델 이름 또는 로컬 모델 폴더")
    parser.add_argument("--device", default=config["device"], choices=("cpu", "cuda", "auto"))
    parser.add_argument("--compute-type", default=config["compute_type"])
    parser.add_argument("--translation-backend", choices=("local", "google"), default=config["translation_backend"],
                        help="영어 번역 방식 (기본: PC에서 번역, google: Google 번역으로 전송)")
    args = parser.parse_args()
    config["translation_backend"] = args.translation_backend
    folder = args.folder.resolve()
    pairs = list(matching_pairs(folder))
    if not pairs:
        print("이름이 같은 MP3와 PNG/JPG 파일이 없어요.")
        return 0
    ffmpeg = find_ffmpeg()
    result = folder / config["output_folder"]
    font_path = None if args.dry_run else find_font(config, args.font)
    if not args.dry_run:
        result.mkdir(parents=True, exist_ok=True)
    failed = False
    for mp3, image in pairs:
        output = result / f"{mp3.stem}.mp4"
        if output.exists() and not args.force and not args.prepare_only:
            print(f"이미 만든 영상은 건너뛰어요: {output.name} (다시 만들려면 --force)")
            continue
        try:
            if args.dry_run:
                duration = audio_duration_seconds(ffmpeg, mp3)
                loops = 1 if args.single_pass else repeat_count(duration, global_number("MAKE_MP4_MIN_DURATION_SECONDS"), global_number("MAKE_MP4_DURATION_ROUNDING_SECONDS"))
                print(f"{mp3.name} + {image.name} → {output.name} / {loops}회 / 가사 JSON: {mp3.with_suffix('.lyrics.json').exists()}")
            else:
                render_video(ffmpeg, mp3, image, output, args, config, args.rect, font_path)
        except Exception as exc:
            failed = True
            print(f"만들지 못했어요: {mp3.name}\n{exc}", file=sys.stderr)
    return int(failed)
