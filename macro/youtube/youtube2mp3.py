"""
YouTube to MP3 Downloader
YouTube 영상 링크 또는 link.txt 파일의 링크 목록을 입력받아 고음질 MP3 파일로 변환 및 저장하는 스크립트입니다.
"""

import os
import sys
import shutil
import argparse
import warnings
from pathlib import Path
from typing import Optional, List

# Windows 터미널 한글 인코딩 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Requests / urllib3 버전 불일치 경고 메시지 숨김
warnings.filterwarnings("ignore")

DEFAULT_LINK_FILE = Path(__file__).resolve().parent / "link.txt"
DEFAULT_DOWNLOADS_DIR = Path(__file__).resolve().parent / "downloads"


def get_ffmpeg_path() -> Optional[str]:
    """
    시스템 또는 파이썬 패키지(imageio_ffmpeg)에서 ffmpeg 실행 파일 경로를 탐색합니다.
    """
    # 1. 시스템 환경변수 PATH에서 ffmpeg 확인
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 2. imageio-ffmpeg 내장 바이너리 확인
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_exe and os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
    except ImportError:
        pass

    # 3. 현재 스크립트 위치의 ffmpeg.exe 확인
    local_ffmpeg = Path(__file__).resolve().parent / "ffmpeg.exe"
    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    return None


def progress_hook(d: dict):
    """
    다운로드 및 변환 진행 상황을 터미널에 표시합니다.
    """
    status = d.get("status")
    if status == "downloading":
        percent = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("_eta_str", "").strip()
        total_bytes = d.get("_total_bytes_str", "") or d.get("_total_bytes_estimate_str", "")
        print(f"\r  ⏳ 다운로드 진행 중: {percent} [{total_bytes}] (속도: {speed}, 남은시간: {eta})   ", end="", flush=True)
    elif status == "finished":
        print("\n  🔄 원본 다운로드 완료! MP3 변환 및 태그 작업 중...")


def load_links_from_file(file_path: Path) -> List[str]:
    """
    파일에서 주석(#, //)과 빈 줄을 제외한 유효한 YouTube URL 목록을 읽어옵니다.
    """
    if not file_path.exists():
        return []

    links: List[str] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                    continue
                # http 또는 https 로 시작하는 링크만 추가
                if stripped.startswith("http://") or stripped.startswith("https://"):
                    links.append(stripped)
    except Exception as e:
        print(f"⚠️ 파일({file_path.name})을 읽는 중 오류가 발생했습니다: {e}")

    return links


def mark_links_as_completed(file_path: Path, completed_links: List[str]):
    """
    다운로드 완료된 링크 라인 앞에 '# [완료]' 주석을 달아 중복 다운로드를 방지합니다.
    """
    if not file_path.exists() or not completed_links:
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        completed_set = set(completed_links)
        new_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped in completed_set and not stripped.startswith("#"):
                new_lines.append(f"# [완료] {line}")
            else:
                new_lines.append(line)

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"📝 {file_path.name} 파일에 다운로드 완료 표시(# [완료])를 남겼어요.")
    except Exception as e:
        print(f"⚠️ {file_path.name} 파일 업데이트 중 오류가 발생했습니다: {e}")


def download_youtube_to_mp3(
    url: str,
    output_dir: Path,
    quality: str = "192",
    allow_playlist: bool = False
) -> bool:
    """
    단일 YouTube URL을 받아 MP3 파일로 변환 및 다운로드합니다.
    """
    try:
        import yt_dlp
    except ImportError:
        print("\n❌ 'yt-dlp' 패키지가 설치되어 있지 않습니다.")
        print("💡 다음 명령어로 설치해 주세요: pip install -r requirements.txt")
        return False

    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("\n❌ ffmpeg를 찾을 수 없습니다.")
        print("💡 다음 명령어로 imageio-ffmpeg를 설치하거나 시스템에 ffmpeg를 설치해 주세요:")
        print("   pip install imageio-ffmpeg")
        return False

    # 출력 폴더 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_file = output_dir / ".download_archive.txt"

    # yt-dlp 옵션 설정
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            },
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            },
        ],
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "windowsfilenames": True,
        "ffmpeg_location": ffmpeg_path,
        "noplaylist": not allow_playlist,
        "quiet": False,
        "no_warnings": True,
        "download_archive": str(archive_file),
        "ignoreerrors": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        "progress_hooks": [progress_hook],
    }

    print(f"\n==================================================")
    print(f"🔗 링크: {url}")
    print(f"📁 저장 경로: {output_dir.resolve()}")
    print(f"🎵 음질 설정: {quality} kbps")
    print(f"==================================================")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # download=True로 한 번에 추출 및 다운로드 진행 (이중 요청 방지 및 403 우회)
            info = ydl.extract_info(url, download=True)
            if not info:
                print("ℹ️ 이미 다운로드된 영상이거나 건너뛴 영상입니다.")
                return True

            title = info.get("title", "알 수 없는 제목")
            duration = info.get("duration", 0)
            mins, secs = divmod(duration, 60)
            uploader = info.get("uploader", "알 수 없음")

            print(f"\n🎬 제목: {title}")
            print(f"👤 채널: {uploader} | ⏱️ {mins}분 {secs}초")

        print(f"✅ MP3 변환 및 다운로드가 완료되었어요!\n")
        return True

    except Exception as e:
        print(f"\n❌ 다운로드 중 오류가 발생했습니다: {e}\n")
        return False


