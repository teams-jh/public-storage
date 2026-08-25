import os
import time
from pathlib import Path
from platforms.base import BaseUploader
from config import CONFIG, SESSION_DIR, get_media_type

class YouTubeUploader(BaseUploader):
    def __init__(self):
        super().__init__("YouTube")
        self.client_secrets_file = CONFIG.get("YOUTUBE_CLIENT_SECRETS_FILE")

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        YouTube 동영상 / 쇼츠 업로드
        (YouTube는 동영상 파일만 지원하므로 사진/GIF의 경우 건너뜁니다)
        1. Google YouTube Data API v3 (가장 안정적 & OAuth 토큰 저장)
        2. Playwright YouTube Studio 웹 자동화
        """
        media_type = get_media_type(media_path)
        if media_type != "video":
            self.logger.warning(
                f"YouTube는 동영상(.mp4, .mov 등) 파일만 지원하므로 "
                f"이미지/GIF 파일({media_path.name})은 업로드를 건너뜁니다."
            )
            return True

        title = metadata.get("title", media_path.stem)
        description = metadata.get("full_caption", "")
        tags_raw = metadata.get("tags", "")
        # 해시태그 목록 추출
        tags = [t.strip("# ").strip() for t in tags_raw.split() if t.strip()]

        self.logger.info(f"YouTube 업로드 시작: {media_path.name}")
        self.logger.info(f"제목: {title}")

        # 방법 1: YouTube Data API v3
        secrets_path = Path(self.client_secrets_file)
        if secrets_path.exists():
            try:
                self.logger.info("YouTube Data API v3를 통해 업로드를 시작합니다...")
                return self._upload_via_api(media_path, title, description, tags)
            except Exception as e:
                self.logger.error(f"YouTube API 업로드 중 오류: {e}. Playwright 모드로 전환합니다.")

        # 방법 2: Playwright 웹 브라우저 자동화
        return self._upload_via_playwright(media_path, title, description)

    def _upload_via_api(self, video_path: Path, title: str, description: str, tags: list) -> bool:
        import pickle
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        token_file = SESSION_DIR / "youtube_token.pickle"
        creds = None

        if token_file.exists():
            with open(token_file, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_file), SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],  # 유튜브 제목 100자 제한
                "description": description,
                "tags": tags,
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": "public",  # 'public', 'private', 'unlisted'
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        self.logger.info("동영상 업로드 진행 중...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                self.logger.info(f"업로드 진행률: {progress}%")

        self.logger.info(f"YouTube 업로드 성공 완료! Video ID: {response.get('id')}")
        self.logger.info(f"URL: https://youtu.be/{response.get('id')}")
        return True

    def _upload_via_playwright(self, video_path: Path, title: str, description: str) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_youtube"
            user_data_dir.mkdir(exist_ok=True)

            self.logger.info("YouTube Studio 브라우저를 실행합니다...")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인
                if "accounts.google.com" in page.url:
                    self.logger.info("Google 로그인이 필요합니다. 브라우저에서 로그인해 주세요 (60초 대기)...")
                    page.wait_for_url("https://studio.youtube.com/**", timeout=60000)

                self.logger.info("만들기 버튼 클릭 및 파일 업로드...")
                page.wait_for_timeout(3000)

                # 만들기 버튼
                create_btn = page.locator("#create-icon, button:has-text('만들기'), button:has-text('CREATE')")
                if create_btn.count() > 0:
                    create_btn.first.click()
                    page.wait_for_timeout(1000)
                    upload_menu = page.locator("tp-yt-paper-item:has-text('동영상 업로드'), tp-yt-paper-item:has-text('Upload videos')")
                    if upload_menu.count() > 0:
                        upload_menu.first.click()
                        page.wait_for_timeout(2000)

                # 파일 선택 input
                file_input = page.locator("input[type='file']")
                if file_input.count() > 0:
                    file_input.first.set_input_files(str(video_path.resolve()))
                    self.logger.info("비디오 업로드 중... 세부정보 입력 대기")
                    page.wait_for_timeout(5000)

                    # 제목 입력
                    title_input = page.locator("#title-textarea #textbox")
                    if title_input.count() > 0:
                        title_input.first.fill(title)

                    # 설명 입력
                    desc_input = page.locator("#description-textarea #textbox")
                    if desc_input.count() > 0:
                        desc_input.first.fill(description)

                    # '아동용이 아닙니다' 라디오 버튼 클릭
                    not_for_kids = page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']")
                    if not_for_kids.count() > 0:
                        not_for_kids.first.click()

                    # 다음 버튼 3회 클릭
                    for _ in range(3):
                        next_btn = page.locator("#next-button")
                        if next_btn.count() > 0:
                            next_btn.first.click()
                            page.wait_for_timeout(1500)

                    # 공개(Public) 라디오 버튼 클릭
                    public_radio = page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
                    if public_radio.count() > 0:
                        public_radio.first.click()
                        page.wait_for_timeout(1000)

                    # 게시(Done) 버튼 클릭
                    done_btn = page.locator("#done-button")
                    if done_btn.count() > 0:
                        done_btn.first.click()
                        self.logger.info("게시 버튼 클릭 완료! 처리 대기 (10초)...")
                        page.wait_for_timeout(10000)
                        self.logger.info("YouTube 업로드 성공 완료!")
                        browser.close()
                        return True

                page.wait_for_timeout(10000)
                browser.close()
                return True
        except Exception as e:
            self.logger.error(f"Playwright YouTube 업로드 실패: {e}")
            return False

