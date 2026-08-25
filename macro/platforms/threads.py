import os
import time
from pathlib import Path
import requests
from platforms.base import BaseUploader
from config import CONFIG, SESSION_DIR, get_media_type

class ThreadsUploader(BaseUploader):
    def __init__(self):
        super().__init__("Threads")
        self.access_token = CONFIG.get("META_ACCESS_TOKEN")
        self.threads_user_id = CONFIG.get("THREADS_USER_ID", "me")

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        스레드(Threads) 미디어(동영상/사진/GIF) 업로드
        1. Threads API 토큰이 있는 경우 공식 API 사용
        2. 없는 경우 Playwright 웹 자동화 사용
        """
        caption = metadata.get("full_caption", "")
        media_type = get_media_type(media_path)
        self.logger.info(f"Threads 업로드 시작 ({media_type.upper()}): {media_path.name}")

        # 방법 1: 공식 Threads API (공개 URL 호스팅 미디어 필요)
        if self.access_token:
            self.logger.info("Threads API를 통한 업로드를 시도합니다.")
            pass

        # 방법 2: Playwright 웹 브라우저 자동화
        return self._upload_via_playwright(media_path, caption)

    def _upload_via_playwright(self, media_path: Path, caption: str) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_threads"
            user_data_dir.mkdir(exist_ok=True)

            media_type = get_media_type(media_path)
            self.logger.info("Threads 브라우저를 실행합니다...")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.on("filechooser", lambda fc: None)

                page.goto("https://www.threads.net/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                # 로그인 확인 및 대기 루프 (최대 180초)
                self.logger.info("Threads 로그인 상태 확인 중...")
                logged_in = False
                for attempt in range(36):  # 5초 * 36 = 180초
                    # 로그인 완료 지표 확인 (스레드 시작 박스, 만들기 아이콘, 프로필 링크 등)
                    start_box = page.locator(
                        "div:has-text('스레드를 시작하세요...'), "
                        "div:has-text('Start a thread...'), "
                        "svg[aria-label='만들기'], "
                        "svg[aria-label='Create'], "
                        "a[aria-label*='프로필'], "
                        "a[aria-label*='Profile']"
                    )
                    if start_box.count() > 0:
                        logged_in = True
                        self.logger.info("Threads 로그인 확인 완료!")
                        break

                    if attempt == 0 or attempt % 6 == 0:
                        self.logger.info("Threads 로그인이 필요합니다. 브라우저에서 인스타그램/Threads 계정으로 로그인해 주세요 (대기 중)...")

                    page.wait_for_timeout(5000)

                if not logged_in:
                    self.logger.error("Threads 로그인 대기 시간이 초과되었습니다.")
                    page.wait_for_timeout(5000)
                    browser.close()
                    return False

                self.logger.info("새 스레드 작성 시작...")
                page.wait_for_timeout(2000)
                
                # '스레드를 시작하세요...' 또는 만들기 버튼 클릭
                create_triggers = page.locator(
                    "div:has-text('스레드를 시작하세요...'), "
                    "div:has-text('Start a thread...'), "
                    "svg[aria-label='만들기'], "
                    "svg[aria-label='Create']"
                )
                if create_triggers.count() > 0:
                    try:
                        create_triggers.first.click()
                        page.wait_for_timeout(1000)
                    except Exception:
                        pass

                # 내용 입력
                textbox = page.locator("div[role='textbox'], div[contenteditable='true']")
                if textbox.count() > 0:
                    try:
                        textbox.first.click()
                        page.wait_for_timeout(300)
                        page.keyboard.insert_text(caption)
                        page.wait_for_timeout(1000)
                        self.logger.info("스레드 내용 입력 완료!")
                    except Exception as e:
                        self.logger.warning(f"스레드 텍스트 입력 실패 (무시): {e}")

                # 파일 첨부 (파일 인풋 찾기)
                file_input = page.locator("input[type='file']")
                if file_input.count() > 0:
                    self.logger.info(f"{media_type.upper()} 파일 첨부 중...")
                    file_input.first.set_input_files(str(media_path.resolve()))
                    wait_sec = 10 if media_type == "video" else 3
                    page.wait_for_timeout(wait_sec * 1000)

                # 게시 버튼 클릭
                post_btn = page.locator("div[role='button']:has-text('게시'), div[role='button']:has-text('Post'), button:has-text('게시'), button:has-text('Post')")
                if post_btn.count() > 0:
                    target_btn = post_btn.first
                    for _ in range(15):
                        try:
                            if target_btn.is_enabled():
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)

                    target_btn.click(force=True)
                    self.logger.info("게시하기 버튼 클릭 완료. 서버 전송 대기 (10초)...")
                    page.wait_for_timeout(10000)
                    self.logger.info("🎉 Threads 업로드 성공 완료!")
                    browser.close()
                    return True

                self.logger.error("Threads 게시 버튼을 찾을 수 없습니다.")
                page.wait_for_timeout(5000)
                browser.close()
                return False
        except Exception as e:
            self.logger.error(f"Playwright Threads 업로드 실패: {e}")
            return False


