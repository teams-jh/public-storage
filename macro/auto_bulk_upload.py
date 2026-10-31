"""여러 SNS에 미디어와 ---로 나눈 게시물을 순서대로 업로드해요."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import time

from youtube_batch_upload import natural_sort_key


def load_settings() -> dict:
    source = (Path(__file__).resolve().parents[1] / "src/constants/global_constants.ts").read_text(encoding="utf-8-sig")
    match = re.search(r"export const AUTO_BULK_UPLOAD_CONFIG\s*=\s*(\{.*?\})\s*as const;", source, re.DOTALL)
    if not match:
        raise ValueError("전역 상수에서 일괄 업로드 설정을 찾지 못했어요.")
    return json.loads(match.group(1))


def configure_account(account: str, settings: dict) -> tuple[Path, Path]:
    """config와 플랫폼 모듈을 불러오기 전에 계정별 경로를 지정해요."""
    base_dir = Path(__file__).resolve().parent
    for key, value in settings["accounts"][account].items():
        os.environ[key] = str(base_dir / value) if key.endswith(("_FILE", "_DIR")) else value
    return Path(os.environ["MACRO_INPUT_FILE"]), Path(os.environ["MACRO_UPLOAD_DIR"])


def build_upload_plan(input_file: Path, upload_dir: Path, settings: dict) -> list:
    from config import SUPPORTED_EXTENSIONS, parse_input_text, parse_scheduled_time

    if not upload_dir.is_dir():
        raise ValueError(f"미디어 폴더를 찾지 못했어요: {upload_dir}")
    media = sorted((p for p in upload_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS), key=natural_sort_key)
    if len(media) < settings["minimum_media_count"]:
        raise ValueError(f"미디어가 {settings['minimum_media_count']}개 이상일 때 실행해 주세요: 현재 {len(media)}개")
    if not input_file.is_file():
        raise ValueError(f"입력 파일을 찾지 못했어요: {input_file}")
    blocks = re.split(r"(?m)^\s*" + re.escape(settings["separator"]) + r"\s*$", input_file.read_text(encoding="utf-8-sig").strip())
    if len(blocks) != len(media):
        raise ValueError(f"미디어 {len(media)}개와 게시물 {len(blocks)}개의 개수를 맞춰 주세요. 게시물은 --- 줄로 나눠 주세요.")
    plan = []
    for index, (path, block) in enumerate(zip(media, blocks), start=1):
        if not block.strip():
            raise ValueError(f"{index}번째 게시물이 비어 있어요. 구분선 사이에 내용을 적어 주세요.")
        seen = set()
        for line in block.splitlines():
            section = line.strip()
            if section in settings["sections"]:
                if section in seen:
                    raise ValueError(f"{index}번째 게시물에 {section}가 반복돼요. 게시물 사이에 ---를 넣어 주세요.")
                seen.add(section)
        metadata = parse_input_text(block)
        try:
            metadata["scheduled_at"] = parse_scheduled_time(metadata["time"])
        except ValueError as error:
            raise ValueError(f"{index}번째 [TIME]을 YYYY-MM-DD HH:MM 형식으로 적어 주세요.") from error
        if metadata["scheduled_at"] and metadata["scheduled_at"] <= datetime.now():
            raise ValueError(f"{index}번째 예약 시각이 지났어요. [TIME]을 수정해 주세요.")
        plan.append((path, metadata))
    return plan


def upload_plan(plan: list, selected: list, uploaders: dict, settings: dict, runner=None) -> bool:
    """실패한 업로드는 기록하고 모든 파일·플랫폼을 처리한 뒤 결과를 보여줘요."""
    from config import get_media_type

    failures = []
    skipped = []
    completed = 0
    for platform in selected:
        if platform in settings["disabled_platforms"]:
            print(f"{platform} 업로드는 비활성화되어 건너뛰어요.")
            continue
        targets = [(path, metadata) for path, metadata in plan
                   if platform not in settings["video_only_platforms"] or get_media_type(path) == "video"]
        if not targets:
            print(f"{platform}에 올릴 동영상이 없어 건너뛰어요.")
            continue
        uploader = None
        for index, (path, metadata) in enumerate(targets, start=1):
            try:
                if metadata["scheduled_at"] and metadata["scheduled_at"] <= datetime.now():
                    raise ValueError("예약 시각이 지났어요. [TIME]을 수정해 주세요.")
                print(f"[{platform} {index}/{len(targets)}] {path.name} 업로드를 시작해요.")
                if runner is None and uploader is None:
                    uploader = (uploaders[platform](completion_wait_seconds=settings["youtube_completion_wait_seconds"])
                                if platform == "youtube" else uploaders[platform]())
                result = (runner(platform, path, metadata.copy()) if runner is not None
                          else uploader.upload(path, metadata.copy()))
                if result is None:
                    skipped.append((platform, path, metadata["title"]))
                    uploader = None
                    print(f"[{platform}] {path.name} 업로드를 종료하고 다음 파일로 넘어가요. 이미 게시됐다면 게시물은 유지돼요.")
                    continue
                if not result:
                    raise RuntimeError("업로드 완료를 확인하지 못했어요. 화면의 로그와 게시 여부를 확인해 주세요.")
            except Exception as error:
                failures.append((platform, path, metadata["title"], str(error)))
                uploader = None
                print(f"[{platform}] {path.name} 업로드에 실패했어요: {error} 다음 업로드로 넘어가요.")
                continue
            completed += 1
            print(f"[{platform}] {path.name} 업로드를 마쳤어요.")
            if platform == "youtube" and index < len(targets):
                delay = settings["youtube_interval_seconds"]
                print(f"{delay}초 뒤 다음 유튜브 영상을 업로드해요.")
                time.sleep(delay)

    print(f"\n업로드 목록 처리를 마쳤어요. 완료 {completed}개 / 실패 {len(failures)}개 / 사용자 건너뛰기 {len(skipped)}개")
    if failures:
        print("\n실패한 업로드 목록이에요.")
        for platform, path, title, reason in failures:
            print(f" - [{platform}] {path.name} | 제목: {title} | 이유: {reason}")
        print("다시 실행하기 전에 실패한 항목의 게시 여부를 확인해 주세요.")
    if skipped:
        print("\nCtrl+D로 건너뛴 업로드 목록이에요.")
        for platform, path, title in skipped:
            print(f" - [{platform}] {path.name} | 제목: {title}")
    return not failures


def main(argv=None, account="first") -> int:
    parser = argparse.ArgumentParser(description="SNS 미디어 일괄 업로드")
    parser.add_argument("--platform", "-p", default="all", choices=["all", "naver", "instagram", "threads", "x", "facebook", "tiktok", "youtube"])
    parser.add_argument("--dry-run", action="store_true", help="업로드 없이 파일과 게시물 연결을 확인해요")
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        input_file, upload_dir = configure_account(account, settings)
        plan = build_upload_plan(input_file, upload_dir, settings)
    except (OSError, ValueError) as error:
        print(f"업로드를 시작하지 않았어요. {error}")
        return 1
    for index, (path, metadata) in enumerate(plan, start=1):
        print(f"{index}. {path.name} → {metadata['title']} / {metadata['time'] or '바로 게시'}")
    if args.dry_run:
        print("파일과 게시물 연결을 확인했어요. 실제 업로드는 하지 않았어요.")
        return 0

    from bulk_upload_control import BulkUploadControl

    selected = settings["platforms"] if args.platform == "all" else [args.platform]
    try:
        with BulkUploadControl(settings) as control:
            return 0 if upload_plan(plan, selected, {}, settings, runner=control.run) else 1
    except RuntimeError as error:
        print(f"업로드를 멈췄어요. {error}")
        return 1


if __name__ == "__main__":
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
    sys.exit(main())
