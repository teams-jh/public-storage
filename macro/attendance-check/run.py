import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

from config import (
    SITE_INFO_PATH,
    DEFAULT_USER_AGENT,
    DEFAULT_VIEWPORT,
    load_site_info,
    setup_logger,
)
from sites import get_checker, SITE_REGISTRY

logger = setup_logger("attendance_runner")


# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_summary_table(results: List[Dict[str, Any]]):
    """
    실행 결과를 터미널에 요약 표로 출력합니다.
    """
    print("\n" + "=" * 70)
    print(f"{'사이트':<15} | {'상태':<12} | {'결과 메시지'}")
    print("-" * 70)

    for res in results:
        name = res.get("site_name", "미상")
        status = res.get("status", "UNKNOWN")
        msg = res.get("message", "")

        status_display = {
            "SUCCESS": "[성공]",
            "ALREADY_CHECKED": "[이미완료]",
            "LOGIN_FAILED": "[로그인실패]",
            "CHECK_FAILED": "[출석실패]",
            "LOGIN_REQUIRED": "[로그인필요]",
            "ERROR": "[오류]",
        }.get(status, f"[{status}]")

        print(f"{name:<15} | {status_display:<12} | {msg}")

    print("=" * 70 + "\n")


def run_attendance(
    target_site: str = None,
    headed: bool = False,
    info_file_path: Path = SITE_INFO_PATH
) -> int:
    """
    출석체크 자동화 메인 함수
    """
    try:
        sites_config = load_site_info(info_file_path)
    except Exception as e:
        logger.error(f"설정 로드 실패: {e}")
        return 1

    if not sites_config:
        logger.warning("site_info.json에 등록된 사이트 정보가 없습니다.")
        return 0

    # 실행 대상 필터링
    run_list = []
    for site in sites_config:
        name = site.get("name", "")
        site_key = site.get("site_key", "")
        enabled = site.get("enabled", True)

        if not enabled:
            logger.info(f"[{name or site_key}] 비활성화(enabled: false)되어 있어 건너뜁니다.")
            continue

        if target_site:
            if target_site.lower() not in [name.lower(), site_key.lower()]:
                continue

        run_list.append(site)

    if not run_list:
        if target_site:
            logger.warning(f"지정한 사이트 '{target_site}'를 site_info.json에서 찾을 수 없습니다.")
        else:
            logger.warning("실행 가능한 활성 사이트가 없습니다.")
        return 0

    logger.info(f"총 {len(run_list)}개 사이트 출석체크를 시작합니다. (헤드리스: {not headed})")

    results: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport=DEFAULT_VIEWPORT,
        )

        for site_info in run_list:
            site_name = site_info.get("name", "")
            site_key = site_info.get("site_key", "")

            checker = get_checker(site_key) or get_checker(site_name)
            if not checker:
                logger.error(f"'{site_name or site_key}' 사이트를 지원하는 출석체크 핸들러가 구현되지 않았습니다.")
                results.append({
                    "site_name": site_name or site_key,
                    "status": "ERROR",
                    "message": "지원하지 않는 사이트 핸들러 (sites 디렉토리에 추가 필요)",
                })
                continue

            result = checker.run(site_info, context)
            results.append(result)

        browser.close()

    print_summary_table(results)

    # 실패 건수가 있으면 1 반환, 전부 정상이면 0
    has_failure = any(r.get("status") in ["LOGIN_FAILED", "ERROR", "CHECK_FAILED"] for r in results)
    return 1 if has_failure else 0


def main():
    parser = argparse.ArgumentParser(description="웹사이트 자동 로그인 및 출석체크 매크로")
    parser.add_argument(
        "--site", "-s",
        type=str,
        default=None,
        help="특정 사이트만 실행 (예: --site 칠성몰, --site chilsung)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="브라우저 창을 화면에 띄워 실행 (기본값: 헤드리스 백그라운드 모드)"
    )
    parser.add_argument(
        "--info-file", "-f",
        type=str,
        default=str(SITE_INFO_PATH),
        help=f"site_info.json 경로 (기본값: {SITE_INFO_PATH})"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="지원하는 사이트 목록 확인"
    )

    args = parser.parse_args()

    if args.list:
        print("\n[지원 사이트 핸들러 목록]")
        for k in sorted(set(SITE_REGISTRY.keys())):
            cls_name = SITE_REGISTRY[k].__name__
            print(f" - {k} ({cls_name})")
        print()
        return

    exit_code = run_attendance(
        target_site=args.site,
        headed=args.headed,
        info_file_path=Path(args.info_file)
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
