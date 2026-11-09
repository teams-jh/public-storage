"""하위 폴더마다 가사 JSON을 준비하고 여러 곡을 순서대로 이어 붙여요."""

import argparse
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
    parse_rect,
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


def merge_folder(ffmpeg, tracks, output, args, config, wav_options):
    from PIL import Image, ImageOps

    font_path = find_font(config, args.font)
    with tempfile.TemporaryDirectory(prefix="lyrics_merge_") as directory:
        work = Path(directory)
        audio_entries = []
        timeline = []
        duration = Decimal(0)
        canvas = None
        for index, (mp3, image) in enumerate(tracks):
            track = work / str(index)
            track.mkdir()
            wav = track / "audio.wav"
            track_duration = decode_wav(ffmpeg, mp3, wav, wav_options)
            cues = load_lyrics(mp3.with_suffix(".lyrics.json"), mp3, float(track_duration), args, config)
            with Image.open(image) as opened:
                background = ImageOps.exif_transpose(opened).convert("RGB")
            if canvas is None:
                canvas = background.size
            if background.size != canvas:
                background = ImageOps.pad(background, canvas, color="black")
            timeline.extend(render_track_frames(background, cues, track_duration, config, args.rect, font_path, track))
            audio_entries.append(f"file '{wav.relative_to(work).as_posix()}'\n")
            duration += track_duration

        (work / "audio.txt").write_text("".join(audio_entries) * args.merge, encoding="utf-8")
        repeated_frames = chain.from_iterable(repeat(timeline, args.merge))
        audio_input = ["-f", "concat", "-i", "audio.txt"]
        output.parent.mkdir(parents=True, exist_ok=True)
        # 완성된 영상만 같은 드라이브의 결과 폴더로 옮겨요.
        with tempfile.TemporaryDirectory(prefix="merge_", dir=output.parent) as staging:
            temporary = Path(staging) / "output.mp4"
            encode_timeline(ffmpeg, repeated_frames, audio_input, duration * args.merge, config, work, temporary)
            temporary.replace(output)


def folder_tracks(root):
    folders = sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name.casefold())
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
    root = Path(__file__).resolve().parent
    default_count = positive_count(str(global_number("MAKE_POP_MERGE_REPEAT_COUNT")))
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--merge", nargs="?", type=positive_count, const=default_count, metavar="횟수",
                      help=f"기존 가사 JSON으로 영상을 만들어요. 기본 반복 횟수는 {default_count}회예요.")
    mode.add_argument("--timestamp", action="store_true", help="폴더별 곡 시작 시각을 텍스트 파일 하나에 저장해요.")
    parser.add_argument("--folder", type=Path, default=root / config["merge_input_folder"],
                        help="곡을 모아 둔 하위 폴더들이 있는 경로예요.")
    parser.add_argument("--dry-run", action="store_true", help="결과를 저장하기 전에 미리 봐요.")
    parser.add_argument("--offline", action="store_true", help="가사를 만들 때 모델을 내려받거나 번역을 요청하지 않아요.")
    parser.add_argument("--font", type=Path, help="한글 TTF/OTF 폰트 경로예요.")
    parser.add_argument("--rect", type=parse_rect, default=tuple(config["rect"]), help="가사 영역 x,y,너비,높이 비율이에요.")
    parser.add_argument("--model", default=config["model"], help="Whisper 모델 이름 또는 로컬 모델 폴더예요.")
    parser.add_argument("--device", default=config["device"], choices=("cpu", "cuda", "auto"))
    parser.add_argument("--compute-type", default=config["compute_type"])
    parser.add_argument("--translation-backend", choices=("local", "google"), default=config["translation_backend"],
                        help="번역 방식을 골라요. google을 고르면 가사 문장을 Google 번역에 보내요.")
    args = parser.parse_args()
    config["translation_backend"] = args.translation_backend
    args.offline = args.offline or args.merge is not None
    result = root / config["merge_output_folder"]
    sample_rate = int(global_number("MAKE_POP_MERGE_AUDIO_SAMPLE_RATE_HZ"))
    wav_options = ("-ar", str(sample_rate),
                   "-ac", str(global_number("MAKE_POP_MERGE_AUDIO_CHANNELS")))

    folders = folder_tracks(args.folder)
    if args.timestamp:
        output = root / global_string(f"MAKE_{profile.upper()}_MERGE_TIMESTAMP_OUTPUT")
        if not write_timestamps(folders, output, sample_rate, wav_options, args.dry_run):
            print(f"하위 폴더에 MP3가 없어요. {args.folder}")
        return 0

    ffmpeg = None
    found = failed = False
    for folder, songs in folders:
        found = True
        if args.merge is None:
            for mp3 in songs:
                try:
                    create_json_only(ffmpeg, mp3, args, config, wav_options)
                except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
                    failed = True
                    print(f"{folder.name}/{mp3.name}의 가사 JSON을 만들지 못했어요.\n{exc}", file=sys.stderr)
            continue

        try:
            images = dict(matching_pairs(folder))
            missing = [mp3.name for mp3 in songs if mp3 not in images]
            if missing:
                raise ValueError(f"같은 이름의 PNG나 JPG를 넣어 주세요. {', '.join(missing)}")
            missing = [mp3.with_suffix(".lyrics.json").name for mp3 in songs
                       if not mp3.with_suffix(".lyrics.json").is_file()]
            if missing:
                raise ValueError(f"--merge 없이 먼저 실행해 가사 JSON을 만들어 주세요. {', '.join(missing)}")
            output = result / f"{folder.name}.mp4"
            print(f"{output.name} / {' → '.join(mp3.stem for mp3 in songs)} / 전체 {args.merge}회", flush=True)
            if not args.dry_run:
                ffmpeg = ffmpeg or find_ffmpeg()
                merge_folder(ffmpeg, [(mp3, images[mp3]) for mp3 in songs], output, args, config, wav_options)
                print(f"영상을 만들었어요. {output}", flush=True)
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
            failed = True
            print(f"{folder.name} 영상을 만들지 못했어요.\n{exc}", file=sys.stderr)

    if not found:
        print(f"하위 폴더에 MP3가 없어요. {args.folder}")
    return int(failed)
