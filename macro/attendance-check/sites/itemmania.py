import time
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class ItemmaniaAttendanceChecker(BaseAttendanceChecker):
    """
    아이템매니아 (ItemMania) 네이버 소셜 로그인 및 출석체크 자동화 클래스
    - 로그인 URL: https://www.itemmania.com/portal/user/login_form.html (네이버 소셜 로그인)
    - 출석체크 URL: https://www.itemmania.com/event/event_ing/e190417_attend/
    """

    def __init__(self):
        super().__init__(site_key="itemmania", display_name="아이템매니아")

    def _close_overlay_popups(self, page: Page):
        """
        아이템매니아 레이어 팝업 닫기
        """
        try:
            popup_close_selectors = [
                "button:has-text('닫기')",
                "a:has-text('닫기')",
                "img[alt*='닫기']",
                ".btn_close",
                "a[onclick*='close']",
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
        아이템매니아 네이버 소셜 로그인 수행
        """
        login_url = site_info.get("login_url", "https://www.itemmania.com/portal/user/login_form.html")
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "네이버 아이디 또는 비밀번호가 site_info.json에 지정되지 않았습니다."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        self._close_overlay_popups(page)

        # 1. 네이버 아이디로 로그인 버튼 클릭
        self.logger.info(f"[{self.display_name}] 네이버 로그인 버튼 클릭...")
        naver_btn = page.locator("button.btn_green, button:has-text('네이버 아이디로 로그인')").first
        naver_btn.wait_for(state="visible", timeout=10000)
        naver_btn.click()

        # 2. 네이버 로그인 페이지(nid.naver.com) 로딩 대기
        self.logger.info(f"[{self.display_name}] 네이버 로그인 폼 로딩 대기...")
        try:
            page.wait_for_url(lambda u: "naver.com" in u or "itemmania.com" in u, timeout=15000)
        except Exception:
            pass

        # 이미 네이버 세션이 있어 바로 리디렉션된 경우
        if "itemmania.com" in page.url and "login" not in page.url:
            return True, "네이버 소셜 간편 로그인 완료"

        # 3. 네이버 계정 입력
        id_input = page.locator("#id, input[name='id']").first
        pw_input = page.locator("#pw, input[name='pw']").first

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.wait_for(state="visible", timeout=5000)
        pw_input.fill(password)
        page.wait_for_timeout(500)

        # 4. 네이버 로그인 버튼 클릭
        self.logger.info(f"[{self.display_name}] 네이버 로그인 제출...")
        submit_btn = page.locator("button#loginBtn_row, button.btn_done:visible, button#log\\.login, button[type='submit']:visible").first
        submit_btn.wait_for(state="visible", timeout=10000)
        submit_btn.click()

        # 5. 로그인 및 리디렉션 결과 대기
        start_time = time.time()
        while time.time() - start_time < 12:
            # 다이얼로그 체크
            if self.captured_dialogs:
                last_msg = self.captured_dialogs[-1]
                if any(w in last_msg for w in ["없습니다", "일치하지", "오류", "틀렸", "실패", "확인", "등록되지", "잘못"]):
                    return False, last_msg

            # 네이버 로그인 폼 내부 에러 메시지 체크
            err_el = page.locator("#err_common, .error_text, .desc_error")
            if err_el.count() > 0 and err_el.first.is_visible():
                err_text = err_el.first.inner_text().strip()
                if err_text:
                    return False, f"네이버 로그인 실패: {err_text}"

            # 아이템매니아로 복귀 확인
            if "itemmania.com" in page.url and "login" not in page.url:
                return True, "네이버 로그인 성공"

            logout_btn = page.locator("a:has-text('로그아웃'), button:has-text('로그아웃'), a[href*='logout']")
            if logout_btn.count() > 0 and logout_btn.first.is_visible():
                return True, "로그인 완료"

            page.wait_for_timeout(600)

        if "itemmania.com" in page.url and "login" not in page.url:
            return True, "네이버 로그인 성공"

        return False, "네이버 로그인 실패 (계정 정보 또는 2단계 인증 확인 필요)"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        아이템매니아 출석체크 수행
        """
        attend_url = site_info.get("url", "https://www.itemmania.com/event/event_ing/e190417_attend/")
        self.logger.info(f"[{self.display_name}] 출석체크 페이지({attend_url}) 이동 중...")
        page.goto(attend_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        self._close_overlay_popups(page)

        # 1. 출석체크하기 버튼 탐색
        attend_selectors = [
            "img[alt*='출석체크하기']",
            "img[src*='btn_04']",
            "a:has-text('출석체크하기')",
            "button:has-text('출석체크하기')",
            "area[alt*='출석체크']",
            ".btn_attend",
        ]
        target_btn = None
        for sel in attend_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                target_btn = loc.first
                break

        if not target_btn:
            page_text = page.inner_text("body")
            if any(w in page_text for w in ["이미 출석", "참여 완료", "출석 완료"]):
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": "오늘 이미 출석체크에 참여하셨습니다.",
                }
            return {
                "success": False,
                "status": "CHECK_FAILED",
                "message": "출석체크 버튼을 찾을 수 없습니다.",
            }

        # 2. 버튼 클릭
        self.logger.info(f"[{self.display_name}] 출석체크 버튼 클릭...")
        target_btn.scroll_into_view_if_needed()
        target_btn.click()
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
            if any(w in dialog_msg for w in ["당첨", "지급", "적립", "마일리지", "상품권", "성공", "완료"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": dialog_msg,
                }

        return {
            "success": True,
            "status": "SUCCESS",
            "message": "출석체크 클릭 완료",
        }
