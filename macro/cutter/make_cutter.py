"""MP4를 대사 구간과 그 앞뒤 구간으로 나누고, 대사를 두 언어로 SRT에 저장해요.

python -m pip install "faster-whisper>=1.2,<2" imageio-ffmpeg "av>=14" "torch>=2.6,<3" "transformers>=4.45,<6" sentencepiece
저장소 루트에서 `python macro/cutter/make_cutter.py`로 실행할 수 있어요.
음성 인식과 번역 모델은 처음 사용할 때 내려받아요. 인식과 번역은 PC에서 실행해요.
"""

import argparse
import math
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory


macro_dir = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(macro_dir), str(macro_dir / "make_mp4")]
from global_constants import load_macro_settings
from lyrics_video import local_translator, speech_model
from make_mp4 import find_ffmpeg


def probe_video(source):
    import av
    from av.stream import Disposition

    with av.open(str(source)) as file:
        video = next((stream for stream in file.streams.video
                      if not stream.disposition & Disposition.attached_pic), None)
        if video is None:
            raise ValueError("영상 트랙을 찾을 수 없어요.")
        audio_streams = file.streams.audio
        audio = next((stream for stream in audio_streams if stream.disposition & Disposition.default),
                     next(iter(audio_streams), None))

        duration = (file.duration or 0) / av.time_base
        if video.duration is not None and video.time_base is not None:
            # FFmpeg의 입력 탐색 시간은 파일의 시작 시각을 기준으로 해요.
            file_start = (file.start_time or 0) / av.time_base
            video_start = video.start_time * video.time_base if video.start_time is not None else file_start
            duration = float(video_start + video.duration * video.time_base - file_start)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("영상 길이를 읽을 수 없어요.")
        if audio is None:
            return video.index, None, duration, ""
        return video.index, audio.index, duration, audio.metadata.get("language", "")


def audio_command(ffmpeg, source, audio_index, sample_rate, start=0.0):
    return [
        ffmpeg, "-nostdin", "-v", "error", "-ss", str(start), "-i", str(source),
        "-map", f"0:{audio_index}", "-af", "aresample=async=1:first_pts=0",
        "-ac", "1", "-ar", str(sample_rate), "-f", "f32le",
    ]


def speech_ranges(ffmpeg, source, audio_index, config):
    import numpy as np
    from faster_whisper.vad import get_speech_timestamps

    sample_rate = config["sample_rate_hz"]
    sample_bytes = struct.calcsize("<f")
    block_bytes = config["scan_seconds"] * sample_rate * sample_bytes
    context_bytes = config["scan_context_seconds"] * sample_rate * sample_bytes
    command = [*audio_command(ffmpeg, source, audio_index, sample_rate), "pipe:1"]
    speech = []
    offset = 0
    previous_context = b""
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        try:
            block = process.stdout.read(block_bytes)
            while block:
                following = process.stdout.read(block_bytes)
                samples = np.frombuffer(previous_context + block + following[:context_bytes], dtype="<f4")
                prefix = len(previous_context) // sample_bytes
                block_samples = len(block) // sample_bytes
                ranges = get_speech_timestamps(
                    samples, sampling_rate=sample_rate,
                    min_silence_duration_ms=config["detection_pause_ms"], speech_pad_ms=0,
                )
                # 앞뒤 문맥으로 감지한 결과에서 이 블록에 속하는 구간만 사용해요.
                for interval in ranges:
                    start = max(0, interval["start"] - prefix)
                    end = min(block_samples, interval["end"] - prefix)
                    if start < end:
                        speech.append(((offset + start) / sample_rate, (offset + end) / sample_rate))
                offset += block_samples
                previous_context = block[-context_bytes:]
                block = following
            if process.wait():
                raise subprocess.CalledProcessError(process.returncode, command)
        finally:
            if process.poll() is None:
                process.kill()
    return speech


