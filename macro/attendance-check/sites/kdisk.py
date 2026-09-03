import time
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class KdiskAttendanceChecker(BaseAttendanceChecker):
    """
    케이디스크 (KDISK) 복불복 출석체크 룰렛 자동화 클래스
    - 로그인 URL: https://www.kdisk.co.kr/index.php
    - 출석체크 URL: https://www.kdisk.co.kr/main/eventMarge.php?mode=eventMarge&sm=event&action=view&idx=171
    """

    def __init__(self, screenshot_delay_sec: int = 15):
        super().__init__(site_key="kdisk", display_name="케이디스크", screenshot_delay_sec=screenshot_delay_sec)

    def _close_overlay_popups(self, page: Page):
        """
        케이디스크 메인/레이어 팝업 닫기
        """
        try:
            popup_close_selectors = [
                "button:has-text('닫기')",
                "a:has-text('닫기')",
                "img[alt*='닫기']",
                ".btn_close",
                "#js-layerAttend .layer_close",
            ]
            for sel in popup_close_selectors:
                elements = page.locator(sel)
                if elements.count() > 0 and elements.first.is_visible():
                    elements.first.click(timeout=1000)
                    page.wait_for_timeout(300)
        except Exception:
            pass

    def login(self, page: Page, site_info: Dict[str, Any]) -> tuple[bool, str]:
        """
        케이디스크 회원 로그인 수행
        """
        login_url = site_info.get("login_url", "https://www.kdisk.co.kr/index.php")
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "아이디 또는 비밀번호가 site_info.json에 지정되지 않았습니다."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        self._close_overlay_popups(page)

        # 1. 아이디 및 비밀번호 입력
        id_input = page.locator("input[name='mb_id']").first
        pw_input = page.locator("input[name='mb_pw']").first

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.wait_for(state="visible", timeout=5000)
        pw_input.fill(password)
        page.wait_for_timeout(500)

        # 2. 로그인 버튼 클릭
        self.logger.info(f"[{self.display_name}] 로그인 버튼 클릭...")
        login_btn = page.locator("input[alt='로그인'], input[src*='login_btn'], a[href*='SecurityfrmCheck']").first
        login_btn.scroll_into_view_if_needed()
        login_btn.click()

        # 3. 로그인 결과 대기 (다이얼로그 메시지 또는 마이페이지/로그아웃 버튼 표시 확인)
        start_time = time.time()
        while time.time() - start_time < 8:
            if self.captured_dialogs:
                last_msg = self.captured_dialogs[-1]
                if any(w in last_msg for w in ["없습니다", "일치하지", "오류", "틀렸", "실패"]):
                    return False, last_msg
                if any(w in last_msg for w in ["성공", "환영"]):
                    return True, last_msg

            # 로그아웃 버튼이나 사용자 정보 영역이 노출되는지 확인
            logout_btn = page.locator("a:has-text('로그아웃'), img[alt*='로그아웃'], .login_after")
            if logout_btn.count() > 0 and logout_btn.first.is_visible():
                return True, "로그인 완료"

            page.wait_for_timeout(500)

        # 타임아웃 시 로그인 폼이 여전히 존재하면 실패로 판단
        if page.locator("input[name='mb_id']").count() > 0 and page.locator("input[name='mb_id']").first.is_visible():
            if self.captured_dialogs:
                return False, self.captured_dialogs[-1]
            return False, "로그인 실패 (아이디 또는 비밀번호 확인 필요)"

        return True, "로그인 완료"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        케이디스크 복불복 룰렛 출석체크 수행
        """
        attend_url = site_info.get(
            "url",
            "https://www.kdisk.co.kr/main/eventMarge.php?mode=eventMarge&sm=event&action=view&idx=171"
        )
        self.logger.info(f"[{self.display_name}] 출석체크 페이지({attend_url}) 이동 중...")
        page.goto(attend_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        self._close_overlay_popups(page)

        # 1. 룰렛 START 버튼 검색
        start_btn = page.locator("#js-roulette button, #js-roulette p.btn button, #js-roulette").first
        try:
            start_btn.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "status": "CHECK_FAILED",
                "message": "출석체크 룰렛(#js-roulette) 버튼을 찾을 수 없습니다.",
            }

        # 2. 버튼 클릭
        self.logger.info(f"[{self.display_name}] 룰렛 '출석체크 START' 버튼 클릭...")
        start_btn.scroll_into_view_if_needed()
        start_btn.click()
        page.wait_for_timeout(3000)

        # 3. 브라우저 Alert 다이얼로그 확인
        if self.captured_dialogs:
            dialog_msg = self.captured_dialogs[-1]
            self.logger.info(f"[{self.display_name}] 다이얼로그 수신: {dialog_msg}")
            if "로그인" in dialog_msg:
                return {
                    "success": False,
                    "status": "LOGIN_REQUIRED",
                    "message": dialog_msg,
                }
            if any(w in dialog_msg for w in ["이미", "완료하셨", "참여하셨", "내일"]):
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": dialog_msg,
                }
            if any(w in dialog_msg for w in ["당첨", "지급", "적립", "포인트", "캐쉬", "성공"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": dialog_msg,
                }

        # 4. 레이어 팝업(#js-layerAttend) 확인
        popup = page.locator("#js-layerAttend")
        if popup.count() > 0 and popup.first.is_visible():
            popup_text = popup.first.inner_text().strip().replace("\n", " ")
            self.logger.info(f"[{self.display_name}] 출석 결과 팝업 감지: {popup_text}")

            # 팝업 닫기/확인 버튼 클릭
            confirm_btn = popup.locator("img[alt*='확인'], a:has-text('확인'), a[onclick*='js-layerAttend']").first
            if confirm_btn.count() > 0 and confirm_btn.is_visible():
                confirm_btn.click()

            if any(w in popup_text for w in ["이미", "참여하셨", "완료하셨"]):
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": popup_text,
                }

            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"출석 완료 ({popup_text})",
            }

        return {
            "success": True,
            "status": "SUCCESS",
            "message": "출석체크 룰렛 실행 완료",
        }
