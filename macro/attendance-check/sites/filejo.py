import time
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class FilejoAttendanceChecker(BaseAttendanceChecker):
    """
    파일조 (FileJo) 출석체크 자동화 클래스
    - 로그인 URL: https://extra.filejo.com/
    - 출석체크 URL: https://extra.filejo.com/main/event.php?doc=check
    """

    def __init__(self):
        super().__init__(site_key="filejo", display_name="파일조")

    def _close_overlay_popups(self, page: Page):
        """
        파일조 메인/레이어 팝업 및 비밀번호 변경 안내 닫기
        """
        try:
            # 1. 비밀번호 변경 안내 (3개월 후에 변경하기)
            later_btn = page.locator("input[onclick*='passChangeLater'], button:has-text('3개월 후에 변경하기'), a:has-text('3개월 후에 변경하기')")
            if later_btn.count() > 0 and later_btn.first.is_visible():
                later_btn.first.click(timeout=1500)
                page.wait_for_timeout(500)
        except Exception:
            pass

        try:
            popup_close_selectors = [
                "button:has-text('닫기')",
                "a:has-text('닫기')",
                "img[alt*='닫기']",
                ".btn_close",
                "a[onclick*='close']",
                ".tsubclbtn a",
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
        파일조 회원 로그인 수행
        """
        login_url = site_info.get("login_url", "https://extra.filejo.com/")
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "아이디 또는 비밀번호가 site_info.json에 지정되지 않았습니다."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        self._close_overlay_popups(page)

        # 1. 로그인 팝업 열기
        id_input = page.locator("#mb_id").first
        if not id_input.is_visible():
            self.logger.info(f"[{self.display_name}] 로그인 레이어 열기...")
            open_btn = page.locator("input.leloginbt1, a:has-text('로그인'), a[onclick*='joinLoginLayer']").first
            if open_btn.count() > 0 and open_btn.is_visible():
                open_btn.click()
            else:
                page.evaluate("() => { if (typeof joinLoginLayer === 'function') joinLoginLayer('login'); }")
            page.wait_for_timeout(600)

        # 2. 아이디 및 비밀번호 입력
        pw_input = page.locator("#mb_pw").first

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.wait_for(state="visible", timeout=5000)
        pw_input.fill(password)
        page.wait_for_timeout(500)

        # 3. 파란색 로그인 버튼(input.loginblue) 클릭
        self.logger.info(f"[{self.display_name}] 로그인 버튼(input.loginblue) 클릭...")
        login_btn = page.locator("input.loginblue, input[value='로그인'].loginblue, input[onclick*='frmCheck_auth_encrypt']").first
        if login_btn.count() > 0 and login_btn.is_visible():
            login_btn.click()
        else:
            page.evaluate("() => { if (typeof frmCheck_auth_encrypt === 'function') frmCheck_auth_encrypt('login', 'ok'); }")

        # 4. 로그인 결과 대기
        start_time = time.time()
        while time.time() - start_time < 8:
            if self.captured_dialogs:
                last_msg = self.captured_dialogs[-1]
                if any(w in last_msg for w in ["없습니다", "일치하지", "오류", "틀렸", "실패", "등록되지", "잘못"]):
                    return False, last_msg
                if any(w in last_msg for w in ["성공", "환영"]):
                    return True, last_msg

            # 로그인 후 나타나는 마이페이지/사용자정보/로그아웃/비밀번호변경 영역 확인
            logged_in_el = page.locator("a:has-text('로그아웃'), .leidtt, .leinfo, .tsubmyptt, .jlebtn3, .top_menu2new, input[onclick*='passChangeLater'], .my_info, .user_name, a.btn_logout, .lelogin_after")
            if logged_in_el.count() > 0 and logged_in_el.first.is_visible():
                self._close_overlay_popups(page)
                return True, "로그인 완료"

            page.wait_for_timeout(500)

        # 다이얼로그 확인
        if self.captured_dialogs:
            last_msg = self.captured_dialogs[-1]
            if any(w in last_msg for w in ["성공", "환영"]):
                return True, last_msg
            return False, last_msg

        # 로그인 폼이 아직 열려있으면 실패
        if page.locator("#mb_id").is_visible():
            return False, "로그인 실패 (아이디 또는 비밀번호 확인 필요)"

        return True, "로그인 완료"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        파일조 출석체크 수행
        """
        attend_url = site_info.get("url", "https://extra.filejo.com/main/event.php?doc=check")
        self.logger.info(f"[{self.display_name}] 상단 '출석도장' 메뉴로 이동 중...")
        
        # 비밀번호 변경 팝업 등 정리
        self._close_overlay_popups(page)

        # 1. 상단 '출석도장' 링크 클릭 또는 movePage 실행 (직접 GET 요청 시 잘못된 요청 오류 방지)
        stamp_btn = page.locator(".top_menu2new a:has-text('출석도장'), a:has-text('출석도장'), a[onclick*='doc=check']").first
        if stamp_btn.count() > 0 and stamp_btn.is_visible():
            stamp_btn.click()
        else:
            page.evaluate("() => { if (typeof movePage === 'function') movePage('/main/event.php?doc=check', 'self', 'Y'); else window.location.href = '/main/event.php?doc=check'; }")

        page.wait_for_timeout(2500)
        self._close_overlay_popups(page)

        # 2. 출석체크 버튼 탐색 (오늘 출석 버튼: .dayright a, a[onclick*='infoCheck'])
        attend_selectors = [
            ".dayright a",
            "a[onclick*='infoCheck']",
            "button:has-text('오늘 출석')",
            "a:has-text('오늘 출석')",
            "div:has-text('오늘 출석')",
            "button:has-text('출석')",
            "a:has-text('출석')",
            "img[alt*='출석']",
            "#btn_attend",
            ".btn_attend",
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
            self.logger.info(f"[{self.display_name}] '오늘 출석' 버튼 클릭...")
            target_btn.scroll_into_view_if_needed()
            target_btn.click()
        else:
            self.logger.info(f"[{self.display_name}] infoCheck() 함수 직접 호출...")
            page.evaluate("() => { if (typeof infoCheck === 'function') infoCheck(); }")

        page.wait_for_timeout(2500)

        # 4. 다이얼로그 확인
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
            if any(w in dialog_msg for w in ["당첨", "지급", "적립", "포인트", "성공", "완료", "출석체크가 되어"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": dialog_msg,
                }

        # 다이얼로그가 없더라도 페이지 내 텍스트 확인
        page_text = page.inner_text("body")
        if any(w in page_text for w in ["이미 출석", "참여 완료", "출석 완료"]):
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

