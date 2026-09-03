import time
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class OndiskAttendanceChecker(BaseAttendanceChecker):
    """
    온디스크 (OnDisk) 복불복 출석체크 슬롯머신/룰렛 자동화 클래스
    - 로그인 URL: https://ondisk.co.kr/index.php
    - 메인 URL: https://ondisk.co.kr/
    - 출석체크 URL: https://ondisk.co.kr/index.php?mode=eventMarge&sm=event&action=view&idx=746&event_page=1
    """

    def __init__(self, screenshot_delay_sec: int = 15):
        super().__init__(site_key="ondisk", display_name="온디스크", screenshot_delay_sec=screenshot_delay_sec)

    def _close_overlay_popups(self, page: Page):
        """
        온디스크 메인/레이어 팝업 닫기
        """
        try:
            popup_close_selectors = [
                "button:has-text('닫기')",
                "a:has-text('닫기')",
                "img[alt*='닫기']",
                ".btn_close",
                ".header-banner__top-bnnr--check .btn_close",
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
        온디스크 회원 로그인 수행
        """
        login_url = site_info.get("login_url", "https://ondisk.co.kr/index.php")
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

        # 3. 로그인 결과 대기
        start_time = time.time()
        while time.time() - start_time < 8:
            if self.captured_dialogs:
                last_msg = self.captured_dialogs[-1]
                if any(w in last_msg for w in ["없습니다", "일치하지", "오류", "틀렸", "실패"]):
                    return False, last_msg
                if any(w in last_msg for w in ["성공", "환영"]):
                    return True, last_msg

            logout_btn = page.locator("a:has-text('로그아웃'), img[alt*='로그아웃'], .login_after, #page-loginInfo")
            if logout_btn.count() > 0 and logout_btn.first.is_visible():
                return True, "로그인 완료"

            page.wait_for_timeout(500)

        if page.locator("input[name='mb_id']").count() > 0 and page.locator("input[name='mb_id']").first.is_visible():
            if self.captured_dialogs:
                return False, self.captured_dialogs[-1]
            return False, "로그인 실패 (아이디 또는 비밀번호 확인 필요)"

        return True, "로그인 완료"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        온디스크 출석체크 수행
        - 로그인 후 https://ondisk.co.kr/ 로 재이동
        - 좌측 프로필 영역의 '출석하기' 버튼 클릭하여 이동
        - eventFrame 내부의 '출석체크 START' 버튼 클릭
        """
        main_url = "https://ondisk.co.kr/"
        attend_url = site_info.get(
            "url",
            "https://ondisk.co.kr/index.php?mode=eventMarge&sm=event&action=view&idx=746&event_page=1",
        )

        # 1. 443 에러 및 리디렉션 방지를 위해 메인 페이지(https://ondisk.co.kr/)로 재이동
        self.logger.info(f"[{self.display_name}] 메인 페이지({main_url})로 이동 중...")
        try:
            page.goto(main_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.warning(f"[{self.display_name}] 메인 페이지 이동 경고: {e}")

        self._close_overlay_popups(page)

        # 2. 좌측 사용자 정보 영역의 '출석하기' 버튼 클릭
        self.logger.info(f"[{self.display_name}] 좌측 정보창 '출석하기' 버튼 클릭 중...")
        check_btn = page.locator("li.check a, a:has-text('출석하기'), a[href*='idx=746']").first
        if check_btn.count() > 0 and check_btn.is_visible():
            check_btn.click()
        else:
            self.logger.info(f"[{self.display_name}] 직접 출석체크 URL({attend_url})로 이동...")
            page.goto(attend_url, wait_until="domcontentloaded", timeout=30000)

        page.wait_for_timeout(3000)
        self._close_overlay_popups(page)

        # 3. 이벤트 iframe (eventFrame) 탐색
        frame = page.frame(name="eventFrame") or page.frame(url=lambda u: "attend" in u)
        if not frame:
            for f in page.frames:
                if "attend" in f.url:
                    frame = f
                    break

        self.captured_dialogs.clear()

        # 4. 출석체크 START 버튼 클릭
        if frame:
            self.logger.info(f"[{self.display_name}] eventFrame 내부 '출석체크 START' 버튼 클릭...")
            start_btn = frame.locator(
                "#js-roulette button, #evtAttendance button, .button, button:has-text('START'), a:has-text('START')"
            ).first
            if start_btn.count() > 0 and start_btn.is_visible():
                start_btn.click()
            else:
                frame.evaluate("() => { const b = document.querySelector('#js-roulette .button, #evtAttendance .button, button'); if (b) b.click(); }")
        else:
            self.logger.info(f"[{self.display_name}] 메인 페이지의 출석체크 버튼 클릭 시도...")
            start_btn = page.locator("#js-roulette button, #evtAttendance button, .button").first
            if start_btn.count() > 0:
                start_btn.click()

        page.wait_for_timeout(3500)

        # 5. 브라우저 Alert 다이얼로그 확인
        if self.captured_dialogs:
            dialog_msg = self.captured_dialogs[-1]
            self.logger.info(f"[{self.display_name}] 다이얼로그 수신: {dialog_msg}")
            if "로그인" in dialog_msg:
                return {
                    "success": False,
                    "status": "LOGIN_REQUIRED",
                    "message": dialog_msg,
                }
            if any(w in dialog_msg for w in ["이미", "완료하셨", "참여하셨", "내일", "하루"]):
                return {
                    "success": False,
                    "status": "ALREADY_CHECKED",
                    "message": dialog_msg,
                }
            if any(w in dialog_msg for w in ["당첨", "지급", "적립", "포인트", "캐쉬", "성공", "완료"]):
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "message": dialog_msg,
                }

        # 6. 레이어 팝업(#js-layerAttend) 확인
        popup = page.locator("#js-layerAttend")
        if popup.count() > 0 and popup.first.is_visible():
            popup_text = popup.first.inner_text().strip().replace("\n", " ")
            self.logger.info(f"[{self.display_name}] 출석 결과 팝업 감지: {popup_text}")

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
            "message": "출석체크 실행 완료",
        }
