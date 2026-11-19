"""하위 폴더마다 가사 JSON을 준비하고 여러 곡을 순서대로 이어 붙여요."""

import argparse
from contextlib import contextmanager
from decimal import Decimal
from itertools import chain, repeat
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from lyrics_video import (
    create_json_only,
    decode_wav,
    encode_timeline,
    find_font,
    load_lyrics,
    normalize_track,
    parse_rect,
    read_lyrics_data,
    render_track_frames,
    settings,
)
from make_mp4 import find_ffmpeg, global_number, global_string, matching_pairs


def positive_count(value):
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("반복 횟수를 1 이상의 정수로 넣어 주세요.") from exc
    if count < 1:
        raise argparse.ArgumentTypeError("반복 횟수를 1 이상의 정수로 넣어 주세요.")
    return count


def automatic_repeat_count(duration, sample_rate):
    frames = round(duration * sample_rate)
    if frames <= 0:
        raise ValueError("재생할 수 있는 소리가 없어요. MP3 파일을 확인해 주세요.")
    target_frames = round(global_number("MAKE_POP_MERGE_MIN_DURATION_SECONDS") * sample_rate)
    return (target_frames + frames - 1) // frames


def print_merge_plan(output, songs, count):
    print(f"{output.name} / {' → '.join(mp3.stem for mp3 in songs)} / 전체 {count}회", flush=True)


@contextmanager
def track_log(mp3, image):
    """작업 중인 파일과 오류 원인을 함께 보여줘요."""
    paths = (f"음원: {mp3.resolve()}\n"
             f"가사 JSON: {mp3.with_suffix('.lyrics.json').resolve()}\n"
             f"배경 이미지: {image.resolve()}")
    print(f"곡을 준비해요.\n{paths}", flush=True)
    try:
        yield
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"곡을 처리하지 못했어요.\n{paths}\n원인: {exc}") from exc


def language_settings(config, language):
    profiles = config["merge_track_profiles"]
    if not isinstance(language, str) or language not in profiles:
        raise ValueError(f"원문 언어를 {', '.join(profiles)} 중 하나로 지정해 주세요.")
    return dict(settings(profiles[language]), translation_backend=config["translation_backend"])


def merge_folder(ffmpeg, tracks, output, args, config, wav_options, *, sample_rate, count):
    from PIL import Image, ImageOps

    font_path = find_font(config, args.font)
    target_loudness = global_number("MAKE_POP_MERGE_TARGET_LOUDNESS_LUFS")
    max_true_peak = global_number("MAKE_POP_MERGE_MAX_TRUE_PEAK_DBTP")
    with tempfile.TemporaryDirectory(prefix="lyrics_merge_") as directory:
        work = Path(directory)
        source_wav = work / "source.wav"
        audio_entries = []
        timeline = []
        duration = Decimal(0)
        canvas = None
        for index, (mp3, image) in enumerate(tracks):
            with track_log(mp3, image):
                track = work / str(index)
                track.mkdir()
                wav = track / "audio.wav"
                track_duration = decode_wav(ffmpeg, mp3, source_wav, wav_options)
                lyrics_path = mp3.with_suffix(".lyrics.json")
                data = None
                track_config = config
                if "merge_track_profiles" in config:
                    data = read_lyrics_data(lyrics_path)
                    if data.get("cues") != []:
                        track_config = language_settings(config, data.get("source_language", config["source_language"]))
                cues = load_lyrics(lyrics_path, mp3, float(track_duration), args, track_config, data=data)
                source_font_path = None
                if cues and "source_font_candidates" in track_config:
                    source_font_path = find_font(track_config, args.font, source=True)
                normalize_track(ffmpeg, source_wav, wav, target_loudness, max_true_peak)
                with Image.open(image) as opened:
                    background = ImageOps.exif_transpose(opened).convert("RGB")
                if canvas is None:
                    canvas = background.size
                if background.size != canvas:
                    background = ImageOps.pad(background, canvas, color="black")
                timeline.extend(render_track_frames(background, cues, track_duration, track_config,
                                                    args.rect, font_path, track, source_font_path=source_font_path))
                audio_entries.append(f"file '{wav.relative_to(work).as_posix()}'\n")
                duration += track_duration

        if count is None:
            count = automatic_repeat_count(duration, sample_rate)
        print_merge_plan(output, (mp3 for mp3, _ in tracks), count)
        (work / "audio.txt").write_text("".join(audio_entries) * count, encoding="utf-8")
        repeated_frames = chain.from_iterable(repeat(timeline, count))
        audio_input = ["-f", "concat", "-i", "audio.txt"]
        output.parent.mkdir(parents=True, exist_ok=True)
        # 완성된 영상만 같은 드라이브의 결과 폴더로 옮겨요.
        with tempfile.TemporaryDirectory(prefix="merge_", dir=output.parent) as staging:
            temporary = Path(staging) / "output.mp4"
            encode_timeline(ffmpeg, repeated_frames, audio_input, duration * count, config, work, temporary)
            temporary.replace(output)


