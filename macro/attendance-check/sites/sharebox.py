import time
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class ShareboxAttendanceChecker(BaseAttendanceChecker):
    """
    쉐어박스 (ShareBox) 출석체크 자동화 클래스
    - 로그인 URL: https://sharebox.co.kr/
    - 출석체크 URL: https://sharebox.co.kr/event/?todo=view&idx=351&p=1
    """

    def __init__(self):
        super().__init__(site_key="sharebox", display_name="쉐어박스")

    def _close_overlay_popups(self, page: Page):
        """
        쉐어박스 메인/레이어 팝업 닫기
        """
        try:
            popup_close_selectors = [
                "button:has-text('닫기')",
                "a:has-text('닫기')",
                "img[alt*='닫기']",
                ".btn_close",
                ".layer_close",
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
        쉐어박스 회원 로그인 수행
        """
        login_url = site_info.get("login_url", "https://sharebox.co.kr/")
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "아이디 또는 비밀번호가 site_info.json에 지정되지 않았습니다."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        self._close_overlay_popups(page)

        # 1. 로그인 팝업 열기 (JS 함수 또는 jQuery 팝업 호출)
        self.logger.info(f"[{self.display_name}] 로그인 팝업 활성화...")
        page.evaluate("""() => {
            if (window.jQuery) {
                window.jQuery('#popup_bg_layer').show();
                window.popup_layer_view('login');
            } else if (typeof popup_layer_view === 'function') {
                popup_layer_view('login');
            }
        }""")
        page.wait_for_timeout(800)

        # 2. 아이디 및 비밀번호 입력
        id_input = page.locator("#user_id").first
        pw_input = page.locator("#user_pw").first

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.wait_for(state="visible", timeout=5000)
        pw_input.fill(password)
        page.wait_for_timeout(500)

        # 3. 로그인 버튼 클릭 (초록색 로그인 버튼 .pbtn_green)
        self.logger.info(f"[{self.display_name}] 로그인 버튼(.pbtn_green) 클릭...")
        login_btn = page.locator(".pbtn_green, div.btn_find div:has-text('로그인')").first
        if login_btn.count() > 0 and login_btn.is_visible():
            login_btn.click()
        else:
            page.evaluate("() => { if (typeof login_submit === 'function') login_submit(); }")

        # 4. 로그인 결과 대기
        start_time = time.time()
        while time.time() - start_time < 8:
            if self.captured_dialogs:
                last_msg = self.captured_dialogs[-1]
                if any(w in last_msg for w in ["없습니다", "일치하지", "오류", "틀렸", "실패", "확인", "등록되지", "존재하지"]):
                    return False, last_msg
                if any(w in last_msg for w in ["성공", "환영"]):
                    return True, last_msg

            # 로그아웃 버튼 또는 사용자 영역 확인
            logout_btn = page.locator(".btn_out, li:has-text('로그아웃'), a:has-text('로그아웃'), a[href*='logout'], .top_info, .tinfo_bx")
            if logout_btn.count() > 0 and logout_btn.first.is_visible():
                return True, "로그인 완료"

            page.wait_for_timeout(500)

        logout_btn = page.locator(".btn_out, li:has-text('로그아웃'), a:has-text('로그아웃'), a[href*='logout'], .top_info, .tinfo_bx")
        if logout_btn.count() > 0 and logout_btn.first.is_visible():
            return True, "로그인 완료"

        if self.captured_dialogs:
            return False, self.captured_dialogs[-1]

        return False, "로그인 실패 (아이디 또는 비밀번호 확인 필요)"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        쉐어박스 출석체크 수행
        로그인 후 상단 메뉴의 '출석체크' 링크를 클릭하거나 지정된 이벤트 URL로 이동합니다.
        """
        attend_url = site_info.get("url", "https://sharebox.co.kr/event/?todo=view&idx=351&p=1")
        self.logger.info(f"[{self.display_name}] 출석체크 페이지로 이동 중...")

        # 상단 네비게이션의 '출석체크' 링크 우선 클릭 시도
        top_attend_btn = page.locator("a:has-text('출석체크'), a[onclick*='attend_top']")
        if top_attend_btn.count() > 0 and top_attend_btn.first.is_visible():
            self.logger.info(f"[{self.display_name}] 상단 '출석체크' 메뉴 클릭...")
            top_attend_btn.first.click()
            page.wait_for_timeout(2000)
        else:
            self.logger.info(f"[{self.display_name}] 출석체크 URL({attend_url}) 직접 접속...")
            page.goto(attend_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

        self._close_overlay_popups(page)

        # 1. 출석체크 버튼 탐색 (.btn_check, li:has-text('출석체크'), AttendGive)
        attend_selectors = [
            ".btn_check",
            "li:has-text('출석체크하기')",
            "li:has-text('출석체크')",
            "button:has-text('출석')",
            "a:has-text('출석')",
            "img[alt*='출석']",
            "[onclick*='AttendGive']",
            "#btn_attend",
            ".btn_attend",
            ".btn_attend_check",
        ]
        target_btn = None
        for sel in attend_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                target_btn = loc.first
                break

        # 출석 완료 텍스트가 이미 표시되어 있는지 확인
        page_text = page.inner_text("body")
        if target_btn:
            btn_text = target_btn.inner_text().strip()
            if "완료" in btn_text:
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": "오늘 이미 출석체크에 참여하셨습니다.",
                }
        elif any(w in page_text for w in ["출석체크 완료", "이미 출석", "참여 완료"]):
            return {
                "success": False,
                "status": "ALREADY_CHECKED",
                "message": "오늘 이미 출석체크에 참여하셨습니다.",
            }

        if not target_btn:
            # AttendGive 함수가 정의되어 있는지 확인
            has_attend_func = page.evaluate("() => typeof AttendGive === 'function'")
            if not has_attend_func:
                return {
                    "success": False,
                    "status": "CHECK_FAILED",
                    "message": "출석체크 버튼을 찾을 수 없습니다.",
                }

        # 2. 버튼 클릭
        self.logger.info(f"[{self.display_name}] 출석체크 버튼 클릭...")
        if target_btn:
            target_btn.scroll_into_view_if_needed()
            target_btn.click()
        else:
            page.evaluate("() => { if (typeof AttendGive === 'function') AttendGive(); }")

        page.wait_for_timeout(2500)

        # 3. 다이얼로그 확인
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
            if any(w in dialog_msg for w in ["당첨", "지급", "적립", "포인트", "성공", "완료", "출석체크!"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": dialog_msg,
                }

        # 클릭 후 출석체크 완료 텍스트가 생겼는지 확인
        new_page_text = page.inner_text("body")
        if any(w in new_page_text for w in ["출석체크 완료", "출석 완료"]):
            return {
                "success": True,
                "status": "SUCCESS",
                "message": "출석체크 완료",
            }

        return {
            "success": True,
            "status": "SUCCESS",
            "message": "출석체크 클릭 완료",
        }

