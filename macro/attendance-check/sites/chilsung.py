import time
from typing import Any, Dict, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class ChilsungAttendanceChecker(BaseAttendanceChecker):
    """
    칠성몰(롯데칠성음료 공식몰) 출석체크 자동화 클래스
    - 로그인 URL: https://mall.lottechilsung.co.kr/sign-in
    - 출석체크 URL: https://mall.lottechilsung.co.kr/daily-check
    """

    def __init__(self):
        super().__init__(site_key="chilsung", display_name="칠성몰")

    def _close_overlay_popups(self, page: Page):
        """
        메인/로그인 화면에 뜰 수 있는 이벤트 레이어 팝업이나 앱 유도 팝업을 닫습니다.
        """
        try:
            # 1. 일반 레이어 팝업 '오늘 하루 보지 않기' or '닫기' 버튼
            popup_close_selectors = [
                "button:has-text('오늘 하루 보지 않기')",
                "button:has-text('닫기')",
                ".layer-popup__close",
                "#byapps_launch_button .go_update",
            ]
            for sel in popup_close_selectors:
                elements = page.locator(sel)
                if elements.count() > 0 and elements.first.is_visible():
                    self.logger.debug(f"팝업 감지되어 닫기 시도: {sel}")
                    elements.first.click(timeout=1500)
                    page.wait_for_timeout(300)
        except Exception:
            pass

    def login(self, page: Page, site_info: Dict[str, Any]) -> tuple[bool, str]:
        """
        칠성몰 로그인 수행
        """
        login_url = site_info.get("login_url", "https://mall.lottechilsung.co.kr/sign-in")
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "아이디 또는 비밀번호가 site_info.json에 지정되지 않았습니다."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)
        self._close_overlay_popups(page)

        # 1. 회원 로그인 탭 활성화 확인
        member_tab = page.locator("button:has-text('회원 로그인')")
        if member_tab.count() > 0 and member_tab.first.is_visible():
            member_tab.first.click()
            page.wait_for_timeout(300)

        # 2. 아이디 및 비밀번호 입력
        id_input = page.locator("input[name='memberId']")
        pw_input = page.locator("input[name='password']")

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.fill(password)
        page.wait_for_timeout(500)

        # 3. 로그인 버튼 클릭
        self.logger.info(f"[{self.display_name}] 로그인 버튼 클릭...")
        login_button = page.get_by_role("button", name="로그인", exact=True)
        if not login_button.is_visible():
            login_button = page.locator("button.SignInForm__LoginButton-sc-1kqfc9j-10, button:has-text('로그인')").first

        login_button.scroll_into_view_if_needed()
        login_button.click()

        # 4. 로그인 결과 대기 (URL 변경 또는 Alert 다이얼로그 / 에러 감지)
        start_time = time.time()
        while time.time() - start_time < 8:
            # 다이얼로그 메시지가 뜬 경우 (예: "아이디, 비밀번호가 일치하지 않습니다.")
            if self.captured_dialogs:
                last_msg = self.captured_dialogs[-1]
                return False, last_msg

            # 페이지 이동이 발생했는지 확인 (로그인 성공 시 보통 메인페이지 또는 리다이렉트 URL로 이동)
            current_url = page.url
            if "/sign-in" not in current_url:
                return True, "로그인 완료"

            page.wait_for_timeout(500)

        # 타임아웃 이후에도 /sign-in에 머물러 있는 경우
        if "/sign-in" in page.url:
            # 다이얼로그가 없더라도 페이지 내 에러 문구 점검
            error_el = page.locator(".error, .warning, [class*='Error'], [class*='Warn']")
            if error_el.count() > 0 and error_el.first.is_visible():
                error_text = error_el.first.inner_text()
                return False, f"로그인 실패 ({error_text})"
            return False, "로그인 응답 없음 (아이디 또는 비밀번호 확인 필요)"

        return True, "로그인 완료"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        칠성몰 출석체크 수행
        """
        check_url = site_info.get("url", "https://mall.lottechilsung.co.kr/daily-check")
        self.logger.info(f"[{self.display_name}] 출석체크 페이지({check_url}) 이동 중...")
        page.goto(check_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)
        self._close_overlay_popups(page)

        # 1. 출석체크 버튼 대기
        attend_btn = page.locator("button.attendance-btn, button:has-text('출석체크하기')").first
        try:
            attend_btn.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "status": "CHECK_FAILED",
                "message": "출석체크 버튼(.attendance-btn)을 찾을 수 없습니다.",
            }

        # 2. 버튼 상태 확인 (비활성화 여부)
        if attend_btn.is_disabled():
            return {
                "success": False,
                "status": "ALREADY_CHECKED",
                "message": "출석체크 버튼이 이미 비활성화(완료)되어 있습니다.",
            }

        # 3. 출석체크 버튼 클릭
        self.logger.info(f"[{self.display_name}] '출석체크하기' 버튼 클릭...")
        attend_btn.scroll_into_view_if_needed()
        attend_btn.click()
        page.wait_for_timeout(2000)

        # 4. 모달 팝업 또는 다이얼로그 확인
        # 4-1. 브라우저 Alert 다이얼로그 확인
        if self.captured_dialogs:
            dialog_msg = self.captured_dialogs[-1]
            if any(w in dialog_msg for w in ["이미", "완료하셨", "참여하셨"]):
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": dialog_msg,
                }
            if any(w in dialog_msg for w in ["완료", "지급", "적립", "성공"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": dialog_msg,
                }
            return {
                "success": False,
                "status": "CHECK_FAILED",
                "message": f"다이얼로그 메시지: {dialog_msg}",
            }

        # 4-2. 칠성몰 커스텀 모달(.dpromotion-modal-box) 확인
        modal_box = page.locator(".dpromotion-modal-box")
        if modal_box.count() > 0 and modal_box.first.is_visible():
            modal_text = modal_box.first.inner_text().strip().replace("\n", " ")
            self.logger.info(f"[{self.display_name}] 출석 모달 감지: {modal_text}")

            # 모달 닫기(확인) 버튼 클릭
            confirm_btn = modal_box.locator("button.dpromotion-alert__button, button:has-text('확인')").first
            if confirm_btn.is_visible():
                confirm_btn.click()
                page.wait_for_timeout(500)

            if "로그인이 필요한" in modal_text:
                return {
                    "success": False,
                    "status": "LOGIN_REQUIRED",
                    "message": "로그인 세션이 만료되었거나 로그인이 필요합니다.",
                }
            if any(w in modal_text for w in ["이미", "완료하셨", "참여하셨"]):
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": modal_text,
                }
            if any(w in modal_text for w in ["완료", "적립", "지급", "포인트"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": modal_text,
                }

            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"출석 완료 응답: {modal_text}",
            }

        # 4-3. 현재 누적 출석 카운트 확인
        count_el = page.locator(".attendance-count")
        attend_count = count_el.inner_text().strip() if count_el.count() > 0 else "미확인"

        return {
            "success": True,
            "status": "SUCCESS",
            "message": f"출석체크 완료 (현재 이번 달 출석일수: {attend_count}일)",
        }
