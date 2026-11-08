"""하위 폴더마다 가사 JSON을 준비하고 여러 곡을 순서대로 이어 붙여요."""

import argparse
from decimal import Decimal
from itertools import chain, repeat
from pathlib import Path
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
from make_mp4 import find_ffmpeg, global_number, matching_pairs


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


def main(profile="k_pop"):
    config = settings(profile)
    root = Path(__file__).resolve().parent
    default_count = positive_count(str(global_number("MAKE_POP_MERGE_REPEAT_COUNT")))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merge", nargs="?", type=positive_count, const=default_count, metavar="횟수",
                        help=f"기존 가사 JSON으로 영상을 만들어요. 기본 반복 횟수는 {default_count}회예요.")
    parser.add_argument("--folder", type=Path, default=root / config["merge_input_folder"],
                        help="곡을 모아 둔 하위 폴더들이 있는 경로예요.")
    parser.add_argument("--dry-run", action="store_true", help="만들 파일과 곡 순서만 보여줘요.")
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
    wav_options = ("-ar", str(global_number("MAKE_POP_MERGE_AUDIO_SAMPLE_RATE_HZ")),
                   "-ac", str(global_number("MAKE_POP_MERGE_AUDIO_CHANNELS")))

    ffmpeg = None
    found = failed = False
    folders = sorted((path for path in args.folder.iterdir() if path.is_dir()), key=lambda path: path.name.casefold())
    for folder in folders:
        songs = sorted(
            (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".mp3"),
            key=lambda path: path.name.casefold(),
        )
        if not songs:
            continue
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
