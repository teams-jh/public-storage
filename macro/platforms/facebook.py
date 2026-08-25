import os
import time
from pathlib import Path
import requests
from platforms.base import BaseUploader
from config import CONFIG, SESSION_DIR, get_media_type

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
            self.logger.info("Facebook 브라우저를 실행합니다...")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인
                if "login" in page.url:
                    self.logger.info("Facebook 로그인이 필요합니다. 브라우저에서 로그인해 주세요 (60초 대기)...")
                    if self.email and self.password:
                        try:
                            page.fill("#email", self.email)
                            page.fill("#pass", self.password)
                            page.click("button[name='login']")
                            page.wait_for_timeout(5000)
                        except Exception:
                            pass
                    page.wait_for_url("https://www.facebook.com/", timeout=60000)

                self.logger.info("Facebook 게시물 작성창 열기...")
                # 메인 피드의 '무슨 생각을 하고 계신가요?' 클릭
                create_box = page.locator("div[role='button']:has-text('무슨 생각을 하고 계신가요?'), div[role='button']:has-text(\"What's on your mind?\")")
                if create_box.count() > 0:
                    create_box.first.click()
                    page.wait_for_timeout(2000)

                    # 텍스트 입력
                    textbox = page.locator("div[role='textbox'], div[contenteditable='true']")
                    if textbox.count() > 0:
                        textbox.first.fill(caption)
                        page.wait_for_timeout(1000)

                    # 사진/동영상 첨부
                    file_input = page.locator("input[type='file']")
                    if file_input.count() > 0:
                        file_input.first.set_input_files(str(media_path.resolve()))
                        wait_sec = 15 if media_type == "video" else 5
                        self.logger.info(f"{media_type.capitalize()} 업로드 및 처리 대기 ({wait_sec}초)...")
                        page.wait_for_timeout(wait_sec * 1000)

                    # 게시 버튼 클릭
                    post_btn = page.locator("div[aria-label='게시'], div[aria-label='Post']")
                    if post_btn.count() > 0:
                        post_btn.first.click()
                        self.logger.info("게시 중... 완료 대기 (10초)")
                        page.wait_for_timeout(10000)
                        self.logger.info("Facebook 업로드 성공 완료!")
                        browser.close()
                        return True

                browser.close()
                return True
        except Exception as e:
            self.logger.error(f"Playwright Facebook 업로드 실패: {e}")
            return False

