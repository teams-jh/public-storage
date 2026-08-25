import os
import time
from pathlib import Path
from platforms.base import BaseUploader
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

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
            size_mb = get_media_size_mb(media_path)
            upload_timeout = get_dynamic_upload_timeout(media_path)
            sync_buffer = get_dynamic_sync_buffer(media_path)

            self.logger.info(f"X(Twitter) 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 세션 유지: {sync_buffer}초)")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.on("filechooser", lambda fc: None)

                page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                # 로그인 확인 및 대기 루프 (최대 180초)
                self.logger.info("X(Twitter) 로그인 상태 확인 중...")
                logged_in = False
                for attempt in range(36):  # 5초 * 36 = 180초
                    # 로그인 완료 지표 확인 (트윗 입력창, 새 트윗 버튼, 사이드바 링크, 계정 스위처 등)
                    login_indicators = page.locator(
                        "div[data-testid='tweetTextarea_0'], "
                        "a[data-testid='SideNav_NewTweet_Button'], "
                        "button[data-testid='SideNav_AccountSwitcher_Button'], "
                        "a[data-testid='AppTabBar_Home_Link'], "
                        "nav[aria-label='기본 타임라인'], "
                        "nav[aria-label='Primary Timeline']"
                    )
                    if login_indicators.count() > 0:
                        logged_in = True
                        self.logger.info("X(Twitter) 로그인 확인 완료!")
                        break

                    # 로그인 안내 메시지
                    if attempt == 0 or attempt % 6 == 0:
                        self.logger.info("X(Twitter) 로그인이 필요합니다. 브라우저에서 Google 계정 또는 아이디로 로그인해 주세요 (대기 중)...")
                        # 비로그인 첫 화면에서 로그인 버튼이 보이면 클릭 보조
                        login_btn = page.locator("a[href='/login'], a[data-testid='loginButton'], span:text-is('로그인'), span:text-is('Log in')")
                        if login_btn.count() > 0 and "login" not in page.url:
                            try:
                                login_btn.first.click()
                            except Exception:
                                pass

                    page.wait_for_timeout(5000)

                if not logged_in:
                    self.logger.error("X(Twitter) 로그인 대기 시간이 초과되었습니다.")
                    page.wait_for_timeout(5000)
                    browser.close()
                    return False

                self.logger.info("트윗 작성 시작...")
                page.wait_for_timeout(2000)

                # 1. 새 트윗 작성 모달 열기 (사이드바 버튼 클릭)
                new_tweet_btn = page.locator("a[data-testid='SideNav_NewTweet_Button'], a[href='/compose/post']")
                if new_tweet_btn.count() > 0:
                    try:
                        new_tweet_btn.first.click()
                        page.wait_for_timeout(1500)
                        self.logger.info("새 트윗 작성 창 열림")
                    except Exception:
                        pass

                # 2. 트윗 텍스트 입력창 찾기
                textbox = page.locator("div[role='dialog'] div[data-testid='tweetTextarea_0'], div[data-testid='tweetTextarea_0'], div[role='textbox']")
                if textbox.count() > 0:
                    try:
                        target_box = textbox.first
                        target_box.click()
                        page.wait_for_timeout(300)
                        # 키보드 직접 타이핑 및 입력
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        page.keyboard.insert_text(caption)
                        page.wait_for_timeout(1000)
                        self.logger.info("트윗 내용 작성 완료!")
                    except Exception as e:
                        self.logger.warning(f"텍스트 입력 실패: {e}")

                # 3. 미디어 파일 업로드 (file input)
                file_input = page.locator("div[role='dialog'] input[data-testid='fileInput'], input[data-testid='fileInput'], input[type='file']")
                if file_input.count() > 0:
                    self.logger.info(f"{media_type.upper()} 파일 첨부 중...")
                    file_input.first.set_input_files(str(media_path.resolve()))
                    
                    # 미디어 처리 및 프리뷰 렌더링 대기 (대용량 동영상 고려: 최대 upload_timeout초)
                    self.logger.info(f"미디어 파일 처리 및 렌더링 대기 중 (최대 {upload_timeout}초)...")
                    for _ in range(upload_timeout // 2):
                        page.wait_for_timeout(2000)
                        has_attachment = page.locator(
                            "div[data-testid='attachments'], "
                            "div[aria-label*='제거'], "
                            "div[aria-label*='Remove'], "
                            "div[data-testid='media']"
                        ).count() > 0
                        if has_attachment:
                            self.logger.info("미디어 첨부 완료 확인!")
                            break

                # 4. AI 생성 콘텐츠 안내 툴팁 방어 및 게시 버튼 클릭
                page.wait_for_timeout(1000)
                # AI generated content detected 툴팁 감지 및 해제
                ai_tooltips = page.locator(
                    "text='AI generated content detected', "
                    "text='AI generated', "
                    "div:has-text('AI generated content detected')"
                )
                if ai_tooltips.count() > 0:
                    self.logger.info("AI 생성 콘텐츠 안내 툴팁 감지 - 닫기 시도 중...")
                    try:
                        ai_tooltips.first.click()
                        page.wait_for_timeout(500)
                    except Exception:
                        pass

                post_btn = page.locator(
                    "div[role='dialog'] button[data-testid='tweetButton'], "
                    "button[data-testid='tweetButton'], "
                    "button[data-testid='tweetButtonInline'], "
                    "div[data-testid='tweetButtonInline'], "
                    "div[data-testid='tweetButton'], "
                    "button:has-text('Post'), "
                    "button:has-text('게시하기')"
                )

                if post_btn.count() > 0:
                    target_btn = post_btn.first
                    # 비활성화 해제 대기 (최대 30초)
                    for _ in range(30):
                        try:
                            aria_disabled = target_btn.get_attribute("aria-disabled")
                            if target_btn.is_enabled() and aria_disabled != "true":
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)

                    self.logger.info("하단 게시하기(Post) 실행 중...")
                    
                    # 1) Playwright 강제 클릭
                    try:
                        target_btn.click(force=True)
                    except Exception:
                        pass

                    # 2) JavaScript DOM 직접 클릭 이벤트 디스패치
                    try:
                        page.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll("button, div[role='button']"));
                            for (const btn of btns) {
                                const text = btn.textContent ? btn.textContent.trim() : "";
                                const testId = btn.getAttribute("data-testid") || "";
                                if (testId === "tweetButton" || testId === "tweetButtonInline" || text === "Post" || text === "게시하기") {
                                    btn.click();
                                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                    return true;
                                }
                            }
                            return false;
                        }""")
                    except Exception:
                        pass

                    # 3) X(Twitter) 전송 단축키 (Control+Enter) 입력
                    try:
                        page.keyboard.press("Control+Enter")
                    except Exception:
                        pass

                    self.logger.info(f"게시 요청 전송 완료. 서버 처리 및 완료 대기 중 (최대 {upload_timeout}초)...")
                    
                    # 완료 대기 (모달 닫힘 또는 토스트 메시지 감지, 최대 upload_timeout초)
                    tweet_sent = False
                    for _ in range(upload_timeout):
                        page.wait_for_timeout(1000)
                        toast = page.locator("div[data-testid='toast']")
                        if toast.count() > 0 and toast.first.is_visible():
                            self.logger.info("🎉 X(Twitter) 게시 토스트 확인!")
                            tweet_sent = True
                            break
                        
                        # 모달 닫힘 감지
                        dialog = page.locator("div[role='dialog']")
                        if dialog.count() == 0:
                            tweet_sent = True
                            self.logger.info("🎉 X(Twitter) 작성 모달 닫힘 확인!")
                            break

                    if tweet_sent:
                        self.logger.info(f"업로드 세션 안전 동기화 중 ({sync_buffer}초간 넉넉하게 대기)...")
                        page.wait_for_timeout(sync_buffer * 1000)
                        self.logger.info("🎉 X(Twitter) 업로드 최종 성공 완료!")
                        browser.close()
                        return True
                    else:
                        self.logger.warning("X(Twitter) 서버 완료 상태를 감지하지 못했습니다.")
                        page.wait_for_timeout(5000)
                        browser.close()
                        return False

                self.logger.error("X(Twitter) 게시하기 버튼을 찾을 수 없습니다.")
                page.wait_for_timeout(5000)
                browser.close()
                return False



        except Exception as e:
            self.logger.error(f"Playwright X(Twitter) 업로드 실패: {e}")
            return False


