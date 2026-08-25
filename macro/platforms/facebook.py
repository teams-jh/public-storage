import os
import time
from pathlib import Path
import requests
from platforms.base import BaseUploader
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

class FacebookUploader(BaseUploader):
    def __init__(self):
        super().__init__("Facebook")
        self.access_token = CONFIG.get("META_ACCESS_TOKEN")
        self.page_id = CONFIG.get("FACEBOOK_PAGE_ID")
        self.email = CONFIG.get("FACEBOOK_EMAIL")
        self.password = CONFIG.get("FACEBOOK_PASSWORD")

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        Facebook 페이지 또는 프로필에 미디어(동영상/사진/GIF) 업로드
        1. Meta Graph API (페이지 비디오/사진 업로드)
        2. Playwright 웹 브라우저 자동화
        """
        title = metadata.get("title", "")
        description = metadata.get("full_caption", "")
        media_type = get_media_type(media_path)
        self.logger.info(f"Facebook 업로드 시작 ({media_type.upper()}): {media_path.name}")

        # 방법 1: Facebook Graph API (페이지 업로드)
        if self.access_token and self.page_id:
            try:
                self.logger.info("Facebook Graph API를 통해 페이지에 미디어를 업로드합니다...")
                
                with open(media_path, "rb") as media_file:
                    files = {"source": media_file}
                    if media_type == "video":
                        url = f"https://graph-video.facebook.com/v19.0/{self.page_id}/videos"
                        payload = {
                            "access_token": self.access_token,
                            "title": title,
                            "description": description
                        }
                    else:
                        # 사진 / GIF
                        url = f"https://graph.facebook.com/v19.0/{self.page_id}/photos"
                        payload = {
                            "access_token": self.access_token,
                            "caption": description
                        }

                    response = requests.post(url, data=payload, files=files)
                    result = response.json()
                    
                    if "id" in result or "post_id" in result:
                        post_id = result.get("id") or result.get("post_id")
                        self.logger.info(f"Facebook Graph API 업로드 성공! ID: {post_id}")
                        return True
                    else:
                        self.logger.error(f"Facebook Graph API 에러 응답: {result}")
            except Exception as e:
                self.logger.error(f"Facebook Graph API 업로드 실패: {e}")

        # 방법 2: Playwright 웹 브라우저 자동화
        return self._upload_via_playwright(media_path, description)

    def _upload_via_playwright(self, media_path: Path, caption: str) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_facebook"
            user_data_dir.mkdir(exist_ok=True)

            media_type = get_media_type(media_path)
            size_mb = get_media_size_mb(media_path)
            upload_timeout = get_dynamic_upload_timeout(media_path)
            sync_buffer = get_dynamic_sync_buffer(media_path)

            self.logger.info(f"Facebook 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 세션 유지: {sync_buffer}초)")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인 및 대기 루프 (최대 180초)
                self.logger.info("Facebook 로그인 상태 확인 중...")
                logged_in = False
                for attempt in range(36):  # 5초 * 36 = 180초
                    create_box = page.locator("div[role='button']:has-text('무슨 생각을 하고 계신가요?'), div[role='button']:has-text(\"What's on your mind?\")")
                    if create_box.count() > 0:
                        logged_in = True
                        self.logger.info("Facebook 로그인 확인 완료!")
                        break

                    if attempt == 0 or attempt % 6 == 0:
                        self.logger.info("Facebook 로그인이 필요합니다. 브라우저에서 로그인해 주세요 (대기 중)...")

                    page.wait_for_timeout(5000)

                if not logged_in:
                    self.logger.error("Facebook 로그인 대기 시간이 초과되었습니다.")
                    page.wait_for_timeout(5000)
                    browser.close()
                    return False

                self.logger.info("Facebook 게시물 작성창 열기...")
                create_box = page.locator("div[role='button']:has-text('무슨 생각을 하고 계신가요?'), div[role='button']:has-text(\"What's on your mind?\")")
                if create_box.count() > 0:
                    create_box.first.click()
                    page.wait_for_timeout(2000)

                    # 텍스트 입력
                    textbox = page.locator("div[role='textbox'], div[contenteditable='true']")
                    if textbox.count() > 0:
                        try:
                            textbox.first.click()
                            page.wait_for_timeout(300)
                            page.keyboard.insert_text(caption)
                            page.wait_for_timeout(1000)
                        except Exception:
                            textbox.first.fill(caption)

                    # 사진/동영상 첨부
                    file_input = page.locator("input[type='file']")
                    if file_input.count() > 0:
                        file_input.first.set_input_files(str(media_path.resolve()))
                        render_wait = max(5, int(size_mb * 1.5)) if media_type == "video" else 3
                        self.logger.info(f"{media_type.capitalize()} 업로드 및 렌더링 대기 중 ({render_wait}초)...")
                        page.wait_for_timeout(render_wait * 1000)

                    # 게시 버튼 클릭
                    post_btn = page.locator("div[aria-label='게시'], div[aria-label='Post']")
                    if post_btn.count() > 0:
                        target_btn = post_btn.first
                        for _ in range(30):
                            try:
                                if target_btn.is_enabled():
                                    break
                            except Exception:
                                pass
                            page.wait_for_timeout(1000)

                        target_btn.click(force=True)
                        self.logger.info(f"게시 중... 서버 완료 대기 중 (최대 {upload_timeout}초)...")
                        
                        # 게시 완료 상태 확인 (최대 upload_timeout초)
                        fb_done = False
                        for _ in range(upload_timeout):
                            page.wait_for_timeout(1000)
                            dialog = page.locator("div[role='dialog']")
                            if dialog.count() == 0:
                                fb_done = True
                                self.logger.info("🎉 Facebook 작성 모달이 닫혀 게시가 완료되었습니다!")
                                break

                        if fb_done:
                            self.logger.info(f"업로드 세션 안전 동기화 중 ({sync_buffer}초간 넉넉하게 대기)...")
                            page.wait_for_timeout(sync_buffer * 1000)
                            self.logger.info("🎉 Facebook 업로드 최종 성공 완료!")
                            browser.close()
                            return True
                        else:
                            self.logger.warning("Facebook 서버 전송 완료 확인을 받지 못했습니다.")
                            page.wait_for_timeout(5000)
                            browser.close()
                            return False

                self.logger.error("Facebook 게시 버튼을 찾을 수 없습니다.")
                page.wait_for_timeout(5000)
                browser.close()
                return False


        except Exception as e:
            self.logger.error(f"Playwright Facebook 업로드 실패: {e}")
            return False
