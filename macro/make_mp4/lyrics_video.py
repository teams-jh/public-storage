"""로컬 가사 인식·번역, 이미지 배치와 시간별 영상 렌더링."""

import argparse
from decimal import Decimal
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave

from make_mp4 import audio_duration_seconds, find_ffmpeg, global_number, matching_pairs, repeat_count


def settings(profile="k_pop"):
    source = (Path(__file__).resolve().parents[2] / "src/constants/global_constants.ts").read_text(encoding="utf-8")
    def read(name):
        match = re.search(rf"export const {re.escape(name)}\s*=\s*(.*?);", source, re.S)
        if not match:
            raise ValueError(f"{name} 설정을 찾을 수 없어요.")
        return json.loads(match.group(1))
    config = read("MAKE_K_POP_LYRICS_CONFIG")
    if profile == "eng_pop":
        config.update(read("MAKE_ENG_POP_LYRICS_CONFIG"))
    elif profile != "k_pop":
        raise ValueError(f"지원하지 않는 가사 설정이에요: {profile}")
    return config


def save_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_cues(cues, duration, bilingual=True, source_language="ko"):
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
        for language in (("ko", "en") if bilingual else (source_language,)):
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


def load_model_with_cache(loader, label):
    """디스크 캐시를 먼저 사용하고 필요한 파일이 없을 때만 내려받아요."""
    try:
        model = loader(local_files_only=True)
    except OSError:
        print(f"저장된 {label}이 없어 내려받아요. 내려받은 파일은 다음 실행에도 사용해요.", flush=True)
        return loader(local_files_only=False)
    print(f"저장된 {label}을 사용해요.", flush=True)
    return model


@lru_cache(maxsize=None)
def speech_model(model_name, device, compute_type):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("음성 인식 패키지가 없어요. requirements.txt를 설치해 주세요.") from exc
    return load_model_with_cache(
        lambda **options: WhisperModel(model_name, device=device, compute_type=compute_type, **options),
        "음성 인식 모델",
    )


def transcribe(mp3, config, args):
    language = config["source_language"]
    print(f"{config['source_label']} 가사를 인식해요: {args.model} ({args.device})", flush=True)
    model = speech_model(args.model, args.device, args.compute_type)
    audio = decode_for_whisper(mp3, model.feature_extractor.sampling_rate)
    segments, _ = model.transcribe(audio, language=language, word_timestamps=True,
                                   beam_size=config["beam_size"], vad_filter=False,
                                   condition_on_previous_text=False)
    cues = []
    def make_cue(start, end, text):
        cue = dict(start=start, end=end, ko="", en="")
        cue[language] = text
        return cue
    for segment in segments:
        if not segment.words:
            if segment.text.strip() and segment.end > segment.start:
                cues.append(make_cue(segment.start, segment.end, segment.text.strip()))
            continue
        group = []
        for word in segment.words:
            if word.end <= word.start:
                continue
            if group and (len("".join(w.word for w in group)) + len(word.word) > config["max_chars"]
                          or word.end - group[0].start > config["max_cue_seconds"]):
                cues.append(make_cue(group[0].start, group[-1].end, "".join(w.word for w in group).strip()))
                group = []
            group.append(word)
        if group:
            cues.append(make_cue(group[0].start, group[-1].end, "".join(w.word for w in group).strip()))
    return cues


