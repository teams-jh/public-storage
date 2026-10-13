"""하나의 게시물에 폴더의 모든 이미지를 첨부하는 공통 실행 코드."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def _load_images(upload_dir: Path) -> list[Path]:
    """지원하는 이미지 파일만 이름순으로 가져옵니다."""
    from config import IMAGE_EXTENSIONS

    if not upload_dir.is_dir():
        return []
    return sorted(
        (path for path in upload_dir.iterdir()
         if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.name.casefold(),
    )


def _prepare_scheduled_time(metadata: dict) -> None:
    from config import parse_scheduled_time

    scheduled_text = metadata.get("time", "").strip()
    if not scheduled_text:
        metadata["scheduled_at"] = None
        return
    try:
        scheduled_at = parse_scheduled_time(scheduled_text)
    except ValueError as exc:
        raise ValueError(f"[TIME] 형식을 확인해 주세요: {scheduled_text} (YYYY-MM-DD HH:MM)") from exc
    if scheduled_at <= datetime.now():
        raise ValueError(f"[TIME]에 미래 시각을 입력해 주세요: {scheduled_text}")
    metadata["scheduled_at"] = scheduled_at


def _upload_group(uploader, images: list[Path], metadata: dict) -> bool:
    """기존 게시 흐름의 파일 선택 단계에 전체 이미지 목록을 전달합니다.

    Playwright의 파일 선택 메서드만 이 호출 동안 교체합니다. 단일 파일을 받는
    기존 플랫폼 업로더의 로그인, 문구, 예약, 게시 완료 확인 로직은 그대로 사용합니다.
    """
    from playwright.sync_api import Locator
    from image_selection import set_and_verify_images

    first_image = str(images[0].resolve())
    original_set_input_files = Locator.set_input_files
    attachment_attempts = 0

    def attach_all_images(locator, files, *args, **kwargs):
        nonlocal attachment_attempts
        if isinstance(files, (str, Path)) and str(Path(files).resolve()) == first_image:
            set_and_verify_images(locator, images, original_set_input_files, *args, **kwargs)
            attachment_attempts += 1
            return None
        return original_set_input_files(locator, files, *args, **kwargs)

    with patch.object(Locator, "set_input_files", attach_all_images):
        uploaded = uploader.upload(images[0], metadata)

    if uploaded and not attachment_attempts:
        print(f"❌ [{uploader.platform_name}] 이미지 첨부 단계를 확인하지 못했어요.")
        return False
    return bool(uploaded)


def run(input_file: Path, upload_dir: Path) -> int:
    """이미지 묶음을 선택한 플랫폼에 한 게시물씩 업로드합니다."""
    from config import parse_input_file
    from platforms import InstagramUploader, ThreadsUploader, TwitterXUploader, TikTokUploader
    from youtube_image_post import YouTubeImagePostUploader

    parser = argparse.ArgumentParser(description="이미지 여러 장을 한 게시물로 올려요")
    parser.add_argument(
        "--platform", "-p",
        choices=("all", "instagram", "threads", "x", "tiktok", "facebook", "youtube", "naver"),
        default="all",
        help="업로드할 플랫폼 (기본값: all)",
    )
    args = parser.parse_args()

    if not input_file.is_file():
        print(f"❌ 입력 파일을 찾지 못했어요: {input_file}")
        return 1
    images = _load_images(upload_dir)
    if not images:
        print(f"❌ 업로드할 이미지가 없어요: {upload_dir}")
        return 1

    metadata = parse_input_file(input_file)
    # 이미지 게시물에서 화면 비율을 선택할 때는 입력 파일 값과 관계없이 정사각형을 사용해요.
    metadata["ratio"] = "1:1"
    try:
        _prepare_scheduled_time(metadata)
    except ValueError as exc:
        print(f"❌ {exc}")
        return 1

    print(f"📄 입력 파일: {input_file.name}")
    print(f"🖼️ 이미지 {len(images)}장: {', '.join(image.name for image in images)}")
    print("📐 이미지 게시 비율: 1:1")
    if metadata["scheduled_at"]:
        print(f"⏰ 예약 시각: {metadata['scheduled_at']:%Y-%m-%d %H:%M}")

    platform_map = {
        "instagram": InstagramUploader,
        "threads": ThreadsUploader,
        "x": TwitterXUploader,
        "tiktok": TikTokUploader,
        "youtube": YouTubeImagePostUploader,
    }
    if args.platform == "all":
        selected = tuple(platform_map)
    elif args.platform not in platform_map:
        print(f"⏭️ {args.platform}은 이미지 묶음 업로드 대상이 아니에요.")
        return 0
    else:
        selected = (args.platform,)

    failed = False
    for platform in selected:
        if platform == "x" and len(images) >= 5:
            print(f"⏭️ X: 이미지가 {len(images)}장이어서 업로드하지 않아요. 4장 이하로 줄여 주세요.")
            continue
        uploader = platform_map[platform]()
        print(f"▶ {uploader.platform_name}: 이미지 {len(images)}장을 올리는 중이에요...")
        try:
            if platform == "youtube":
                success = uploader.upload(images, metadata)
            else:
                success = _upload_group(uploader, images, metadata)
        except Exception as exc:
            print(f"❌ {uploader.platform_name}: {exc}")
            success = False
        print(f"{'✅' if success else '❌'} {uploader.platform_name}: {'업로드했어요' if success else '업로드하지 못했어요'}")
        failed |= not success

    return 1 if failed else 0
