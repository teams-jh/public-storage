import time
from typing import Any, Dict
from urllib.parse import urlsplit

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class OndiskAttendanceChecker(BaseAttendanceChecker):
    """
    온디스크 (OnDisk) 복불복 출석체크 슬롯머신/룰렛 자동화 클래스
    - 로그인 URL: https://new.ondisk.co.kr/
    - 출석체크 URL: https://new.ondisk.co.kr/event/746?page=2
    """

    def __init__(self, screenshot_delay_sec: int = 15):
        super().__init__(site_key="ondisk", display_name="온디스크", screenshot_delay_sec=screenshot_delay_sec)

    @staticmethod
    def _site_url(configured_url: str, current_url: str) -> str:
        """기존 설정 파일의 주소는 개편된 사이트 주소로 바꿉니다."""
        return current_url if urlsplit(configured_url).hostname == "ondisk.co.kr" else configured_url

    @staticmethod
    def _result(message: str) -> Dict[str, Any]:
        """출석 결과 문구를 실행 결과로 변환합니다."""
        message = " ".join(message.split())
        if "로그인" in message:
            return {"success": False, "status": "LOGIN_REQUIRED", "message": message}
        if any(word in message for word in ("이미", "완료하셨", "참여하셨", "내일 다시")):
            return {"success": False, "status": "ALREADY_CHECKED", "message": message}
        if any(word in message for word in ("당첨", "지급", "적립", "포인트", "캐쉬", "성공", "완료")):
            return {"success": True, "status": "SUCCESS", "message": message}
        return {"success": False, "status": "CHECK_FAILED", "message": message}

    def _close_overlay_popups(self, page: Page):
        """출석 영역을 가리는 상단 광고 배너를 닫습니다."""
        for selector in (
            ".header-banner__close",
            ".page-header-topbnnr2 .btn_close",
        ):
            try:
                button = page.locator(selector).first
                if button.count() and button.is_visible():
                    button.click(timeout=1000)
            except Exception:
                pass

    def login(self, page: Page, site_info: Dict[str, Any]) -> tuple[bool, str]:
        """
        온디스크 회원 로그인 수행
        """
        login_url = self._site_url(
            site_info.get("login_url", "https://new.ondisk.co.kr/"),
            "https://new.ondisk.co.kr/",
        )
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "아이디 또는 비밀번호를 설정해 주세요."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        self._close_overlay_popups(page)

        # 재시도 때 이미 로그인된 세션이면 입력창을 다시 찾지 않습니다.
        logged_in = page.locator("a:has-text('로그아웃'):visible, button:has-text('로그아웃'):visible")
        profile_attendance = page.get_by_text("출석하기", exact=True)
        if logged_in.count() or (profile_attendance.count() and profile_attendance.first.is_visible()):
            return True, "이미 로그인했어요."

        notice_button = page.locator(".ajs-modal .ajs-button:has-text('확인'):visible").first
        if notice_button.count():
            notice_button.click()

        # 새 사이트는 userid/password, 기존 사이트는 mb_id/mb_pw를 사용합니다.
        new_login = page.locator(".login-insert__input--text[name='userid']:visible")
        is_new_site = urlsplit(page.url).hostname == "new.ondisk.co.kr"
        id_input = new_login.first if is_new_site else page.locator("input[name='mb_id']:visible").first
        pw_input = (
            page.locator(".login-insert__input--text[name='password']:visible").first
            if is_new_site else page.locator("input[name='mb_pw']:visible").first
        )

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.wait_for(state="visible", timeout=5000)
        pw_input.fill(password)
        # 로그인 버튼 클릭
        self.logger.info(f"[{self.display_name}] 로그인 버튼 클릭...")
        self.captured_dialogs.clear()
        login_btn = (
            page.locator(".login-button__button:visible").first
            if is_new_site else page.locator("input[alt='로그인']:visible").first
        )
        login_btn.click()

        # 로그인 결과를 실제 화면에서 확인합니다.
        start_time = time.monotonic()
        while time.monotonic() - start_time < 15:
            if logged_in.count() or (profile_attendance.count() and profile_attendance.first.is_visible()):
                return True, "로그인했어요."
            if self.captured_dialogs:
                message = self.captured_dialogs[-1]
                if any(word in message for word in ("아이디", "비밀번호", "로그인")):
                    return False, message
                self.captured_dialogs.clear()
            alert = page.locator(".ajs-content:visible").first
            if alert.count():
                message = alert.inner_text().strip()
                if any(word in message for word in ("아이디", "비밀번호", "로그인")) and any(
                    word in message for word in ("확인", "틀", "없", "일치", "실패", "필요", "다시")
                ):
                    return False, message
                notice_button = page.locator(".ajs-modal .ajs-button:has-text('확인'):visible").first
                if notice_button.count():
                    notice_button.click()

            page.wait_for_timeout(500)

        return False, "로그인 상태를 확인하지 못했어요. 아이디와 비밀번호를 확인해 주세요."

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """로그인 후 프로필의 출석하기 버튼을 눌러 출석을 진행합니다."""
        main_url = "https://new.ondisk.co.kr/"
        self.logger.info(f"[{self.display_name}] 메인 페이지({main_url}) 접속 중...")
        page.goto(main_url, wait_until="domcontentloaded", timeout=30000)
        self._close_overlay_popups(page)

        notice = page.locator(".ajs-content:visible").first
        if notice.count():
            message = notice.inner_text().strip()
            if "로그인" in message:
                return {"success": False, "status": "LOGIN_REQUIRED", "message": message}
            notice_button = page.locator(".ajs-modal .ajs-button:has-text('확인'):visible").first
            if notice_button.count():
                notice_button.click()

        attendance_link = page.get_by_text("출석하기", exact=True).first
        try:
            attendance_link.wait_for(state="visible", timeout=10000)
        except Exception:
            return {
                "success": False,
                "status": "CHECK_FAILED",
                "message": "프로필의 출석하기 버튼을 찾지 못했어요.",
            }

        self.logger.info(f"[{self.display_name}] 프로필의 출석하기 버튼 클릭...")
        try:
            attendance_link.click(timeout=5000)
        except PlaywrightTimeoutError:
            # 고정 헤더가 좌표 클릭을 가릴 때는 링크의 클릭 동작을 실행합니다.
            if not urlsplit(page.url).path.startswith("/event/"):
                attendance_link.evaluate("element => (element.closest('a, button') || element).click()")
        self.logger.info(f"[{self.display_name}] 출석하기 클릭 후 URL: {page.url}")
        self._close_overlay_popups(page)

        frame = page.frame(url=lambda url: "/event/20140409_attend/" in url)
        target = frame or page

        start_btn = target.locator("#js-roulette button").first
        try:
            start_btn.wait_for(state="visible", timeout=10000)
        except Exception:
            return {
                "success": False,
                "status": "CHECK_FAILED",
                "message": "출석체크 버튼을 찾지 못했어요.",
            }

        self.captured_dialogs.clear()
        self.logger.info(f"[{self.display_name}] 출석체크 START 버튼 클릭...")
        start_btn.click()

        # 룰렛 애니메이션 후 AlertifyJS 또는 기존 레이어가 결과를 표시합니다.
        start_time = time.monotonic()
        while time.monotonic() - start_time < 15:
            if self.captured_dialogs:
                return self._result(self.captured_dialogs[-1])
            for scope in (page, frame) if frame else (page,):
                for selector in (".ajs-content:visible", "#js-layerAttend:visible"):
                    popup = scope.locator(selector).first
                    if popup.count():
                        message = popup.inner_text().strip()
                        if message:
                            self.logger.info(f"[{self.display_name}] 출석 결과: {message}")
                            return self._result(message)
            page.wait_for_timeout(500)

        return {
            "success": False,
            "status": "CHECK_FAILED",
            "message": "출석체크 결과를 확인하지 못했어요.",
        }