def scene_ranges(duration, speech, pause_ms, config):
    minimum_edge = config["minimum_edge_seconds"]
    padding = config["speech_padding_ms"] / 1000
    minimum_gap = max(pause_ms / 1000, 2 * padding + minimum_edge)
    spoken = []
    for start, end in speech:
        start, end = max(0.0, start), min(duration, end)
        if start >= end:
            continue
        if spoken and start - spoken[-1][1] < minimum_gap:
            spoken[-1] = spoken[-1][0], max(spoken[-1][1], end)
        else:
            spoken.append((start, end))

    cursor = 0.0
    for start, end in spoken:
        start = max(0.0, start - padding)
        end = min(duration, end + padding)
        if start - cursor >= minimum_edge:
            yield cursor, start, False
        else:
            start = cursor
        if duration - end < minimum_edge:
            end = duration
        yield start, end, True
        cursor = end
    if cursor < duration:
        yield cursor, duration, False


def save_scene(ffmpeg, source, output, video_index, start, end, config):
    subprocess.run(
        [ffmpeg, "-nostdin", "-v", "error", "-ss", str(start), "-i", str(source),
         "-t", str(end - start), "-map", f"0:{video_index}", "-map", "0:a?",
         "-c:v", "libx264", "-preset", config["encoder_preset"], "-crf", str(config["video_crf"]),
         "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
         "-c:a", "aac", "-b:a", f"{config['audio_bitrate_kbps']}k", "-movflags", "+faststart", str(output)],
        check=True,
    )


def srt_time(milliseconds):
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def read_audio(ffmpeg, source, audio_index, sample_rate, start, duration):
    import numpy as np

    audio = subprocess.check_output([
        *audio_command(ffmpeg, source, audio_index, sample_rate, start), "-t", str(duration), "pipe:1",
    ])
    return np.frombuffer(audio, dtype="<f4")


def detect_language(model, ffmpeg, source, audio_index, speech, config):
    import numpy as np

    remaining_seconds = config["language_sample_seconds"]
    sample_rate = config["sample_rate_hz"]
    samples = []
    for start, end in speech:
        duration = min(remaining_seconds, end - start)
        if duration <= 0:
            continue
        audio = read_audio(ffmpeg, source, audio_index, sample_rate, start, duration)
        if audio.size:
            samples.append(audio)
            remaining_seconds -= audio.size / sample_rate
        if remaining_seconds <= 0:
            break
    if not samples:
        raise RuntimeError("언어를 알아볼 수 있는 대사가 없어요. --language로 원본 언어를 선택해 주세요.")
    _, _, probabilities = model.detect_language(audio=np.concatenate(samples))
    return max((item for item in probabilities if item[0] in config["subtitle_order"]),
               key=lambda item: item[1])[0]


def translate_cues(texts, source_language, target_language, config):
    import torch

    tags = config["translation_tags"]
    tokenizer, model = local_translator(config["translation_model"], family="nllb")
    tokenizer.src_lang = tags[source_language]
    target_id = tokenizer.convert_tokens_to_ids(tags[target_language])
    batch_size = config["translation_batch_size"]
    with torch.inference_mode():
        for offset in range(0, len(texts), batch_size):
            inputs = tokenizer(texts[offset:offset + batch_size], return_tensors="pt", padding=True)
            tokens = model.generate(**inputs, forced_bos_token_id=target_id,
                                    max_new_tokens=config["translation_max_new_tokens"])
            yield from tokenizer.batch_decode(tokens, skip_special_tokens=True)


def save_subtitles(model, ffmpeg, source, output, audio_index, start, end, config, language):
    duration = end - start
    audio = read_audio(ffmpeg, source, audio_index, config["sample_rate_hz"], start, duration)
    if not audio.size:
        return False
    segments, _ = model.transcribe(audio, language=language,
                                   task="transcribe", condition_on_previous_text=False)
    recognized = []
    for segment in segments:
        text = " ".join(segment.text.split())
        start_ms = round(max(0.0, segment.start) * 1000)
        end_ms = round(min(duration, segment.end) * 1000)
        if text and start_ms < end_ms:
            recognized.append((start_ms, end_ms, text))
    if not recognized:
        return False

    order = config["subtitle_order"][language]
    target = next(code for code in order if code != language)
    translations = translate_cues([text for _, _, text in recognized], language, target, config)
    cues = []
    for (start_ms, end_ms, text), translation in zip(recognized, translations, strict=True):
        translated_text = " ".join(translation.split())
        if not translated_text:
            raise RuntimeError("자막 번역이 비어 있어요. 다시 시도해 주세요.")
        lines = {language: text, target: translated_text}
        cues.append(f"{len(cues) + 1}\n{srt_time(start_ms)} --> {srt_time(end_ms)}\n{lines[order[0]]}\n{lines[order[1]]}\n")
    output.write_text("\n".join(cues), encoding="utf-8")
    return True


