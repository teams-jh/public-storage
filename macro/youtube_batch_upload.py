"""MP4와 반복된 [TITLE]/[CONTENT]/[TIME]을 순서대로 유튜브에 올려요."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time


def load_settings() -> dict:
    """설정은 저장소의 전역 상수에서만 읽어요."""
    source = (
        Path(__file__).resolve().parents[1]
        / "src" / "constants" / "global_constants.ts"
    ).read_text(encoding="utf-8-sig")
    match = re.search(
        r"export const YOUTUBE_BATCH_CONFIG\s*=\s*(\{.*?\})\s*as const;",
        source,
        re.DOTALL,
    )
    if not match:
        raise ValueError("global_constants.ts에서 유튜브 일괄 업로드 설정을 찾지 못했어요.")
    return json.loads(match.group(1))


def natural_sort_key(path: Path) -> tuple:
    """파일명의 숫자를 비교해 1, 2, 10 순서로 정렬해요."""
    return (
        tuple(
            (1, int(part)) if part.isdigit() else (0, part.casefold())
            for part in re.split(r"(\d+)", path.name)
        ),
        path.name,
    )


def build_upload_plan(input_file: Path, upload_directory: Path, settings: dict) -> list:
    """모든 개수와 게시물 형식을 검증한 뒤 업로드 목록을 반환해요."""
    if not input_file.is_file():
        raise ValueError(f"입력 파일을 찾지 못했어요: {input_file}")
    if not upload_directory.is_dir():
        raise ValueError(f"영상 폴더를 찾지 못했어요: {upload_directory}")

    videos = sorted(
        (path for path in upload_directory.iterdir()
         if path.is_file() and path.suffix.casefold() == settings["video_suffix"]),
        key=natural_sort_key,
    )
    lines = input_file.read_text(encoding="utf-8-sig").splitlines()
    sections = settings["sections"]
    counts = {section: sum(line.strip() == section for line in lines) for section in sections}
    if any(count != len(videos) for count in counts.values()):
        details = ", ".join(f"{section} {count}개" for section, count in counts.items())
        raise ValueError(
            f"파일 개수가 달라요. MP4 {len(videos)}개, {details}. "
            "개수를 맞춘 뒤 다시 실행해 주세요."
        )
    if not videos:
        raise ValueError("업로드할 MP4가 없어요. 영상과 입력 내용을 추가해 주세요.")

    # 구분선 유무와 관계없이 태그는 TITLE → CONTENT → TIME 순서여야 해요.
    entries = []
    current = None
    current_section = None
    expected = iter(sections)
    next_section = next(expected)
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == settings["separator"]:
            if current is None or next_section is not None:
                raise ValueError(f"{line_number}번째 줄의 구분선 앞에 제목·본문·시간을 모두 적어 주세요.")
            current_section = None
            continue
        if stripped in sections:
            if stripped == sections[0] and next_section is None:
                expected = iter(sections)
                next_section = next(expected)
            if stripped != next_section:
                raise ValueError(f"{line_number}번째 줄의 태그 순서를 확인해 주세요: {' → '.join(sections)}")
            if stripped == sections[0]:
                current = {section: [] for section in sections}
                entries.append(current)
            current_section = stripped
            next_section = next(expected, None)
        elif current_section is not None:
            current[current_section].append(line)
        elif stripped:
            raise ValueError(f"{line_number}번째 줄의 내용을 제목·본문·시간 태그 아래에 적어 주세요.")

    plan = []
    for index, (video, entry) in enumerate(zip(videos, entries), start=1):
        title, content, time_text = ("\n".join(entry[section]).strip() for section in sections)
        if not title:
            raise ValueError(f"{index}번째 [TITLE]에 제목을 적어 주세요.")
        scheduled_at = None
        if time_text:
            try:
                scheduled_at = datetime.strptime(time_text, settings["time_format"])
            except ValueError as error:
                raise ValueError(
                    f"{index}번째 [TIME]을 YYYY-MM-DD HH:MM 형식으로 적어 주세요: {time_text}"
                ) from error
            if scheduled_at <= datetime.now():
                raise ValueError(f"{index}번째 [TIME]이 이미 지났어요. 미래 시각을 적어 주세요: {time_text}")
        plan.append((video, {
            "title": title,
            "content": content,
            "time": time_text,
            "scheduled_at": scheduled_at,
            "tags": "",
        }))
    return plan


def upload_plan(plan: list, uploader, settings=None) -> bool:
    """실패한 영상은 대기 후 재시도하고, 재시도까지 실패하면 멈춰요."""
    settings = settings if settings is not None else load_settings()
    completed = 0
    unconfirmed = []
    for index, (video, metadata) in enumerate(plan, start=1):
        for attempt in range(settings["max_retries"] + 1):
            scheduled_at = metadata["scheduled_at"]
            if scheduled_at and scheduled_at <= datetime.now():
                print(f"{video.name}의 예약 시각이 지났어요. [TIME]을 수정한 뒤 다시 실행해 주세요.")
                return False
            print(f"[{index}/{len(plan)}] 업로드해요: {video.name}")
            try:
                success = uploader.upload(video, metadata)
            except Exception as error:
                print(f"업로드 중 문제가 생겼어요: {error}")
                success = False
            if success or getattr(uploader, "submission_unconfirmed", False) is True:
                break
            if attempt < settings["max_retries"]:
                delay = settings["retry_delay_seconds"]
                print(f"{video.name} 업로드에 실패했어요. {delay}초 뒤 같은 영상을 다시 시도해요.")
                time.sleep(delay)
        if not success and getattr(uploader, "submission_unconfirmed", False) is True:
            unconfirmed.append((video, metadata["title"]))
            print(f"{video.name}은 {settings['post_submit_wait_seconds']}초 뒤에도 완료를 확인하지 못했어요. 다음 영상으로 넘어가요.")
            continue
        if not success:
            print(
                f"{video.name} 업로드를 확인하지 못해 중단했어요. "
                f"완료 {completed}개 / 전체 {len(plan)}개. "
                "다시 실행하기 전에 YouTube Studio에서 게시 여부를 확인해 주세요."
            )
            return False
        completed += 1
        print(f"{video.name} 업로드를 마쳤어요.")
    print(f"유튜브 업로드 처리를 마쳤어요. 완료 {completed}개 / 완료 미확인 {len(unconfirmed)}개")
    if unconfirmed:
        print("완료를 확인하지 못한 영상 목록이에요. YouTube Studio에서 게시 여부를 확인해 주세요.")
        for video, title in unconfirmed:
            print(f" - {video.name} | 제목: {title}")
    return not unconfirmed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="유튜브 MP4 순차 일괄 업로드")
    parser.add_argument("--dry-run", action="store_true", help="업로드 없이 파일·입력 개수와 연결 순서를 확인해요")
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        base_dir = Path(__file__).resolve().parent
        plan = build_upload_plan(
            base_dir / settings["input_file"],
            base_dir / settings["upload_directory"],
            settings,
        )
    except (OSError, ValueError) as error:
        print(f"업로드를 시작하지 않았어요. {error}")
        return 1

    for index, (video, metadata) in enumerate(plan, start=1):
        print(f"{index}. {video.name} → {metadata['title']} / {metadata['time'] or '바로 게시'}")
    if args.dry_run:
        print(f"영상과 입력 {len(plan)}개의 연결을 확인했어요. 실제 업로드는 하지 않았어요.")
        return 0

    # 개수·내용 검증이 끝난 뒤에만 로그인/브라우저 관련 모듈을 불러와요.
    from platforms.youtube import YouTubeUploader
    from upload_pause import pause_on_escape

    uploader = YouTubeUploader(
        completion_wait_seconds=settings["completion_wait_seconds"],
        post_submit_wait_seconds=settings["post_submit_wait_seconds"],
    )
    return 0 if pause_on_escape(upload_plan)(plan, uploader, settings) else 1


if __name__ == "__main__":
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
    sys.exit(main())