def load_lyrics(path, mp3, duration, args, config):
    source_language, target_language = config["source_language"], config["target_language"]
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
        if data.get("source_language", source_language) != source_language:
            raise ValueError(f"가사 원문 언어가 달라요. {path.name}의 source_language를 확인해 주세요.")
    else:
        if args.offline:
            raise ValueError(f"{path.name}이 없어요. --offline을 빼거나 한영 가사 JSON을 만들어 주세요.")
        cues = transcribe(mp3, config, args)
        previous_end = 0
        for cue in cues:
            cue["start"] = max(previous_end, cue["start"])
            cue["end"] = min(duration, cue["end"])
            previous_end = cue["end"]
        cues = [cue for cue in cues if cue["start"] < cue["end"] and cue[source_language]]
        data = {"source_sha256": digest, "recognition_model": args.model,
                "source_language": source_language, "review_required": True, "cues": cues}
        validate_cues(cues, duration, bilingual=False, source_language=source_language)
        save_json(path, data)
    cues = validate_cues(data.get("cues"), duration, bilingual=False, source_language=source_language)
    missing = [cue for cue in cues if not isinstance(cue.get(target_language), str) or not cue[target_language].strip()]
    if missing and args.offline:
        raise ValueError(f"{config['target_label']} 가사가 비어 있어요. {path.name}의 {target_language} 문장을 채워 주세요.")
    if missing:
        dependencies = ("torch", "transformers", "sentencepiece") if config["translation_backend"] == "local" else ("deep_translator",)
        if any(importlib.util.find_spec(name) is None for name in dependencies):
            raise RuntimeError("번역 패키지가 없어요. python -m pip install -r requirements.txt를 실행해 주세요.")
        translated = {cue[source_language]: cue[target_language] for cue in cues if cue.get(target_language)}
        if config["translation_backend"] == "local":
            print(f"PC에서 {config['target_label']}로 번역해요.", flush=True)
        else:
            print(f"{config['target_label']}로 번역해요. 가사 문장을 Google 번역으로 보내요.", flush=True)
        for index, cue in enumerate(cues, start=1):
            if cue in missing:
                try:
                    text = translated.get(cue[source_language]) or translate_text(cue[source_language], config)
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError("빈 번역 결과예요.")
                    cue[target_language] = text.strip()
                    translated[cue[source_language]] = cue[target_language]
                    save_json(path, data)
                    print(f"{config['target_label']} 가사를 저장했어요: {index}/{len(cues)}", flush=True)
                except Exception as exc:
                    raise RuntimeError(f"{index}번째 번역을 받지 못했어요. 다시 실행하면 이어서 번역해요: {exc}") from exc
    return validate_cues(cues, duration)


@lru_cache(maxsize=None)
def local_translator(model_name, family="marian", source_tag=None):
    from huggingface_hub import hf_hub_download

    print(f"번역 모델을 준비해요: {model_name}", flush=True)
    def load(**options):
        if family == "nllb":
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            if not Path(model_name).is_dir():
                hf_hub_download(repo_id=model_name, filename="sentencepiece.bpe.model", **options)
            tokenizer = AutoTokenizer.from_pretrained(model_name, src_lang=source_tag, **options)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name, **options)
            model.eval()
            return tokenizer, model
        from transformers import MarianMTModel, MarianTokenizer
        if not Path(model_name).is_dir():
            # 캐시가 비었을 때 일부 Transformers 버전은 OSError 대신 TypeError를 내요.
            # 필수 토크나이저 파일을 먼저 확인해 캐시 누락을 일관되게 처리해요.
            for filename in ("source.spm", "target.spm", "vocab.json"):
                hf_hub_download(repo_id=model_name, filename=filename, **options)
        tokenizer = MarianTokenizer.from_pretrained(model_name, **options)
        model = MarianMTModel.from_pretrained(model_name, **options)
        model.eval()
        return tokenizer, model

    return load_model_with_cache(load, "번역 모델")


