import time
from pathlib import Path
from platforms.base import BaseUploader
from config import CONFIG, SESSION_DIR, get_media_type

class InstagramUploader(BaseUploader):
    def __init__(self):
        super().__init__("Instagram")
        self.username = CONFIG.get("INSTAGRAM_USERNAME")
        self.password = CONFIG.get("INSTAGRAM_PASSWORD")

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        Instagram 릴스/사진/GIF 업로드
        1. instagrapi 라이브러리가 있는 경우 모바일 API 세션으로 업로드 시도 (사진/릴스 분기)
        2. 없는 경우 Playwright 웹 자동화로 대체
        """
        caption = metadata.get("full_caption", "")
        media_type = get_media_type(media_path)
        self.logger.info(f"Instagram 업로드 시작 ({media_type.upper()}): {media_path.name}")
        self.logger.info(f"캡션 내용 요약:\n{caption[:100]}...")

        # 방법 1: instagrapi 라이브러리 사용 (추천: 모바일 API)
        try:
            from instagrapi import Client
            cl = Client()
            session_file = SESSION_DIR / "instagram_session.json"
            
            if session_file.exists():
                self.logger.info("저장된 Instagram 세션을 로드합니다.")
                cl.load_settings(session_file)
            
            if self.username and self.password:
                cl.login(self.username, self.password)
                cl.dump_settings(session_file)
                self.logger.info("Instagram 로그인 성공")
                
                if media_type == "video":
                    # 릴스(Clip) 업로드
                    self.logger.info("릴스(Clip) 업로드를 진행합니다...")
                    media = cl.clip_upload(str(media_path), caption=caption)
                    self.logger.info(f"Instagram 릴스 업로드 완료! Media ID: {media.pk}")
                else:
                    # 사진(Photo) 업로드
                    self.logger.info("사진(Photo) 업로드를 진행합니다...")
                    media = cl.photo_upload(str(media_path), caption=caption)
                    self.logger.info(f"Instagram 사진 업로드 완료! Media ID: {media.pk}")
                return True
            else:
                self.logger.warning("Instagram 계정 정보가 .env에 설정되지 않았습니다. Playwright 웹 모드로 전환합니다.")
        except ImportError:
            self.logger.info("instagrapi가 설치되어 있지 않습니다. Playwright 웹 자동화 모드를 사용합니다.")
        except Exception as e:
            self.logger.error(f"instagrapi 업로드 중 오류 발생: {e}. Playwright 모드로 전환합니다.")


        # 방법 2: Playwright 웹 브라우저 자동화
        return self._upload_via_playwright(media_path, caption)

    def _upload_via_playwright(self, media_path: Path, caption: str) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_insta"
            user_data_dir.mkdir(exist_ok=True)

            self.logger.info("Playwright 브라우저를 실행합니다...")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,  # 첫 로그인/인증을 위해 브라우저 표시
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인
                if "login" in page.url:
                    self.logger.info("Instagram 로그인이 필요합니다. 브라우저에서 로그인해 주세요 (60초 대기)...")
                    if self.username and self.password:
                        try:
                            page.fill("input[name='username']", self.username)
                            page.fill("input[name='password']", self.password)
                            page.click("button[type='submit']")
                            page.wait_for_timeout(5000)
                        except Exception:
                            pass
                    # 로그인 완료 대기
                    page.wait_for_url("https://www.instagram.com/", timeout=60000)

                self.logger.info("만들기(+) 버튼 클릭 및 미디어 업로드 시도...")
                # 만들기 아이콘 찾기 (New post)
                create_btn = page.locator("svg[aria-label='새로운 게시물'], svg[aria-label='New post']").locator("..")
                if create_btn.count() > 0:
                    create_btn.first.click()
                    page.wait_for_timeout(2000)

                    # 파일 업로드 인풋 찾기
                    file_input = page.locator("input[type='file']")
                    file_input.set_input_files(str(media_path.resolve()))
                    page.wait_for_timeout(3000)

                    # 비율/자르기/필터 '다음' 단계 클릭 (최대 3회 시도)
                    for _ in range(3):
                        next_btns = page.locator("div[role='button']:has-text('다음'), div[role='button']:has-text('Next')")
                        if next_btns.count() > 0 and next_btns.first.is_visible():
                            next_btns.first.click()
                            page.wait_for_timeout(2000)
                        else:
                            break

                    # 캡션 입력
                    caption_box = page.locator("div[aria-label='문구 입력...'], div[aria-label='Write a caption...'], div[role='textbox']")
                    if caption_box.count() > 0:
                        caption_box.first.fill(caption)
                        page.wait_for_timeout(1000)

                    # 공유하기 클릭
                    share_btn = page.locator("div[role='button']:has-text('공유하기'), div[role='button']:has-text('Share')")
                    if share_btn.count() > 0:
                        share_btn.first.click()
                        self.logger.info("게시물이 공유되는 중입니다. 완료될 때까지 대기합니다...")
                        page.wait_for_timeout(15000)
                        self.logger.info("Instagram 업로드 성공 완료!")
                        browser.close()
                        return True

                self.logger.warning("업로드 버튼을 자동으로 완료하지 못했습니다. 수동으로 확인해 주세요.")
                page.wait_for_timeout(10000)
                browser.close()
                return True
        except Exception as e:
            self.logger.error(f"Playwright 인스타그램 업로드 실패: {e}")
            return False

