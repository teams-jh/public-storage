import os
import time
from pathlib import Path
from platforms.base import BaseUploader
from config import CONFIG, SESSION_DIR, get_media_type

class TwitterXUploader(BaseUploader):
    def __init__(self):
        super().__init__("X_Twitter")
        self.api_key = CONFIG.get("TWITTER_API_KEY")
        self.api_secret = CONFIG.get("TWITTER_API_SECRET")
        self.access_token = CONFIG.get("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = CONFIG.get("TWITTER_ACCESS_TOKEN_SECRET")

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        X(Twitter) 미디어(동영상/사진/GIF) 및 글 업로드
        1. Tweepy API 키가 설정되어 있는 경우 공식 API 사용
        2. 없는 경우 Playwright 웹 자동화로 대체
        """
        caption = metadata.get("full_caption", "")
        # X는 기본 280자 제한 (한국어 약 140자) 고려
        if len(caption) > 270:
            caption = caption[:267] + "..."
            
        media_type = get_media_type(media_path)
        self.logger.info(f"X(Twitter) 업로드 시작 ({media_type.upper()}): {media_path.name}")

        # 방법 1: Tweepy를 통한 API 업로드
        if all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            try:
                import tweepy
                self.logger.info("Tweepy API를 통해 미디어 업로드 및 트윗 작성을 진행합니다...")
                
                # V1.1 인증 (미디어 업로드용)
                auth = tweepy.OAuth1UserHandler(
                    self.api_key, self.api_secret,
                    self.access_token, self.access_token_secret
                )
                api_v1 = tweepy.API(auth)
                
                # V2 클라이언트 (트윗 작성용)
                client_v2 = tweepy.Client(
                    consumer_key=self.api_key,
                    consumer_secret=self.api_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_token_secret
                )
                
                # 미디어 카테고리 분기
                if media_type == "gif":
                    category = "tweet_gif"
                elif media_type == "image":
                    category = "tweet_image"
                else:
                    category = "tweet_video"

                # 미디어 업로드
                media = api_v1.media_upload(
                    filename=str(media_path),
                    media_category=category
                )
                
                # 비디오 처리 완료 대기
                if media_type == "video":
                    self.logger.info(f"동영상 미디어 업로드 완료 (Media ID: {media.media_id}), 처리 대기 중...")
                    time.sleep(5)
                else:
                    self.logger.info(f"이미지/GIF 미디어 업로드 완료 (Media ID: {media.media_id})")
                    time.sleep(1)
                
                # 트윗 작성
                response = client_v2.create_tweet(text=caption, media_ids=[media.media_id])
                self.logger.info(f"X(Twitter) 트윗 작성 성공! ID: {response.data.get('id')}")
                return True
            except Exception as e:
                self.logger.error(f"Tweepy API 업로드 중 오류: {e}. Playwright 모드로 전환합니다.")

        # 방법 2: Playwright 웹 브라우저 자동화
        return self._upload_via_playwright(media_path, caption)

    def _upload_via_playwright(self, media_path: Path, caption: str) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_x"
            user_data_dir.mkdir(exist_ok=True)

            media_type = get_media_type(media_path)
            self.logger.info("X(Twitter) 브라우저를 실행합니다...")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인
                if "login" in page.url or "i/flow/login" in page.url:
                    self.logger.info("X 로그인이 필요합니다. 브라우저에서 로그인해 주세요 (60초 대기)...")
                    page.wait_for_url("https://x.com/home", timeout=60000)

                self.logger.info("트윗 작성 시작...")
                # 트윗 입력창 찾기
                textbox = page.locator("div[data-testid='tweetTextarea_0'], div[role='textbox']")
                if textbox.count() > 0:
                    textbox.first.click()
                    textbox.first.fill(caption)
                    page.wait_for_timeout(1000)

                # 미디어 파일 업로드 (file input)
                file_input = page.locator("input[data-testid='fileInput'], input[type='file']")
                if file_input.count() > 0:
                    file_input.first.set_input_files(str(media_path.resolve()))
                    wait_sec = 10 if media_type == "video" else 3
                    self.logger.info(f"{media_type.capitalize()} 업로드 및 처리 대기 ({wait_sec}초)...")
                    page.wait_for_timeout(wait_sec * 1000)

                # 게시하기(Tweet/Post) 버튼 클릭
                post_btn = page.locator("button[data-testid='tweetButtonInline'], button[data-testid='tweetButton']")
                if post_btn.count() > 0:
                    post_btn.first.click()
                    self.logger.info("게시 중... 완료 대기 (5초)")
                    page.wait_for_timeout(5000)
                    self.logger.info("X(Twitter) 업로드 성공 완료!")
                    browser.close()
                    return True

                browser.close()
                return True
        except Exception as e:
            self.logger.error(f"Playwright X(Twitter) 업로드 실패: {e}")
            return False

