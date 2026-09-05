import time
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class FilecityAttendanceChecker(BaseAttendanceChecker):
    """
    파일시티 (FileCity) 출석체크 자동화 클래스
    - 로그인 URL: https://www.filecity.co.kr/
    - 이벤트 URL: https://www.filecity.co.kr/event/attend_re.html
    """

    def __init__(self, screenshot_delay_sec: int = 15):
        super().__init__(site_key="filecity", display_name="파일시티", screenshot_delay_sec=screenshot_delay_sec)

    def _close_overlay_popups(self, page: Page):
        """
        파일시티 메인/레이어 팝업 및 flixco 레이어 닫기
        """
        try:
            page.evaluate(
                "() => { if (typeof closeEventPop === 'function') closeEventPop(1); const pop = document.getElementById('flixco_layer'); if (pop) pop.style.display = 'none'; }"
            )
        except Exception:
            pass

        try:
            popup_close_selectors = [
                "button.fl_btn",
                "button[onclick*='closeEventPop']",
                ".layer_close",
                "button:has-text('닫기')",
                "a:has-text('닫기')",
                "img[alt*='닫기']",
                ".btn_close",
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
        파일시티 회원 로그인 수행
        """
        login_url = site_info.get("login_url", "https://www.filecity.co.kr/")
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "아이디 또는 비밀번호가 site_info.json에 지정되지 않았습니다."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        self._close_overlay_popups(page)

        # 1. 아이디 및 비밀번호 입력
        id_input = page.locator("#userid, input[name='userid']").first
        pw_input = page.locator("#userpw, input[name='userpw']").first

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.wait_for(state="visible", timeout=5000)
        pw_input.fill(password)
        page.wait_for_timeout(500)

        # 2. 로그인 버튼 클릭
        self.logger.info(f"[{self.display_name}] 로그인 버튼 클릭...")
        login_btn = page.locator(
            "input[src*='login_submit'], input[src*='login_btn'], form[name*='login'] input[type='image'], .btn_login"
        ).first
        login_btn.scroll_into_view_if_needed()
        login_btn.click()

        # 3. 로그인 결과 대기
        start_time = time.time()
        while time.time() - start_time < 8:
            if self.captured_dialogs:
                last_msg = self.captured_dialogs[-1]
                if any(w in last_msg for w in ["없습니다", "일치하지", "오류", "틀렸", "실패", "확인"]):
                    return False, last_msg
                if any(w in last_msg for w in ["성공", "환영"]):
                    return True, last_msg

            # 로그인 후 나타나는 마이페이지/회원정보/로그아웃/출석체크 영역 확인
            logged_in_el = page.locator(
                "div.login_btn:has-text('출석체크'), div.login_btn:has-text('나가기'), a:has-text('로그아웃'), .btn_logout, .login_btm"
            )
            if logged_in_el.count() > 0 and logged_in_el.first.is_visible():
                return True, "로그인 완료"

            page.wait_for_timeout(500)

        if (
            page.locator("#userid, input[name='userid']").count() > 0
            and page.locator("#userid, input[name='userid']").first.is_visible()
        ):
            if self.captured_dialogs:
                return False, self.captured_dialogs[-1]
            return False, "로그인 실패 (아이디 또는 비밀번호 확인 필요)"

        return True, "로그인 완료"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        파일시티 출석체크 이벤트 수행
        """
        attend_url = site_info.get("url", "https://www.filecity.co.kr/event/attend_re.html")
        self.logger.info(f"[{self.display_name}] 좌측 정보창 '출석체크' 메뉴로 이동 중...")

        # 1. 좌측 회원 영역의 '출석체크' 버튼 클릭하여 이동 (또는 직접 이동)
        attend_div = page.locator(
            "div.login_btn:has-text('출석체크'), div[onclick*='attend_re'], .login_btm .last, a:has-text('출석체크')"
        ).first
        if attend_div.count() > 0 and attend_div.is_visible():
            attend_div.click()
        else:
            page.goto(attend_url, wait_until="domcontentloaded", timeout=30000)

        page.wait_for_timeout(2500)
        self._close_overlay_popups(page)

        # 2. 출석체크 버튼 탐색 (#btn_submit, .btn_check)
        attend_selectors = [
            "#btn_submit",
            ".btn_check",
            "div:has-text('출석체크하기')",
            "button:has-text('출석체크')",
            "a:has-text('출석체크')",
            "img[alt*='출석']",
        ]
        target_btn = None
        for sel in attend_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                target_btn = loc.first
                break

        # 3. 버튼 클릭
        self.captured_dialogs.clear()
        if target_btn:
            self.logger.info(f"[{self.display_name}] '출석체크하기' 버튼 클릭...")
            target_btn.scroll_into_view_if_needed()
            target_btn.click()
        else:
            self.logger.info(f"[{self.display_name}] #btn_submit 클릭 스크립트 실행...")
            page.evaluate("() => { if ($('#btn_submit').length) $('#btn_submit').click(); }")

        page.wait_for_timeout(2500)

        # 4. 다이얼로그 확인
        if self.captured_dialogs:
            dialog_msg = self.captured_dialogs[-1]
            self.logger.info(f"[{self.display_name}] 다이얼로그 수신: {dialog_msg}")
            if "로그인" in dialog_msg or "인증" in dialog_msg:
                return {
                    "success": False,
                    "status": "LOGIN_REQUIRED",
                    "message": dialog_msg,
                }
            if any(w in dialog_msg for w in ["1회", "1번", "하루", "이미", "완료하셨", "참여하셨", "내일"]):
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": dialog_msg,
                }
            if any(w in dialog_msg for w in ["당첨", "지급", "적립", "포인트", "성공", "완료", "되었습니다"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": dialog_msg,
                }

        # 다이얼로그가 없더라도 페이지 내 텍스트 확인
        page_text = page.inner_text("body")
        if any(w in page_text for w in ["이미 참여", "출석 완료", "출석체크 완료"]):
            return {
                "success": False,
                "status": "ALREADY_CHECKED",
                "message": "오늘 이미 출석체크에 참여하셨습니다.",
            }

        return {
            "success": True,
            "status": "SUCCESS",
            "message": "출석체크 클릭 완료",
        }
