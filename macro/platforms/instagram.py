import time
from pathlib import Path
from platforms.base import BaseUploader
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

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

            media_type = get_media_type(media_path)
            size_mb = get_media_size_mb(media_path)
            upload_timeout = get_dynamic_upload_timeout(media_path)
            sync_buffer = get_dynamic_sync_buffer(media_path)

            self.logger.info(f"Playwright 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 세션 유지: {sync_buffer}초)")
            with sync_playwright() as p:

                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,  # 첫 로그인/인증을 위해 브라우저 표시
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인 및 대기 루프 (최대 180초)
                self.logger.info("Instagram 로그인 상태 확인 중...")
                
                # .env에 계정 정보가 있다면 자동 입력 시도
                if self.username and self.password:
                    try:
                        user_field = page.locator("input[name='username']")
                        pass_field = page.locator("input[name='password']")
                        submit_btn = page.locator("button[type='submit']")
                        if user_field.count() > 0 and pass_field.count() > 0:
                            self.logger.info(".env의 계정 정보로 자동 입력을 진행합니다...")
                            user_field.first.fill(self.username)
                            page.wait_for_timeout(300)
                            pass_field.first.fill(self.password)
                            page.wait_for_timeout(500)
                            submit_btn.first.click()
                            page.wait_for_timeout(3000)
                    except Exception as e:
                        self.logger.warning(f"자동 로그인 입력 시도 중 예외 (무시): {e}")

                logged_in = False
                for attempt in range(36):  # 5초 * 36 = 180초
                    # '나중에 하기' / 'Not Now' 팝업 자동 클릭
                    try:
                        not_now = page.locator("button:has-text('나중에 하기'), button:has-text('Not Now'), button:has-text('나중에')")
                        if not_now.count() > 0 and not_now.first.is_visible():
                            not_now.first.click()
                            page.wait_for_timeout(1000)
                    except Exception:
                        pass

                    # 로그인 완료 지표 확인 (만들기 아이콘, 홈 아이콘, 프로필 등)
                    create_btn = page.locator(
                        "svg[aria-label='새로운 게시물'], "
                        "svg[aria-label='새 게시물'], "
                        "svg[aria-label='New post'], "
                        "svg[aria-label='만들기'], "
                        "svg[aria-label='Create'], "
                        "span:text-is('만들기'), "
                        "span:text-is('Create')"
                    )
                    if create_btn.count() > 0:
                        logged_in = True
                        self.logger.info("Instagram 로그인 확인 완료!")
                        break

                    if attempt == 0 or attempt % 6 == 0:
                        self.logger.info("Instagram 로그인이 필요합니다. 브라우저에서 로그인(또는 2FA 인증)을 완료해 주세요 (대기 중)...")

                    page.wait_for_timeout(5000)

                if not logged_in:
                    self.logger.error("Instagram 로그인 대기 시간이 초과되었습니다.")
                    page.wait_for_timeout(5000)
                    browser.close()
                    return False

                # 팝업 및 이전 잔여 모달(친구 공유 모달 등) 자동 닫기 정리
                try:
                    not_now = page.locator("button:has-text('나중에 하기'), button:has-text('Not Now'), button:has-text('나중에')")
                    if not_now.count() > 0 and not_now.first.is_visible():
                        not_now.first.click()
                        page.wait_for_timeout(1000)

                    # 혹시 이전 '친구에게 공유' 팝업이 떠 있다면 닫기
                    stale_close = page.locator("div[role='dialog'] svg[aria-label='닫기'], div[role='dialog'] svg[aria-label='Close']")
                    if stale_close.count() > 0 and page.locator("input[placeholder*='검색']").count() > 0:
                        stale_close.first.click()
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                self.logger.info("만들기(+) 버튼 클릭 및 미디어 업로드 시도...")
                create_btn = page.locator(
                    "svg[aria-label='새로운 게시물'], "
                    "svg[aria-label='새 게시물'], "
                    "svg[aria-label='New post'], "
                    "svg[aria-label='만들기'], "
                    "svg[aria-label='Create'], "
                    "span:text-is('만들기'), "
                    "span:text-is('Create')"
                )
                if create_btn.count() > 0:
                    create_target = create_btn.first
                    try:
                        create_target.locator("..").click()
                    except Exception:
                        create_target.click(force=True)
                    page.wait_for_timeout(2000)

                    # 1. 파일 업로드 인풋 주입
                    file_input = page.locator("input[type='file']")
                    if file_input.count() > 0:
                        self.logger.info("미디어 파일 첨부 중...")
                        file_input.first.set_input_files(str(media_path.resolve()))
                        page.wait_for_timeout(3000)

                    # 2. [다음] 버튼들을 순차적으로 클릭하여 캡션(문구 입력) 단계까지 확실하게 전이
                    self.logger.info("자르기/필터 단계를 통과하여 캡션 입력창으로 이동합니다...")
                    caption_box = None
                    for step in range(8):
                        # 캡션창이 이미 나타났는지 확인
                        candidates = page.locator(
                            "div[aria-label*='문구'], "
                            "div[aria-label*='caption'], "
                            "div[aria-label*='Write'], "
                            "div[role='textbox']"
                        )
                        if candidates.count() > 0 and candidates.first.is_visible():
                            caption_box = candidates.first
                            self.logger.info("캡션(문구) 입력 화면 도달 확인!")
                            break

                        self.logger.info(f"[{step + 1}단계] '다음' 버튼 클릭 시도...")
                        # 1) JS DOM 이벤트 직접 전송
                        try:
                            page.evaluate("""() => {
                                const elements = Array.from(document.querySelectorAll("div[role='dialog'] div[role='button'], div[role='dialog'] button, div[role='dialog'] span"));
                                for (const el of elements) {
                                    const text = el.textContent ? el.textContent.trim() : "";
                                    if (text === '다음' || text === 'Next') {
                                        el.click();
                                        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                        except Exception:
                            pass

                        # 2) Playwright 선택자 강제 클릭
                        next_btns = page.locator(
                            "div[role='dialog'] div[role='button']:has-text('다음'), "
                            "div[role='dialog'] div[role='button']:has-text('Next'), "
                            "button:has-text('다음'), "
                            "button:has-text('Next')"
                        )
                        if next_btns.count() > 0:
                            try:
                                next_btns.first.click(force=True)
                            except Exception:
                                pass

                        page.wait_for_timeout(2000)

                    # 3. 캡션 입력
                    if not caption_box:
                        candidates = page.locator("div[aria-label*='문구'], div[aria-label*='caption'], div[role='textbox'], div[contenteditable='true']")
                        if candidates.count() > 0:
                            caption_box = candidates.first

                    if caption_box:
                        try:
                            caption_box.click()
                            page.wait_for_timeout(300)
                            page.keyboard.insert_text(caption)
                            page.wait_for_timeout(1000)
                            self.logger.info("캡션 내용 입력 완료!")
                        except Exception as e:
                            self.logger.warning(f"키보드 입력 실패, fill 시도: {e}")
                            try:
                                caption_box.fill(caption)
                            except Exception:
                                pass

                    # 4. [공유하기] 버튼 확실하게 클릭
                    self.logger.info("최종 [공유하기] 버튼 클릭 시도...")
                    page.wait_for_timeout(1500)
                    
                    for _ in range(3):
                        # 1) JS DOM 이벤트 직접 디스패치
                        try:
                            page.evaluate("""() => {
                                const elements = Array.from(document.querySelectorAll("div[role='dialog'] div[role='button'], div[role='dialog'] button, div[role='dialog'] span"));
                                for (const el of elements) {
                                    const text = el.textContent ? el.textContent.trim() : "";
                                    if (text === '공유하기' || text === 'Share') {
                                        el.click();
                                        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                        except Exception:
                            pass

                        # 2) Playwright 강제 클릭
                        share_btns = page.locator(
                            "div[role='dialog'] div[role='button']:has-text('공유하기'), "
                            "div[role='dialog'] div[role='button']:has-text('Share'), "
                            "button:has-text('공유하기'), "
                            "button:has-text('Share')"
                        )
                        if share_btns.count() > 0:
                            try:
                                share_btns.first.click(force=True)
                            except Exception:
                                pass
                        page.wait_for_timeout(1500)

                    # 5. 실제 업로드 완료 엄격 검증 (오직 업로드 모달 내부에서 확인)
                    upload_success = False
                    self.logger.info(f"모달 내부에서 실제 업로드 완료 화면을 대기합니다 (최대 {upload_timeout}초 = {upload_timeout // 60}분)...")
                    
                    for wait_i in range(upload_timeout):
                        page.wait_for_timeout(1000)
                        
                        # 업로드 모달(div[role='dialog']) 내부의 텍스트만 엄격하게 검사
                        is_completed = False
                        try:
                            is_completed = page.evaluate("""() => {
                                const dialogs = Array.from(document.querySelectorAll("div[role='dialog']"));
                                for (const dialog of dialogs) {
                                    const text = dialog.innerText || "";
                                    // 오직 모달 내부에서 완료 문구가 명확히 떴을 때만 감지
                                    if (
                                        text.includes("게시물이 공유되었습니다") ||
                                        text.includes("동영상이 공유되었습니다") ||
                                        text.includes("릴스가 공유되었습니다") ||
                                        text.includes("Your post has been shared") ||
                                        text.includes("Your reel has been shared") ||
                                        (text.includes("공유되었습니다") && !text.includes("공유하기"))
                                    ) {
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                        except Exception:
                            pass

                        if is_completed:
                            upload_success = True
                            self.logger.info("🎉 Instagram 모달 완료 화면 감지: 게시물이 성공적으로 공유되었습니다!")
                            break

                        # 만약 8초 / 20초가 지났는데도 아직 '공유하기' 상태에 멈춰있다면 재클릭
                        if wait_i == 8 or wait_i == 20:
                            self.logger.info("공유하기 버튼 재클릭 시도...")
                            try:
                                page.evaluate("""() => {
                                    const dialog = document.querySelector("div[role='dialog']");
                                    if (!dialog) return false;
                                    const elements = Array.from(dialog.querySelectorAll("div[role='button'], button, span"));
                                    for (const el of elements) {
                                        const text = el.textContent ? el.textContent.trim() : "";
                                        if (text === '공유하기' || text === 'Share') {
                                            el.click();
                                            el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                            return true;
                                        }
                                    }
                                    return false;
                                }""")
                            except Exception:
                                pass

                    if upload_success:
                        self.logger.info(f"업로드 세션 안전 동기화 중 ({sync_buffer}초간 넉넉하게 대기)...")
                        page.wait_for_timeout(sync_buffer * 1000)
                        self.logger.info("🎉 Instagram 업로드 최종 성공 완료!")
                        browser.close()
                        return True
                    else:
                        self.logger.error("Instagram 서버 전송 시간이 초과되었거나 완료 화면을 감지하지 못했습니다.")
                        page.wait_for_timeout(5000)
                        browser.close()
                        return False








                self.logger.error("Instagram 만들기 버튼 또는 업로드 단계를 진행하지 못했습니다.")
                page.wait_for_timeout(5000)
                browser.close()
                return False

        except Exception as e:
            self.logger.error(f"Playwright 인스타그램 업로드 실패: {e}")
            return False



