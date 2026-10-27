"""같은 이름의 MP3와 이미지를 한 시간 초과 길이의 MP4로 변환해요."""

import argparse
from decimal import Decimal
from pathlib import Path
import re
import shutil
import subprocess
import sys


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def global_number(name: str) -> Decimal:
    """프로젝트의 전역 상수에서 이 매크로의 숫자 설정을 읽어요."""
    constants_file = Path(__file__).resolve().parents[2] / "src" / "constants" / "global_constants.ts"
    source = constants_file.read_text(encoding="utf-8")
    match = re.search(rf"export const {re.escape(name)}\s*=\s*(\d+(?:\.\d+)?)\s*;", source)
    if match is None:
        raise ValueError(f"{name} 설정을 찾을 수 없어요: {constants_file}")
    return Decimal(match.group(1))


def find_ffmpeg() -> str:
    """시스템 FFmpeg 또는 기존 매크로에서 쓰는 imageio-ffmpeg를 찾아요."""
    executable = shutil.which("ffmpeg")
    if executable:
        return executable

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError("FFmpeg를 찾을 수 없어요. pip install imageio-ffmpeg를 실행해 주세요.") from exc


def audio_duration_seconds(ffmpeg: str, mp3: Path) -> Decimal:
    """FFmpeg의 입력 정보에서 MP3 길이를 읽어요."""
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(mp3)],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if match is None:
        raise ValueError(f"MP3 길이를 읽을 수 없어요: {mp3.name}\n{result.stderr.strip()}")
    hours, minutes, seconds = match.groups()
    duration = Decimal(hours) * 3600 + Decimal(minutes) * 60 + Decimal(seconds)
    if duration <= 0:
        raise ValueError(f"MP3 길이가 0초예요: {mp3.name}")
    return duration


def repeat_count(duration: Decimal, minimum: Decimal, rounding: Decimal) -> int:
    """FFmpeg의 0.01초 표시 오차를 고려해 기준을 확실히 초과해요."""
    shortest_possible = duration - rounding
    if shortest_possible <= 0:
        raise ValueError("MP3 길이가 너무 짧아 반복 횟수를 계산할 수 없어요.")
    return int(minimum // shortest_possible) + 1


def matching_pairs(folder: Path):
    """같은 파일명을 가진 MP3와 PNG/JPG 쌍을 찾아요. 둘 다 있으면 PNG를 써요."""
    files = sorted(folder.iterdir(), key=lambda path: path.name.casefold())
    images = {}
    for suffix in (".jpg", ".png"):
        for file in files:
            if file.is_file() and file.suffix.lower() == suffix:
                images[file.stem] = file

    for mp3 in files:
        if mp3.is_file() and mp3.suffix.lower() == ".mp3" and mp3.stem in images:
            yield mp3, images[mp3.stem]


def create_mp4(
    ffmpeg: str, mp3: Path, image: Path, output: Path, loops: int, fps: int, bitrate: int
) -> None:
    """이미지를 고정 화면으로 두고 MP3 전체를 필요한 횟수만큼 반복해요."""
    temporary = output.with_name(f"{output.stem}.partial.mp4")
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-stats", "-y",
        "-loop", "1", "-framerate", str(fps), "-i", str(image),
        "-stream_loop", str(loops - 1), "-i", str(mp3),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-tune", "stillimage",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", f"{bitrate}k", "-shortest", "-movflags", "+faststart",
        str(temporary),
    ]
    try:
        subprocess.run(command, check=True)
        temporary.replace(output)
    except (OSError, subprocess.CalledProcessError):
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="반복 횟수만 확인하고 MP4를 만들지 않아요")
    args = parser.parse_args()

    folder = Path(__file__).resolve().parent
    pairs = list(matching_pairs(folder))
    if not pairs:
        print("이름이 같은 MP3와 PNG/JPG 파일이 없어요.")
        return 0

    try:
        minimum = global_number("MAKE_MP4_MIN_DURATION_SECONDS")
        rounding = global_number("MAKE_MP4_DURATION_ROUNDING_SECONDS")
        fps = int(global_number("MAKE_MP4_VIDEO_FPS"))
        bitrate = int(global_number("MAKE_MP4_AUDIO_BITRATE_KBPS"))
        ffmpeg = find_ffmpeg()
    except (OSError, ValueError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    failed = False
    for mp3, image in pairs:
        output = mp3.with_suffix(".mp4")
        if output.exists():
            print(f"건너뛰어요 (이미 있음): {output.name}")
            continue

        try:
            duration = audio_duration_seconds(ffmpeg, mp3)
            loops = repeat_count(duration, minimum, rounding)
            print(f"{output.name}: {image.name} / MP3 {loops}회 반복 (약 {duration * loops / 60:.1f}분)", flush=True)
            if not args.dry_run:
                create_mp4(ffmpeg, mp3, image, output, loops, fps, bitrate)
                print(f"만들었어요: {output.name}")
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            failed = True
            print(f"만들지 못했어요: {output.name} ({exc})", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
