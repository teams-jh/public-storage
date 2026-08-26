import sys
import os
import argparse
from pathlib import Path

# Windows 콘솔 한글 깨짐 방지
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from config import parse_input_file, get_target_media, get_media_type, UPLOAD_DIR, INPUT_FILE
from platforms import (
    InstagramUploader,
    ThreadsUploader,
    TwitterXUploader,
    FacebookUploader,
    TikTokUploader,
    YouTubeUploader,
)

PLATFORM_MAP = {
    "instagram": InstagramUploader,
    "threads": ThreadsUploader,
    "x": TwitterXUploader,
    "facebook": FacebookUploader,
    "tiktok": TikTokUploader,
    "youtube": YouTubeUploader,
}

MEDIA_TYPE_NAMES = {
    "video": "동영상 (Video)",
    "image": "사진 (Image)",
}

def print_banner():
    print("=" * 65)
    print(" 🚀 SNS 통합 미디어 자동 업로드 매크로 (Multi-Platform Uploader)")
    print(" (동영상 및 사진/이미지 파일 지원)")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="SNS 미디어(동영상/사진) 자동 업로드 매크로")

    parser.add_argument(
        "--platform", "-p",
        choices=["all", "instagram", "threads", "x", "facebook", "tiktok", "youtube"],
        default="all",
        help="업로드할 대상 플랫폼 (기본값: all)"
    )
    parser.add_argument(
        "--file", "--media", "-m", "-f", "--video", "-v",
        dest="media_file",
        type=str,
        default=None,
        help="특정 미디어 파일 지정 (지정하지 않을 경우 upload 폴더 내 첫 번째 미디어 자동 선택)"
    )
    args = parser.parse_args()

    print_banner()

    # 1. input.txt 내용 확인
    metadata = parse_input_file(INPUT_FILE)
    print(f"\n📄 [1] input.txt 로드 완료:")
    print(f" - 제목(Title): {metadata['title']}")
    print(f" - 내용 요약:\n{metadata['content'][:120]}...")
    if metadata.get('ratio'):
        print(f" - 비율(Ratio): {metadata['ratio']}")
    if metadata['tags']:
        print(f" - 태그(Tags): {metadata['tags']}")

    # 2. 미디어 파일(동영상/사진/GIF) 확인
    target_media: Path | None = None
    if args.media_file:
        candidate = Path(args.media_file)
        if candidate.exists():
            target_media = candidate
        else:
            print(f"\n❌ 지정한 미디어 파일을 찾을 수 없습니다: {args.media_file}")
            sys.exit(1)
    else:
        media_list = get_target_media(UPLOAD_DIR)
        if not media_list:
            print(f"\n⚠️ 'macro/upload/' 폴더에 업로드할 미디어 파일이 없습니다.")
            print(f" 👉 동영상(.mp4, .mov 등), 사진(.jpg, .png 등), GIF(.gif) 파일을 macro/upload/ 폴더에 넣고 다시 실행해 주세요.")
            sys.exit(1)
        target_media = media_list[0]
        media_type = get_media_type(target_media)
        media_type_name = MEDIA_TYPE_NAMES.get(media_type, "미디어")
        print(f"\n🎬 [2] 업로드 대상 {media_type_name} 발견 ({len(media_list)}개 중 1번째 선택):")
        print(f" - 파일명: {target_media.name}")
        print(f" - 미디어 종류: {media_type_name}")
        print(f" - 경로: {target_media.resolve()}")

    # 3. 대상 플랫폼 선정
    if args.platform == "all":
        # 페이스북은 현재 비활성화되어 제외
        selected_platforms = [k for k in PLATFORM_MAP.keys() if k != "facebook"]
    else:
        selected_platforms = [args.platform]

    print(f"\n🎯 [3] 업로드 대상 플랫폼: {', '.join(selected_platforms)}")
    if args.platform == "all":
        print(" (ℹ️ 페이스북은 현재 비활성화되어 건너뜁니다)")
    print("-" * 65)

    results = {}
    for plat_key in selected_platforms:
        if plat_key == "facebook":
            print(f"\n▶ [Facebook] ⚠️ 페이스북 업로드 기능은 현재 비활성화되어 있어 건너뜁니다.")
            results["Facebook"] = "⏸️ 비활성화 (건너뜀)"
            continue

        if plat_key == "youtube" and media_type != "video":
            print(f"\n▶ [YouTube] ⚠️ YouTube는 동영상 전용 플랫폼입니다. 현재 파일({media_type_name})은 업로드를 건너뜁니다.")
            results["YouTube"] = "⏭️ 건너뜀 (동영상 전용)"
            continue

        uploader_cls = PLATFORM_MAP[plat_key]
        uploader = uploader_cls()
        
        print(f"\n▶ [{uploader.platform_name}] 업로드 진행 중...")
        try:
            success = uploader.upload(target_media, metadata)
            results[uploader.platform_name] = "✅ 성공" if success else "❌ 실패"
        except Exception as e:
            print(f"❌ [{uploader.platform_name}] 에러 발생: {e}")
            results[uploader.platform_name] = f"❌ 실패 ({e})"


    # 4. 결과 요약 리포트
    print("\n" + "=" * 65)
    print(" 📊 전체 업로드 결과 요약")
    print("=" * 65)
    for plat, status in results.items():
        print(f" - {plat:12}: {status}")
    print("=" * 65)
    print("작업이 완료되었습니다.\n")

if __name__ == "__main__":
    main()

