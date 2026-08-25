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
        Facebook 페이지 또는 프로필에 미디어(동영상/사진/GIF) 업로드 (현재 비활성화됨)
        """
        self.logger.info("Facebook 업로드 기능은 현재 비활성화되어 있습니다 (스킵).")
        return True

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
                
                # 1. 작성 모달(dialog)이 열려있지 않은 경우에만 클릭
                dialog = page.locator("div[role='dialog']")
                if dialog.count() == 0:
                    create_box = page.locator(
                        "div[role='button']:has-text('무슨 생각을 하고 계신가요?'), "
                        "div[role='button']:has-text(\"What's on your mind?\"), "
                        "span:has-text('무슨 생각을 하고 계신가요?'), "
                        "span:has-text(\"What's on your mind?\")"
                    )
                    if create_box.count() > 0:
                        create_box.first.click()
                        page.wait_for_timeout(2000)

                # 2. 텍스트(본문/설명) 먼저 모달에 입력
                self.logger.info("모달 내부 본문 텍스트 입력 중...")
                textbox = page.locator(
                    "div[role='dialog'] div[role='textbox'], "
                    "div[role='dialog'] div[contenteditable='true'], "
                    "div[role='dialog'] div[aria-label*='무슨 생각을 하고 계신가요'], "
                    "div[role='dialog'] div[aria-label*=\"What's on your mind\"]"
                )
                if textbox.count() > 0:
                    try:
                        target_box = textbox.first
                        target_box.click()
                        page.wait_for_timeout(300)
                        page.keyboard.insert_text(caption)
                        page.wait_for_timeout(1000)
                        self.logger.info("Facebook 텍스트 입력 완료!")
                    except Exception as e:
                        self.logger.warning(f"키보드 텍스트 입력 실패: {e}")
                        try:
                            textbox.first.fill(caption)
                        except Exception:
                            pass

                # 3. '게시물에 추가' 영역의 초록색 [사진/동영상] 아이콘 확실하게 클릭하여 파일 인풋 생성
                self.logger.info("모달 내부 초록색 [사진/동영상] 아이콘 클릭 시도...")
                page.wait_for_timeout(1000)

                # 1) JavaScript로 '게시물에 추가' 옆 초록색 사진 아이콘 정밀 클릭
                try:
                    page.evaluate("""() => {
                        const dialog = document.querySelector("div[role='dialog']");
                        if (!dialog) return false;
                        
                        // 1-1) aria-label 매칭
                        const elements = Array.from(dialog.querySelectorAll("div[role='button'], [aria-label], div[tabindex='0']"));
                        for (const el of elements) {
                            const label = el.getAttribute("aria-label") || "";
                            if (label.includes("사진/동영상") || label.includes("Photo/video") || label.includes("사진") || label.includes("Photo")) {
                                el.click();
                                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                return true;
                            }
                        }

                        // 1-2) '게시물에 추가' 텍스트 컨테이너 내 첫 번째 아이콘 클릭
                        const allDivs = Array.from(dialog.querySelectorAll("div, span"));
                        for (const d of allDivs) {
                            if (d.textContent && (d.textContent.trim() === "게시물에 추가" || d.textContent.trim() === "Add to your post")) {
                                const parent = d.closest("div[class*='']");
                                if (parent) {
                                    const iconBtns = parent.querySelectorAll("div[role='button'], div[tabindex='0']");
                                    if (iconBtns.length > 0) {
                                        iconBtns[0].click();
                                        iconBtns[0].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                        return true;
                                    }
                                }
                            }
                        }
                        return false;
                    }""")
                except Exception as e:
                    self.logger.warning(f"JS 사진 아이콘 클릭 예외: {e}")

                # 2) Playwright 선택자로도 사진 아이콘 클릭 보조
                photo_triggers = page.locator(
                    "div[role='dialog'] div[aria-label*='사진/동영상'], "
                    "div[role='dialog'] div[aria-label*='Photo/video'], "
                    "div[role='dialog'] div[aria-label*='사진'], "
                    "div[role='dialog'] div[aria-label*='Photo'], "
                    "div[role='dialog'] img[src*='photo'], "
                    "div[role='dialog'] svg"
                )
                if photo_triggers.count() > 0:
                    try:
                        photo_triggers.first.click(force=True)
                    except Exception:
                        pass

                page.wait_for_timeout(1500)

                # 4. 모달 내부에 생성된 input[type='file']에 미디어 파일 첨부
                self.logger.info(f"{media_type.upper()} 미디어 파일 첨부 중...")
                file_attached = False
                for _ in range(10):  # input 생성 대기 (최대 5초)
                    file_input = page.locator("div[role='dialog'] input[type='file'], input[type='file']")
                    if file_input.count() > 0:
                        file_input.first.set_input_files(str(media_path.resolve()))
                        file_attached = True
                        break
                    page.wait_for_timeout(500)

                if file_attached:
                    render_wait = max(5, int(size_mb * 1.5)) if media_type == "video" else 3
                    self.logger.info(f"{media_type.capitalize()} 렌더링 완료 대기 중 ({render_wait}초)...")
                    page.wait_for_timeout(render_wait * 1000)
                else:
                    self.logger.warning("파일 첨부 input을 찾지 못해 텍스트만 게시를 진행합니다.")

                # 5. 파란색 [게시] 버튼 단 1회 정확하게 클릭 (중복 시도 방지)
                self.logger.info("하단 파란색 [게시] 버튼 클릭...")
                page.wait_for_timeout(1500)


                # 활성화 상태 대기
                post_btn = page.locator(
                    "div[role='dialog'] div[aria-label='게시'], "
                    "div[role='dialog'] div[aria-label='Post'], "
                    "div[role='dialog'] div[role='button']:has-text('게시'), "
                    "div[role='dialog'] div[role='button']:has-text('Post')"
                )
                
                clicked_done = False
                if post_btn.count() > 0:
                    target_btn = post_btn.last
                    for _ in range(15):
                        try:
                            aria_disabled = target_btn.get_attribute("aria-disabled")
                            if target_btn.is_enabled() and aria_disabled != "true":
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(500)
                    try:
                        target_btn.click(force=True)
                        clicked_done = True
                    except Exception:
                        pass

                # Playwright 클릭이 안 먹혔을 경우에만 JS 좌표 클릭 실행
                if not clicked_done:
                    try:
                        page.evaluate("""() => {
                            const elements = Array.from(document.querySelectorAll("div[role='dialog'] div[role='button'], div[role='dialog'] div[aria-label*='게시'], div[role='dialog'] div[aria-label*='Post']"));
                            for (const el of elements) {
                                const text = el.innerText || el.textContent || "";
                                const aria = el.getAttribute("aria-label") || "";
                                if (text.trim() === '게시' || text.trim() === 'Post' || aria === '게시' || aria === 'Post') {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                    except Exception:
                        pass

                self.logger.info(f"게시 요청 전송 완료. 서버 처리 및 모달 닫힘 대기 중 (최대 {upload_timeout}초)...")
                
                # 게시 완료 상태 확인 (모달 닫힘 감지, 최대 upload_timeout초)
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




        except Exception as e:
            self.logger.error(f"Playwright Facebook 업로드 실패: {e}")
            return False
