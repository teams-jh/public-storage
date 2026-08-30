from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
from playwright.sync_api import BrowserContext, Dialog, Page

from config import SCREENSHOTS_DIR, SCREENSHOTS_SUCCESS_DIR, SCREENSHOTS_FAIL_DIR, setup_logger


class BaseAttendanceChecker(ABC):
    """
    모든 사이트 출석체크 자동화 핸들러의 기본 추상 클래스.
    각 사이트별 로그인 방식 및 출석체크 UI 동작을 구현합니다.
    """

    def __init__(self, site_key: str, display_name: str):
        self.site_key = site_key
        self.display_name = display_name
        self.logger = setup_logger(f"Checker.{site_key}")
        self.captured_dialogs: List[str] = []

    def _setup_dialog_listener(self, page: Page):
        """
        브라우저 Alert/Confirm 다이얼로그를 자동 수신하고 내용을 기록합니다.
        """
        self.captured_dialogs = []

        def on_dialog(dialog: Dialog):
            msg = dialog.message
            self.logger.info(f"[{self.display_name}] 브라우저 다이얼로그({dialog.type}): {msg}")
            self.captured_dialogs.append(msg)
            try:
                dialog.accept()
            except Exception as e:
                self.logger.warning(f"다이얼로그 수락 실패: {e}")

        page.on("dialog", on_dialog)

    def save_screenshot(
        self,
        page: Page,
        prefix: str = "status",
        is_success: bool = False,
        scroll_y: int = 300,
        full_page: bool = True
    ) -> Optional[Path]:
        """
        현재 페이지 화면을 스크롤한 뒤 전체 화면(full_page)으로 캡처하여 성공(success) 또는 실패(fail) 하위 폴더에 저장합니다.
        """
        try:
            target_dir = SCREENSHOTS_SUCCESS_DIR if is_success else SCREENSHOTS_FAIL_DIR
            target_dir.mkdir(parents=True, exist_ok=True)

            # 출석 영역/결과 화면이 잘 담기도록 스크롤을 아래로 이동
            try:
                if scroll_y > 0:
                    page.evaluate(f"window.scrollBy(0, {scroll_y})")
                    page.wait_for_timeout(500)
            except Exception:
                pass

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.site_key}_{prefix}_{timestamp}.png"
            filepath = target_dir / filename
            page.screenshot(path=str(filepath), full_page=full_page)
            self.logger.debug(f"스크린샷 저장 완료 ({'success' if is_success else 'fail'}): {filepath}")
            return filepath
        except Exception as e:
            self.logger.warning(f"스크린샷 저장 실패: {e}")
            return None

    def run(self, site_info: Dict[str, Any], context: BrowserContext) -> Dict[str, Any]:
        """
        단일 사이트 출석체크 전체 흐름을 실행합니다.
        1. 페이지 생성 및 리스너 등록
        2. 로그인 수행
        3. 출석체크 수행
        4. 결과 리포트 반환 및 성공/실패 스크린샷 캡처
        """
        site_name = site_info.get("name", self.display_name)
        self.logger.info(f"========== [{site_name}] 출석체크 시작 ==========")
        page = context.new_page()
        self._setup_dialog_listener(page)

        result = {
            "site_key": self.site_key,
            "site_name": site_name,
            "success": False,
            "status": "UNKNOWN",  # SUCCESS, ALREADY_CHECKED, LOGIN_FAILED, CHECK_FAILED, ERROR
            "message": "",
            "dialogs": [],
            "screenshot": None,
        }

        try:
            # 1. 로그인
            self.logger.info(f"[{site_name}] 로그인 시도 중...")
            login_success, login_msg = self.login(page, site_info)
            if not login_success:
                self.logger.error(f"[{site_name}] 로그인 실패: {login_msg}")
                result["status"] = "LOGIN_FAILED"
                result["message"] = f"로그인 실패: {login_msg}"
                result["screenshot"] = str(self.save_screenshot(page, "login_failed", is_success=False) or "")
                result["dialogs"] = self.captured_dialogs.copy()
                return result

            self.logger.info(f"[{site_name}] 로그인 성공! 출석체크 페이지로 이동합니다.")

            # 2. 출석체크
            check_result = self.check_attendance(page, site_info)
            result.update(check_result)
            result["dialogs"] = self.captured_dialogs.copy()

            if result["success"]:
                self.logger.info(f"[{site_name}] 출석체크 성공: {result['message']}")
                result["screenshot"] = str(self.save_screenshot(page, "success", is_success=True) or "")
            elif result["status"] == "ALREADY_CHECKED":
                self.logger.info(f"[{site_name}] 이미 출석 완료됨: {result['message']}")
                result["screenshot"] = str(self.save_screenshot(page, "already_checked", is_success=True) or "")
            else:
                self.logger.warning(f"[{site_name}] 출석체크 미완료/실패: {result['message']}")
                result["screenshot"] = str(self.save_screenshot(page, "check_failed", is_success=False) or "")

        except Exception as e:
            self.logger.exception(f"[{site_name}] 예외 발생: {e}")
            result["status"] = "ERROR"
            result["message"] = f"오류 발생: {str(e)}"
            result["screenshot"] = str(self.save_screenshot(page, "error", is_success=False) or "")
            result["dialogs"] = self.captured_dialogs.copy()
        finally:
            try:
                page.close()
            except Exception:
                pass
            self.logger.info(f"========== [{site_name}] 출석체크 종료 ({result['status']}) ==========\n")

        return result

    @abstractmethod
    def login(self, page: Page, site_info: Dict[str, Any]) -> tuple[bool, str]:
        """
        사이트 로그인 로직을 구현합니다.
        :return: (성공 여부, 메시지)
        """
        pass

    @abstractmethod
    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        출석체크 버튼 클릭 및 결과 확인 로직을 구현합니다.
        :return: { "success": bool, "status": str, "message": str }
        """
        pass
