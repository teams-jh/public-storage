import os
import time
from pathlib import Path
from platforms.base import BaseUploader
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

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

            size_mb = get_media_size_mb(video_path)
            upload_timeout = get_dynamic_upload_timeout(video_path)
            sync_buffer = get_dynamic_sync_buffer(video_path)

            self.logger.info(f"YouTube Studio 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 완료 후 세션유지: {sync_buffer}초)")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인 (최대 180초 대기)
                if "accounts.google.com" in page.url:
                    self.logger.info(f"Google 로그인이 필요합니다. 브라우저에서 로그인해 주세요 (최대 {LOGIN_TIMEOUT_SECONDS}초 대기)...")
                    try:
                        page.wait_for_url("https://studio.youtube.com/**", timeout=LOGIN_TIMEOUT_SECONDS * 1000)
                    except Exception:
                        self.logger.error("YouTube 로그인 대기 시간이 초과되었습니다.")
                        browser.close()
                        return False

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
                    self.logger.info(f"동영상 파일 첨부 완료! 서버 업로드 및 인코딩 진행 대기 중 (최대 {upload_timeout}초)...")
                    page.wait_for_timeout(5000)

                    # 제목 입력
                    title_input = page.locator("#title-textarea #textbox")
                    if title_input.count() > 0:
                        title_input.first.fill(title)
                        self.logger.info("동영상 제목 입력 완료")

                    # 설명 입력
                    desc_input = page.locator("#description-textarea #textbox")
                    if desc_input.count() > 0:
                        desc_input.first.fill(description)
                        self.logger.info("동영상 설명 입력 완료")

                    # '아동용이 아닙니다' 라디오 버튼 클릭
                    not_for_kids = page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']")
                    if not_for_kids.count() > 0:
                        not_for_kids.first.click()

                    # 유튜브 하단 서버 업로드 완료율 대기 (0% -> 100% / 업로드 완료 / 처리 중)
                    self.logger.info("YouTube 서버로 동영상 파일 전송 완료 대기 중...")
                    for _ in range(upload_timeout // 3):
                        page.wait_for_timeout(3000)
                        upload_status = page.locator("span.progress-label, div.progress-label, span:has-text('업로드 완료'), span:has-text('처리 완료'), span:has-text('검사 완료')")
                        if upload_status.count() > 0:
                            status_text = upload_status.first.inner_text()
                            if any(k in status_text for k in ["업로드 완료", "처리", "검사", "완료", "100%"]):
                                self.logger.info(f"동영상 업로드 상태 확인: {status_text}")
                                break

                    # 다음 버튼 3회 클릭 (세부정보 -> 동영상 요소 -> 검사 -> 공개 상태)
                    for step in range(3):
                        next_btn = page.locator("#next-button")
                        if next_btn.count() > 0:
                            next_btn.first.click()
                            page.wait_for_timeout(2000)

                    # 공개(Public) 라디오 버튼 클릭
                    public_radio = page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
                    if public_radio.count() > 0:
                        public_radio.first.click()
                        page.wait_for_timeout(1000)

                    # 게시(Done/Save) 버튼 클릭
                    done_btn = page.locator("#done-button")
                    if done_btn.count() > 0:
                        done_btn.first.click()
                        self.logger.info(f"게시(Done) 버튼 클릭 완료! 서버 최종 게시 및 링크 생성 대기 중 (최대 {upload_timeout}초)...")
                        
                        # 업로드 완료 및 링크 생성 확인 대기 (최대 upload_timeout초)
                        yt_done = False
                        for _ in range(upload_timeout):
                            page.wait_for_timeout(1000)
                            # 완료 다이얼로그에 유튜브 링크 또는 닫기 버튼이 생성된 경우
                            yt_link = page.locator("a[href*='youtu.be'], a.ytcp-video-info")
                            close_btn = page.locator("#close-button, button:has-text('닫기'), button:has-text('Close')")
                            
                            if yt_link.count() > 0:
                                href = yt_link.first.get_attribute("href") or ""
                                self.logger.info(f"🎉 YouTube 동영상 게시 완료! 링크: {href}")
                                yt_done = True
                                break
                            elif close_btn.count() > 0 and close_btn.first.is_visible():
                                yt_done = True
                                self.logger.info("🎉 YouTube 동영상 게시 완료 확인 (완료 창 노출)!")
                                break

                        if yt_done:
                            # 백그라운드 전송 유실 방지를 위한 파일 크기 비례 안전 대기
                            self.logger.info(f"업로드 세션 안전 동기화 중 ({sync_buffer}초간 넉넉하게 대기)...")
                            page.wait_for_timeout(sync_buffer * 1000)
                            self.logger.info("🎉 YouTube 최종 업로드 성공 완료!")
                            browser.close()
                            return True
                        else:
                            self.logger.warning("YouTube 서버 처리 완료 확인을 받지 못했습니다.")
                            page.wait_for_timeout(5000)
                            browser.close()
                            return False

                self.logger.error("YouTube 업로드 input을 찾지 못했습니다.")
                page.wait_for_timeout(5000)
                browser.close()
                return False



        except Exception as e:
            self.logger.error(f"Playwright YouTube 업로드 실패: {e}")
            return False

