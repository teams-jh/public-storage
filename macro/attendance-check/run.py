import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

from config import (
    SITE_INFO_PATH,
    DEFAULT_USER_AGENT,
    DEFAULT_VIEWPORT,
    MAX_RETRY_ROUNDS,
    RETRY_DELAY_SEC,
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
    print(f"{'사이트':<15} | {'상태':<12} | {'재시도':<6} | {'결과 메시지'}")
    print("-" * 70)

    for res in results:
        name = res.get("site_name", "미상")
        status = res.get("status", "UNKNOWN")
        msg = res.get("message", "")
        retried = res.get("retried", False)

        status_display = {
            "SUCCESS": "[성공]",
            "ALREADY_CHECKED": "[이미완료]",
            "LOGIN_FAILED": "[로그인실패]",
            "CHECK_FAILED": "[출석실패]",
            "LOGIN_REQUIRED": "[로그인필요]",
            "ERROR": "[오류]",
        }.get(status, f"[{status}]")

        retried_str = "O" if retried else "-"
        print(f"{name:<15} | {status_display:<12} | {retried_str:<6} | {msg}")

    print("=" * 70 + "\n")


def run_attendance(
    target_site: str = None,
    headed: bool = True,
    slow_mo: int = 0,
    channel: str = "chrome",
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

    effective_slow_mo = slow_mo if slow_mo > 0 else (600 if headed else 0)
    logger.info(
        f"총 {len(run_list)}개 사이트 출석체크를 시작합니다. "
        f"(브라우저 창 표시: {'화면 표시 모드(기본)' if headed else '헤드리스(백그라운드)'}, 채널: {channel or 'chromium'}, 속도지연: {effective_slow_mo}ms)"
    )

    results_map: Dict[str, Dict[str, Any]] = {}
    ordered_keys: List[str] = []

    with sync_playwright() as p:
        # 브라우저 실행 (Chrome 채널 우선, 실패 시 기본 Chromium 사용)
        launch_kwargs = {
            "headless": not headed,
            "slow_mo": effective_slow_mo,
        }
        if channel:
            launch_kwargs["channel"] = channel

        try:
            browser = p.chromium.launch(**launch_kwargs)
        except Exception as e:
            if channel:
                logger.warning(f"'{channel}' 채널 실행 실패({e}), 기본 chromium으로 실행합니다.")
                launch_kwargs.pop("channel", None)
                browser = p.chromium.launch(**launch_kwargs)
            else:
                raise e

        context = browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport=DEFAULT_VIEWPORT,
        )

        # ----------------------------------------------------
        # 1차 전체 출석체크 라운드
        # ----------------------------------------------------
        for site_info in run_list:
            site_name = site_info.get("name", "")
            site_key = site_info.get("site_key", "")
            dict_key = site_key or site_name

            if dict_key not in ordered_keys:
                ordered_keys.append(dict_key)

            checker = get_checker(site_key) or get_checker(site_name)
            if not checker:
                logger.error(f"'{site_name or site_key}' 사이트를 지원하는 출석체크 핸들러가 구현되지 않았습니다.")
                results_map[dict_key] = {
                    "site_name": site_name or site_key,
                    "status": "ERROR",
                    "message": "지원하지 않는 사이트 핸들러 (sites 디렉토리에 추가 필요)",
                    "retried": False,
                }
                continue

            result = checker.run(site_info, context)
            result["retried"] = False
            results_map[dict_key] = result

        # ----------------------------------------------------
        # 2차 실패 사이트 재시도 라운드 (1회 재시도)
        # ----------------------------------------------------
        failed_sites = [
            site_info for site_info in run_list
            if results_map.get(site_info.get("site_key") or site_info.get("name", "")).get("status") not in ["SUCCESS", "ALREADY_CHECKED"]
        ]

        if failed_sites and MAX_RETRY_ROUNDS > 0:
            import time
            time.sleep(RETRY_DELAY_SEC)

            failed_names = [s.get("name") or s.get("site_key") for s in failed_sites]
            logger.info("\n" + "=" * 70)
            logger.info(f"🔄 총 {len(failed_sites)}개 실패 사이트에 대해 재시도를 진행합니다: {failed_names}")
            logger.info("=" * 70 + "\n")

            for site_info in failed_sites:
                site_name = site_info.get("name", "")
                site_key = site_info.get("site_key", "")
                dict_key = site_key or site_name

                checker = get_checker(site_key) or get_checker(site_name)
                if not checker:
                    continue

                logger.info(f"[{site_name or site_key}] 재시도 실행 중...")
                retry_result = checker.run(site_info, context)
                retry_result["retried"] = True
                results_map[dict_key] = retry_result

        if headed:
            # 사용자가 화면의 최종 결과를 충분히 확인할 수 있도록 3초 대기
            import time
            time.sleep(3)

        browser.close()

    final_results = [results_map[k] for k in ordered_keys]
    print_summary_table(final_results)

    # 실패 건수가 있으면 1 반환, 전부 정상이면 0
    has_failure = any(r.get("status") not in ["SUCCESS", "ALREADY_CHECKED"] for r in final_results)
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
        "--headless",
        action="store_true",
        help="브라우저 창을 띄우지 않고 백그라운드에서 조용히 실행 (기본값: 브라우저 화면 표시)"
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=0,
        help="동작 간 속도 지연(ms 단위, 기본값: 화면 표시 모드 시 600ms)"
    )
    parser.add_argument(
        "--channel",
        type=str,
        default="chrome",
        help="브라우저 채널 (chrome, msedge, chromium 등, 기본값: chrome)"
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

    # 기본값: 브라우저 화면 표시 (args.headless 가 주어질 때만 백그라운드로 전환)
    is_headed = not args.headless

    exit_code = run_attendance(
        target_site=args.site,
        headed=is_headed,
        slow_mo=args.slow_mo,
        channel=args.channel,
        info_file_path=Path(args.info_file)
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