def main():
    config = load_macro_settings("MAKE_CUTTER_CONFIG")
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input-dir", type=Path, default=folder / config["input_folder"], help="MP4가 있는 폴더")
    parser.add_argument("--output-dir", type=Path, default=folder / config["output_folder"], help="장면을 저장할 폴더")
    parser.add_argument("--pause-ms", type=int, default=config["pause_ms"],
                        help="대사를 나누는 최소 쉼(ms), 기본값 %(default)s")
    parser.add_argument("--language", choices=config["subtitle_order"], help="원본 영상의 언어. 생략하면 자동으로 감지해요.")
    parser.add_argument("--model", default=config["whisper_model"], help="Whisper 모델 이름 또는 폴더, 기본값 %(default)s")
    args = parser.parse_args()
    minimum_pause = max(config["detection_pause_ms"],
                        2 * config["speech_padding_ms"] + math.ceil(config["minimum_edge_seconds"] * 1000))
    if args.pause_ms < minimum_pause:
        parser.error(f"대사를 나눌 쉼은 {minimum_pause}ms 이상으로 설정해 주세요.")
    if not args.input_dir.is_dir():
        parser.error(f"입력 폴더를 찾을 수 없어요. {args.input_dir}")

    sources = sorted((path for path in args.input_dir.resolve().iterdir()
                      if path.is_file() and path.suffix.lower() == ".mp4"), key=lambda path: path.name.casefold())
    if not sources:
        print(f"MP4를 찾을 수 없어요. {args.input_dir}")
        return 0

    try:
        ffmpeg = find_ffmpeg()
    except RuntimeError as exc:
        parser.error(str(exc))

    output_dir = args.output_dir.resolve()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        parser.error(f"결과 폴더를 만들 수 없어요. {exc}")
    failed = False
    for source in sources:
        destination = output_dir / source.stem
        if destination.exists():
            print(f"{source.name}의 결과 폴더가 이미 있어요. 건너뛰었어요.", flush=True)
            continue
        try:
            print(f"{source.name}에서 대사를 찾고 있어요.", flush=True)
            video_index, audio_index, duration, audio_tag = probe_video(source)
            speech = []
            if audio_index is not None:
                speech = speech_ranges(ffmpeg, source, audio_index, config)
            scenes = list(scene_ranges(duration, speech, args.pause_ms, config))
            model = None
            language = args.language
            if any(has_speech for _, _, has_speech in scenes):
                model = speech_model(args.model, config["whisper_device"], config["whisper_compute_type"])
                audio_tag = audio_tag.lower().split("-")[0]
                tagged = config["audio_language_tags"].get(audio_tag, audio_tag)
                if language is None:
                    language = tagged if tagged in config["subtitle_order"] else detect_language(
                        model, ffmpeg, source, audio_index, speech, config,
                    )
            width = config["number_width"]
            with TemporaryDirectory(dir=output_dir) as stage:
                staged_scenes = Path(stage) / "scenes"
                staged_scenes.mkdir()
                for index, (start, end, has_speech) in enumerate(scenes, 1):
                    output = staged_scenes / f"{index:0{width}d}. {source.stem}.mp4"
                    print(f"장면을 저장하고 있어요. ({index}/{len(scenes)}) {output.name}", flush=True)
                    save_scene(ffmpeg, source, output, video_index, start, end, config)
                    if has_speech and not save_subtitles(model, ffmpeg, source, output.with_suffix(".srt"), audio_index,
                                                         start, end, config, language):
                        print(f"{output.name}에서 자막으로 옮길 대사를 찾지 못했어요.", flush=True)
                staged_scenes.rename(destination)
            print(f"{len(scenes)}개 장면을 저장했어요. {destination}", flush=True)
        except ImportError as exc:
            print(f"필요한 패키지를 불러올 수 없어요. 아래 명령으로 설치해 주세요.\n{__doc__.splitlines()[2]}\n{exc}",
                  file=sys.stderr)
            return 1
        except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", None) or str(exc)
            print(f"{source.name}을 나누는 중 문제가 생겼어요. {detail.strip()}", file=sys.stderr, flush=True)
            failed = True
    return int(failed)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
