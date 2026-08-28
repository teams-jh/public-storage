import time
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from sites.base import BaseAttendanceChecker


class HeypollAttendanceChecker(BaseAttendanceChecker):
    """
    헤이폴 (HeyPoll) 카카오 소셜 로그인 및 출석/서베이 자동화 클래스
    - 로그인 URL: https://www.heypoll.co.kr/login (카카오 계정 로그인)
    - 메인/서베이 URL: https://www.heypoll.co.kr/survey/surveys
    - 투표/폴 URL: https://www.heypoll.co.kr/survey/polls
    """

    def __init__(self):
        super().__init__(site_key="heypoll", display_name="헤이폴")

    def _close_overlay_popups(self, page: Page):
        """
        헤이폴 레이어 팝업 / 공지 닫기
        """
        try:
            popup_close_selectors = [
                "button:has-text('닫기')",
                "button:has-text('오늘 하루 보지 않기')",
                "a:has-text('닫기')",
                ".btn_close",
                "button:has-text('확인')",
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
        헤이폴 카카오 소셜 로그인 수행
        """
        login_url = site_info.get("login_url", "https://www.heypoll.co.kr/login")
        user_id = site_info.get("id", "")
        password = site_info.get("password", "")

        if not user_id or not password:
            return False, "카카오 아이디 또는 비밀번호가 site_info.json에 지정되지 않았습니다."

        self.logger.info(f"[{self.display_name}] 로그인 페이지({login_url}) 접속 중...")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        self._close_overlay_popups(page)

        # 1. 카카오 로그인 버튼(노란 원형 아이콘) 탐색 및 팝업 대기
        self.logger.info(f"[{self.display_name}] 카카오 로그인 버튼 클릭 및 팝업 대기...")
        kakao_btn = page.locator("section span.cursor-pointer, section svg path[fill='#FEE500']").first

        if not kakao_btn.is_visible():
            # 대체 선택자
            kakao_btn = page.locator("section > *").first

        try:
            with page.context.expect_page(timeout=10000) as popup_info:
                kakao_btn.click()
            kakao_popup = popup_info.value
            kakao_popup.wait_for_load_state("domcontentloaded", timeout=15000)
            kakao_popup.wait_for_timeout(1000)
        except Exception as e:
            # 팝업 대신 현재 페이지 리디렉션 확인
            if "kakao.com" in page.url:
                kakao_popup = page
            else:
                return False, f"카카오 로그인 팝업 호출 실패: {e}"

        self.logger.info(f"[{self.display_name}] 카카오 로그인 폼 입력 중... ({kakao_popup.url})")

        # 2. 카카오 계정 입력
        id_input = kakao_popup.locator("input[name='loginId'], #loginId--1, input[type='text']").first
        pw_input = kakao_popup.locator("input[name='password'], #password--2, input[type='password']").first

        id_input.wait_for(state="visible", timeout=10000)
        id_input.fill(user_id)
        pw_input.wait_for(state="visible", timeout=5000)
        pw_input.fill(password)
        kakao_popup.wait_for_timeout(500)

        # 3. 카카오 로그인 버튼 클릭
        self.logger.info(f"[{self.display_name}] 카카오 로그인 제출...")
        submit_btn = kakao_popup.locator("button[type='submit'], button.submit, button.highlight").first
        submit_btn.click()

        # 4. 카카오 인증 및 리디렉션 결과 대기
        start_time = time.time()
        while time.time() - start_time < 12:
            # 팝업 내부 에러 메시지 체크
            if not kakao_popup.is_closed():
                err_el = kakao_popup.locator(".desc_error, .info_tf, .error_text, p[class*='error']")
                if err_el.count() > 0 and err_el.first.is_visible():
                    err_msg = err_el.first.inner_text().strip()
                    if err_msg:
                        kakao_popup.close()
                        return False, f"카카오 로그인 실패: {err_msg}"

            # 메인 페이지 URL 또는 프로필 노출 체크
            if "login" not in page.url:
                return True, "카카오 로그인 성공"

            # 로그인 완료 후 메뉴/프로필/마이페이지 요소 확인
            logout_btn = page.locator("a:has-text('로그아웃'), button:has-text('로그아웃'), a[href*='logout']")
            if logout_btn.count() > 0 and logout_btn.first.is_visible():
                return True, "카카오 로그인 완료"

            page.wait_for_timeout(600)

        # 팝업이 닫히고 메인 페이지로 복귀했는지 확인
        if "login" not in page.url:
            return True, "카카오 로그인 성공"

        return False, "카카오 로그인 실패 (계정 정보 또는 2단계 인증 확인 필요)"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        헤이폴 서베이 / 투표 페이지 이동 및 출석 확인
        """
        target_url = site_info.get("url", "https://www.heypoll.co.kr/survey/surveys")
        self.logger.info(f"[{self.display_name}] 서베이 페이지({target_url}) 이동 중...")
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        self._close_overlay_popups(page)

        # 1. 서베이 목록 또는 퀵서베이 확인
        self.logger.info(f"[{self.display_name}] 이용 가능한 서베이 확인 중...")
        
        # 투표 탭(데일리 투표) 확인
        poll_tab = page.locator("a:has-text('투표'), button:has-text('투표')").first
        if poll_tab.count() > 0 and poll_tab.is_visible():
            poll_tab.click()
            page.wait_for_timeout(1500)

        # 투표 항목 탐색
        poll_items = page.locator("a[href*='/survey/polls/']")
        if poll_items.count() > 0:
            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"헤이폴 정상 접속 및 참여 가능 서베이/투표 {poll_items.count()}건 확인 완료",
            }

        return {
            "success": True,
            "status": "SUCCESS",
            "message": "헤이폴 로그인 및 서베이 페이지 접속 완료",
        }