def translate_text(text, config):
    if config["translation_backend"] == "local":
        import torch

        tokenizer, model = local_translator(config["translation_model"], config.get("translation_family", "marian"),
                                            config.get("translation_source_tag"))
        inputs = tokenizer(text, return_tensors="pt", truncation=False)
        if inputs["input_ids"].shape[-1] > model.config.max_position_embeddings:
            raise ValueError("번역할 가사가 너무 길어요. JSON에서 짧은 문장으로 나눠 주세요.")
        with torch.inference_mode():
            language_options = {}
            if config.get("translation_target_tag"):
                language_options["forced_bos_token_id"] = tokenizer.convert_tokens_to_ids(config["translation_target_tag"])
            output = model.generate(**inputs, num_beams=config["beam_size"], do_sample=False,
                                    max_new_tokens=config["translation_max_new_tokens"], **language_options)
        return tokenizer.decode(output[0], skip_special_tokens=True)

    # deep-translator는 요청 timeout을 전달하지 않아 별도 프로세스로 실행 시간을 제한해요.
    worker = (
        "import json,sys; from deep_translator import GoogleTranslator; "
        "data=json.loads(sys.stdin.read()); "
        "print(json.dumps(GoogleTranslator(source=data['source'], target=data['target']).translate(data['text'])))"
    )
    try:
        payload = dict(text=text, source=config["source_language"], target=config["target_language"])
        result = subprocess.run([sys.executable, "-c", worker], input=json.dumps(payload),
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
        path = Path(candidate)
        if not supplied and not path.is_absolute():
            path = Path(__file__).resolve().parent / path
        if path.is_file():
            return str(path.resolve())
    raise ValueError("한글 폰트가 없어요. --font로 한글 TTF/OTF 파일을 지정해 주세요.")


def lyric_window(cues, current_index, radius):
    """현재 가사와 실제로 존재하는 이전·다음 가사를 표시 순서대로 골라요."""
    return [(index - current_index, cues[index])
            for index in range(max(0, current_index - radius), min(len(cues), current_index + radius + 1))]


def lyric_frame(background, cues, current_index, config, font_path, rect):
    from PIL import Image, ImageColor, ImageDraw, ImageFont

    image = background.convert("RGBA")
    overlay = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(overlay)
    x, y, width, height = [value * dimension for value, dimension in
                            zip(rect, (image.width, image.height, image.width, image.height))]
    radius = config["context_radius"]
    window = lyric_window(cues, current_index, radius)
    slot_height = height / (radius * 2 + 1)
    available_height = slot_height * (1 - config["context_slot_gap_ratio"])
    maximum = max(1, round(image.height * config["font_ratio"]))
    minimum = max(1, round(image.height * config["min_font_ratio"]))
    for size in range(maximum, minimum - 1, -1):
        layouts = []
        for offset, cue in window:
            groups = []
            for language, font_size, color in (
                (config["source_language"], size, config[f"{config['source_language']}_color"]),
                (config["target_language"], max(1, min(size - 1, round(size * config["translation_font_scale"]))),
                 config[f"{config['target_language']}_color"]),
            ):
                font = ImageFont.truetype(font_path, font_size)
                stroke = max(1, round(font_size * config["stroke_ratio"])) * config["stroke_multiplier"]
                bold = max(0, round(font_size * config["bold_ratio"]))
                padding = bold + stroke
                # 원문에 개행이 있어도 한 줄로 합치고, 너비를 넘으면 글자 크기를 줄여요.
                lines = [" ".join(cue[language].split())]
                ascent, descent = font.getmetrics()
                line_height = ascent + descent + padding * 2
                line_gap = font_size * config["line_gap_ratio"]
                group_height = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
                groups.append((lines, font, color, bold, padding, line_height, line_gap, group_height))
            language_gap = size * config["language_gap_ratio"]
            total = sum(group[-1] for group in groups) + language_gap
            fits_width = all(font.getlength(line) + padding * 2 <= width
                             for lines, font, _, _, padding, _, _, _ in groups for line in lines)
            if total > available_height or not fits_width:
                break
            layouts.append((offset, groups, total, language_gap))
        else:
            break
    else:
        raise ValueError("가사가 영역보다 길어요. JSON에서 짧은 구간으로 나누거나 --rect를 넓혀 주세요.")
    for offset, groups, total, language_gap in layouts:
        top = y + (offset + radius + 0.5) * slot_height - total / 2
        alpha = round(255 * (1 if offset == 0 else config["context_opacity"]))
        outline = (*ImageColor.getrgb(config["stroke_color"]), alpha)
        for lines, font, color, bold, padding, line_height, line_gap, group_height in groups:
            fill = (*ImageColor.getrgb(color), alpha)
            for line in lines:
                position = (x + width / 2, top + padding)
                draw.text(position, line, font=font, anchor="mt", fill=fill,
                          stroke_width=padding, stroke_fill=outline)
                draw.text(position, line, font=font, anchor="mt", fill=fill,
                          stroke_width=bold, stroke_fill=fill)
                top += line_height + line_gap
            top += language_gap - line_gap
    return Image.alpha_composite(image, overlay).convert("RGB")


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
        print(f"가사 {len(cues)}구간을 준비했어요: {mp3.stem}", flush=True)
        if args.prepare_only:
            return
        with Image.open(image_path) as opened:
            background = ImageOps.exif_transpose(opened).convert("RGB")
        background.save(work / "blank.png")
        timeline = []
        if cues[0]["start"] > 0:
            timeline.append(("blank.png", cues[0]["start"]))
        for index, cue in enumerate(cues):
            name = f"cue_{index}.png"
            frame = lyric_frame(background, cues, index, config, font_path, rect)
            frame.save(work / name)
            # 발화가 끝나도 유지하고 다음 가사의 발화 시작 시각에 교체해요.
            display_end = cues[index + 1]["start"] if index + 1 < len(cues) else duration
            timeline.append((name, display_end - cue["start"]))
        loops = 1
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


def repeat_video(ffmpeg, source, output, duration, config=None):
    """곡 사이에 무음을 넣고 마지막 곡까지 재생해 기준 길이를 초과해요."""
    config = settings() if config is None else config
    gap = Decimal(str(config["repeat_gap_seconds"]))
    if gap < 0:
        raise ValueError("곡 사이 무음 길이는 0초 이상으로 설정해 주세요.")
    source_duration = audio_duration_seconds(ffmpeg, source)
    # n곡 + (n-1)개 무음이 기준을 초과해야 해요. 마지막에는 무음을 붙이지 않아요.
    loops = repeat_count(source_duration + gap, Decimal(str(duration)) + gap,
                         global_number("MAKE_MP4_DURATION_ROUNDING_SECONDS"))
    temporary = output.with_suffix(".partial.mp4")
    total = source_duration * loops + gap * (loops - 1)
    print(f"반복 영상을 만들어요: {output.name} / 곡 전체 {loops}회 / 곡 사이 {gap}초 무음 / 약 {total / 60:.1f}분", flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix="k_pop_repeat_") as directory:
            work = Path(directory)
            # 목록에는 ASCII 상대 경로만 넣어 한글·공백·따옴표가 있는 파일명도 처리해요.
            shutil.copyfile(source, work / "source.mp4")
            if loops > 1 and gap > 0:
                # 무음 동안은 곡의 마지막 화면을 유지해요. 한 곡 출력에는 무음을 넣지 않아요.
                subprocess.run([
                    ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", "source.mp4", "-map", "0:v:0", "-map", "0:a:0",
                    "-vf", f"tpad=stop_mode=clone:stop_duration={gap}", "-af", f"apad=pad_dur={gap}",
                    "-r", str(int(global_number("MAKE_K_POP_VIDEO_FPS"))),
                    "-c:v", "libx264", "-preset", config["encoder_preset"], "-crf", str(config["crf"]),
                    "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a",
                    f"{int(global_number('MAKE_MP4_AUDIO_BITRATE_KBPS'))}k", "padded.mp4",
                ], cwd=work, check=True)
                entries = ["file 'padded.mp4'"] * (loops - 1) + ["file 'source.mp4'"]
            else:
                entries = ["file 'source.mp4'"] * loops
            (work / "repeat.txt").write_text("\n".join(entries) + "\n", encoding="utf-8")
            subprocess.run([
                ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", "repeat.txt",
                "-map", "0:v:0", "-map", "0:a:0", "-c", "copy", "-movflags", "+faststart", str(temporary.resolve()),
            ], cwd=work, check=True)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def create_outputs(ffmpeg, mp3, image, result, args, config, font_path):
    single = result / f"{mp3.stem}.mp4"
    hour = result / f"{mp3.stem}{config['hour_suffix']}.mp4"
    targets = ([single] if args.output_option == "1" else [hour] if args.output_option == "2" else [single, hour])
    pending = [path for path in targets if args.force or not path.exists()]
    for path in targets:
        if path not in pending:
            print(f"이미 만든 영상은 건너뛰어요: {path.name} (다시 만들려면 --force)")
    if args.prepare_only:
        if not args.dry_run:
            render_video(ffmpeg, mp3, image, single, args, config, args.rect, font_path)
        return
    if args.dry_run:
        for path in pending:
            kind = "한 곡" if path == single else f"곡 사이 {config['repeat_gap_seconds']}초 무음, 곡 전체를 반복해 {config['repeat_duration_seconds']}초 초과"
            print(f"{mp3.name} + {image.name} → {path} / {kind}")
        return
    if not pending:
        return
    with tempfile.TemporaryDirectory(prefix="k_pop_source_") as directory:
        source = single
        if single in pending:
            render_video(ffmpeg, mp3, image, single, args, config, args.rect, font_path)
        elif hour in pending and (args.force or not single.exists()):
            # 옵션 2는 원본 가사 영상을 임시 폴더에서 만들고 반복 영상만 남겨요.
            source = Path(directory) / "source.mp4"
            render_video(ffmpeg, mp3, image, source, args, config, args.rect, font_path)
        if hour in pending:
            repeat_video(ffmpeg, source, hour, config["repeat_duration_seconds"], config=config)


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


def main(profile="k_pop"):
    config = settings(profile)
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("option", nargs="?", choices=("1", "2"), help="1: 한 곡만, 2: 1시간 반복만, 생략: 둘 다 만들어요")
    parser.add_argument("--folder", type=Path, default=root / config["input_folder"], help=f"음원과 이미지가 있는 폴더 (기본: {config['input_folder']})")
    parser.add_argument("--dry-run", action="store_true", help="파일과 길이만 확인해요. 다운로드·번역·파일 저장은 하지 않아요")
    parser.add_argument("--prepare-only", action="store_true", help="가사 JSON만 준비해요")
    length = parser.add_mutually_exclusive_group()
    length.add_argument("--option", choices=("1", "2"), dest="named_option", help="1: 한 곡만, 2: 1시간 반복만")
    length.add_argument("--single-pass", action="store_const", const="1", dest="named_option", help="옵션 1과 같아요")
    length.add_argument("--repeat-hour", action="store_const", const="2", dest="named_option", help="옵션 2와 같아요")
    parser.add_argument("--force", action="store_true", help="기존 MP4를 새로 만들어요. 가사 JSON은 재사용해요")
    parser.add_argument("--offline", action="store_true", help="기존 한영 가사 JSON만 사용해요")
    parser.add_argument("--font", type=Path, help="한글 TTF/OTF 폰트 경로")
    parser.add_argument("--rect", type=parse_rect, default=tuple(config["rect"]), help="가사 영역 x,y,너비,높이 비율")
    parser.add_argument("--model", default=config["model"], help="Whisper 모델 이름 또는 로컬 모델 폴더")
    parser.add_argument("--device", default=config["device"], choices=("cpu", "cuda", "auto"))
    parser.add_argument("--compute-type", default=config["compute_type"])
    parser.add_argument("--translation-backend", choices=("local", "google"), default=config["translation_backend"],
                        help="가사 번역 방식 (기본: PC에서 번역, google: Google 번역으로 전송)")
    args = parser.parse_args()
    if args.option and args.named_option:
        parser.error("숫자 옵션과 --option/--single-pass/--repeat-hour 중 하나만 사용해 주세요.")
    args.output_option = args.option or args.named_option
    config["translation_backend"] = args.translation_backend
    folder = args.folder.resolve()
    pairs = list(matching_pairs(folder))
    if not pairs:
        print("이름이 같은 MP3와 PNG/JPG 파일이 없어요.")
        return 0
    ffmpeg = find_ffmpeg()
    result = root / config["output_folder"]
    font_path = None if args.dry_run else find_font(config, args.font)
    if not args.dry_run:
        result.mkdir(parents=True, exist_ok=True)
    failed = False
    for mp3, image in pairs:
        try:
            create_outputs(ffmpeg, mp3, image, result, args, config, font_path)
        except Exception as exc:
            failed = True
            print(f"만들지 못했어요: {mp3.name}\n{exc}", file=sys.stderr)
    return int(failed)