def folder_tracks(root, *, flat=False):
    folders = [root.resolve()] if flat else sorted(
        (path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name.casefold()
    )
    for folder in folders:
        songs = sorted(
            (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".mp3"),
            key=lambda path: path.name.casefold(),
        )
        if songs:
            yield folder, songs


def write_timestamps(folders, output, sample_rate, wav_options, dry_run):
    seconds_per_hour = int(global_number("MAKE_POP_MERGE_SECONDS_PER_HOUR"))
    seconds_per_minute = int(global_number("MAKE_POP_MERGE_SECONDS_PER_MINUTE"))
    ffmpeg = None
    sections = []
    for folder, songs in folders:
        ffmpeg = ffmpeg or find_ffmpeg()
        elapsed_frames = 0
        lines = [f"[{folder.name}]"]
        with tempfile.TemporaryDirectory(prefix="timestamps_") as directory:
            wav = Path(directory) / "audio.wav"
            for mp3 in songs:
                hours, remaining = divmod(elapsed_frames // sample_rate, seconds_per_hour)
                minutes, seconds = divmod(remaining, seconds_per_minute)
                name = re.sub(r"^\d+\.\s+", "", mp3.stem).split(" - ", 1)[0]
                lines.append(f"{hours:02d}:{minutes:02d}:{seconds:02d} {name}")
                try:
                    duration = decode_wav(ffmpeg, mp3, wav, wav_options)
                except (OSError, subprocess.CalledProcessError) as exc:
                    raise ValueError(
                        f"{folder.name}/{mp3.name}의 재생 시간을 읽을 수 없어요. MP3 파일을 확인해 주세요."
                    ) from exc
                # PCM 프레임 수를 누적해 소수점 오차로 초 경계가 어긋나는 일을 막아요.
                elapsed_frames += round(duration * sample_rate)
        sections.append("\n".join(lines))

    if not sections:
        return False
    report = "\n\n".join(sections) + "\n"
    if dry_run:
        print(report, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="timestamps_", dir=output.parent) as staging:
            temporary = Path(staging) / output.name
            temporary.write_text(report, encoding="utf-8")
            temporary.replace(output)
        print(f"타임스탬프를 저장했어요. {output}")
    return True


def main(profile="k_pop"):
    config = settings(profile)
    flat = config.get("merge_flat_input", False)
    track_profiles = config.get("merge_track_profiles")
    root = Path(__file__).resolve().parent
    automatic_repeat = object()
    description = "폴더에 있는 여러 언어의 곡을 이어 붙여요." if flat else __doc__
    parser = argparse.ArgumentParser(description=description)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--merge", nargs="?", type=positive_count, const=automatic_repeat, metavar="횟수",
                      help="기존 가사 JSON으로 영상을 만들어요. 횟수를 생략하면 최소 재생 시간에 맞춰 반복해요.")
    mode.add_argument("--timestamp", action="store_true", help="폴더별 곡 시작 시각을 텍스트 파일 하나에 저장해요.")
    parser.add_argument("--folder", type=Path, default=root / config["merge_input_folder"],
                        help="곡을 모아 둔 폴더예요." if flat else "곡을 모아 둔 하위 폴더들이 있는 경로예요.")
    parser.add_argument("--dry-run", action="store_true", help="결과를 저장하기 전에 미리 봐요.")
    parser.add_argument("--offline", action="store_true", help="가사를 만들 때 모델을 내려받거나 번역을 요청하지 않아요.")
    parser.add_argument("--font", type=Path, help="가사에 사용할 폰트 파일 경로예요.")
    parser.add_argument("--rect", type=parse_rect, default=tuple(config["rect"]), help="가사 영역 x,y,너비,높이 비율이에요.")
    parser.add_argument("--model", default=config["model"], help="Whisper 모델 이름 또는 로컬 모델 폴더예요.")
    parser.add_argument("--device", default=config["device"], choices=("cpu", "cuda", "auto"))
    parser.add_argument("--compute-type", default=config["compute_type"])
    parser.add_argument("--translation-backend", choices=("local", "google"), default=config["translation_backend"],
                        help="번역 방식을 골라요. google을 고르면 가사 문장을 Google 번역에 보내요.")
    if track_profiles:
        parser.add_argument("--source-language", choices=track_profiles,
                            help="가사 JSON이 없는 곡의 원문 언어를 골라요.")
    args = parser.parse_args()
    config["translation_backend"] = args.translation_backend
    args.offline = args.offline or args.merge is not None
    result = root / config["merge_output_folder"]
    sample_rate = int(global_number("MAKE_POP_MERGE_AUDIO_SAMPLE_RATE_HZ"))
    wav_options = ("-ar", str(sample_rate),
                   "-ac", str(global_number("MAKE_POP_MERGE_AUDIO_CHANNELS")))

    folders = folder_tracks(args.folder, flat=flat)
    empty_folder = "폴더에 MP3가 없어요." if flat else "하위 폴더에 MP3가 없어요."
    if args.timestamp:
        timestamp_output = config.get("merge_timestamp_output") or global_string(f"MAKE_{profile.upper()}_MERGE_TIMESTAMP_OUTPUT")
        output = root / timestamp_output
        if not write_timestamps(folders, output, sample_rate, wav_options, args.dry_run):
            print(f"{empty_folder} {args.folder}")
        return 0

    ffmpeg = None
    found = failed = False
    for folder, songs in folders:
        found = True
        if args.merge is None:
            for mp3 in songs:
                try:
                    track_config = config
                    if track_profiles and not mp3.with_suffix(".lyrics.json").exists() and not args.dry_run:
                        if args.source_language is None:
                            raise ValueError("--source-language로 곡의 원문 언어를 골라 주세요.")
                        track_config = language_settings(config, args.source_language)
                    create_json_only(ffmpeg, mp3, args, track_config, wav_options)
                except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
                    failed = True
                    print(f"가사 JSON을 만들지 못했어요.\n음원: {mp3.resolve()}\n"
                          f"가사 JSON: {mp3.with_suffix('.lyrics.json').resolve()}\n원인: {exc}", file=sys.stderr)
            continue

        try:
            images = dict(matching_pairs(folder))
            missing = [mp3.name for mp3 in songs if mp3 not in images]
            if missing:
                raise ValueError(f"같은 이름의 PNG나 JPG를 넣어 주세요. {', '.join(missing)}")
            missing = [mp3.with_suffix(".lyrics.json").name for mp3 in songs
                       if not mp3.with_suffix(".lyrics.json").is_file()]
            if missing:
                command = "--source-language로 원문 언어를 골라" if track_profiles else "--merge 없이 먼저"
                raise ValueError(f"{command} 실행해 가사 JSON을 만들어 주세요. {', '.join(missing)}")
            output = result / f"{folder.name}.mp4"
            count = None if args.merge is automatic_repeat else args.merge
            if args.dry_run:
                if count is None:
                    ffmpeg = ffmpeg or find_ffmpeg()
                    with tempfile.TemporaryDirectory(prefix="merge_preview_") as directory:
                        wav = Path(directory) / "audio.wav"
                        duration = sum(decode_wav(ffmpeg, mp3, wav, wav_options) for mp3 in songs)
                    count = automatic_repeat_count(duration, sample_rate)
                print_merge_plan(output, songs, count)
            else:
                ffmpeg = ffmpeg or find_ffmpeg()
                merge_folder(ffmpeg, [(mp3, images[mp3]) for mp3 in songs], output, args, config, wav_options,
                             sample_rate=sample_rate, count=count)
                print(f"영상을 만들었어요. {output}", flush=True)
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
            failed = True
            print(f"{folder.name} 영상을 만들지 못했어요.\n입력 폴더: {folder.resolve()}\n{exc}", file=sys.stderr)

    if not found:
        print(f"{empty_folder} {args.folder}")
    return int(failed)