def download_multiple_links(
    urls: List[str],
    output_dir: Path,
    quality: str = "192",
    allow_playlist: bool = False,
    source_file: Optional[Path] = None,
) -> int:
    """
    여러 YouTube 링크를 순차적으로 다운로드합니다.
    다운로드 완료 시마다 즉시 파일에 반영하여 언제든 중단 후 이어받기가 가능합니다.
    """
    total = len(urls)
    print(f"\n🚀 총 {total}개의 링크를 순차적으로 다운로드합니다.")

    successful_links: List[str] = []

    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{total}] 작업 시작 -----------------------------")
        success = download_youtube_to_mp3(
            url,
            output_dir=output_dir,
            quality=quality,
            allow_playlist=allow_playlist,
        )
        if success:
            successful_links.append(url)
            # 한 곡 완료 시마다 즉시 link.txt에 완료 표시를 남겨 중단 시에도 이어받기 가능
            if source_file:
                mark_links_as_completed(source_file, [url])

    print("\n" + "=" * 55)
    print(f"✨ 작업 완료: 총 {total}개 중 {len(successful_links)}개 다운로드 성공!")
    print("=" * 55)

    return len(successful_links)


def interactive_mode(output_dir: Path, quality: str = "192"):
    """
    직접 콘솔에서 링크를 입력받아 반복 다운로드하는 대화형 모드입니다.
    """
    print("\n" + "=" * 55)
    print("🎵  YouTube to MP3 다운로더 (직접 입력 모드)  🎵")
    print("=" * 55)
    print(f"• 기본 저장 경로: {output_dir.resolve()}")
    print("• link.txt 파일에 링크를 적어두면 실행 즉시 자동 다운로드됩니다.")
    print("• 종료하려면 'q' 또는 'exit'를 입력하세요.")

    while True:
        try:
            url_input = input("\n👉 YouTube 링크를 입력해 주세요 (종료: q): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 프로그램을 종료합니다.")
            break

        if not url_input:
            continue

        if url_input.lower() in ("q", "quit", "exit", "종료"):
            print("\n👋 프로그램을 종료합니다.")
            break

        download_youtube_to_mp3(url_input, output_dir=output_dir, quality=quality)


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 동영상을 고음질 MP3 파일로 변환하여 다운로드합니다."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="다운로드할 YouTube 링크 (여러 개 입력 가능). 비워둘 경우 link.txt의 링크를 자동으로 다운로드합니다.",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="링크가 적힌 텍스트 파일 경로 (기본 link.txt 대신 특정 파일을 지정할 때 사용)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_DOWNLOADS_DIR),
        help=f"MP3 저장 디렉토리 경로 (기본값: {DEFAULT_DOWNLOADS_DIR})",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="192",
        choices=["128", "192", "256", "320"],
        help="MP3 오디오 음질 kbps (기본값: 192)",
    )
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="재생목록 URL인 경우 전체 재생목록 다운로드 허용",
    )

    args = parser.parse_args()
    target_output_dir = Path(args.output)

    # 1. -f 옵션으로 특정 파일을 명시한 경우
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {file_path.resolve()}")
            return
        links = load_links_from_file(file_path)
        if not links:
            print(f"⚠️ {file_path.name} 파일에 유효한 링크가 없습니다.")
            return
        download_multiple_links(
            links,
            output_dir=target_output_dir,
            quality=args.quality,
            allow_playlist=args.playlist,
            source_file=file_path,
        )
        return

    # 2. CLI 인자로 URL을 직접 넘긴 경우
    if args.urls:
        download_multiple_links(
            args.urls,
            output_dir=target_output_dir,
            quality=args.quality,
            allow_playlist=args.playlist,
        )
        return

    # 3. 인자가 없는 경우: link.txt 확인
    if DEFAULT_LINK_FILE.exists():
        links_in_file = load_links_from_file(DEFAULT_LINK_FILE)
        if links_in_file:
            print("\n" + "=" * 55)
            print("🎵  YouTube to MP3 다운로더  🎵")
            print("=" * 55)
            print(f"📄 'link.txt'에서 {len(links_in_file)}개의 링크를 발견했어요!")
            for idx, lk in enumerate(links_in_file[:5], 1):
                print(f"   {idx}. {lk}")
            if len(links_in_file) > 5:
                print(f"   ... 외 {len(links_in_file) - 5}개")
            print("⚡ 입력 대기 없이 바로 전체 다운로드를 시작합니다.")
            print("=" * 55)

            download_multiple_links(
                links_in_file,
                output_dir=target_output_dir,
                quality=args.quality,
                allow_playlist=args.playlist,
                source_file=DEFAULT_LINK_FILE,
            )
            return

    # 4. link.txt에 유효한 링크가 없는 경우: 직접 입력 대화형 모드로 실행
    print("\nℹ️ 'link.txt'에 다운로드할 링크가 없습니다.")
    interactive_mode(output_dir=target_output_dir, quality=args.quality)


if __name__ == "__main__":
    main()
