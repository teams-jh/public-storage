import os
import time
from pathlib import Path
from platforms.base import BaseUploader
from config import CONFIG, SESSION_DIR, get_media_type

class TikTokUploader(BaseUploader):
    def __init__(self):
        super().__init__("TikTok")
        self.access_token = CONFIG.get("TIKTOK_ACCESS_TOKEN")

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        TikTok 미디어(동영상/포토) 업로드
        - TikTok Studio 웹 자동화 (Playwright) 기반
        """
        media_type = get_media_type(media_path)
        self.logger.info(f"TikTok 업로드 시작 ({media_type.upper()}): {media_path.name}")
        return self._upload_via_playwright(media_path, metadata)

    def _ensure_photo_tab(self, page) -> bool:
        """
        상단 [사진] 탭으로 확실하게 전환하는 다중 방어 로직
        """
        self.logger.info("상단 [사진] 탭 전환 시도 중...")
        
        # 1. JavaScript 직접 탐색 및 클릭 (DOM 이벤트 버블링)
        try:
            clicked = page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll("div, span, button, p, a, [role='tab']"));
                for (const el of elements) {
                    const text = el.textContent ? el.textContent.trim() : "";
                    if ((text === '사진' || text === 'Photo' || text === 'Photos') && el.children.length <= 1) {
                        el.click();
                        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                        if (el.parentElement) {
                            el.parentElement.click();
                        }
                        return true;
                    }
                }
                return false;
            }""")
            if clicked:
                page.wait_for_timeout(1500)
                self.logger.info("JavaScript 직접 클릭으로 [사진] 탭 전환 성공")
        except Exception as e:
            self.logger.warning(f"JS 탭 클릭 시도 중 예외 (무시): {e}")

        # 2. Playwright 다중 선택자 강제 클릭
        selectors = [
            "div[role='tab']:has-text('사진')",
            "div[role='tab']:has-text('Photo')",
            "div[role='tab']:has-text('Photos')",
            "div[class*='tab']:has-text('사진')",
            "div[class*='Tab']:has-text('사진')",
            "span:text-is('사진')",
            "button:text-is('사진')",
            "div:text-is('사진')",
            "text=사진",
            "text=Photo",
        ]
        for sel in selectors:
            try:
                tabs = page.locator(sel)
                if tabs.count() > 0:
                    for i in range(tabs.count()):
                        target = tabs.nth(i)
                        if target.is_visible():
                            target.scroll_into_view_if_needed()
                            target.click(force=True)
                            page.wait_for_timeout(1500)
                            self.logger.info(f"Playwright 선택자({sel})로 [사진] 탭 클릭 완료")
                            return True
            except Exception:
                pass

        return False

    def _upload_via_playwright(self, media_path: Path, metadata: dict) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_tiktok"
            user_data_dir.mkdir(exist_ok=True)

            caption = metadata.get("full_caption", "")
            media_type = get_media_type(media_path)
            self.logger.info("TikTok 업로드 브라우저를 실행합니다...")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                # 원치 않는 파일 다이얼로그가 열렸을 때 자동 취소
                page.on("filechooser", lambda fc: None)

                page.goto("https://www.tiktok.com/creator-center/upload?lang=ko-KR", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)

                # 로그인 확인 및 업로드 인풋 감지 대기 (최대 180초)
                self.logger.info("TikTok 업로드 페이지 로드 확인 중...")
                page.wait_for_timeout(3000)

                # 사진 업로드인 경우 상단 [사진] 탭 확실하게 전환
                if media_type != "video":
                    self._ensure_photo_tab(page)

                file_input = None
                for attempt in range(36):  # 5초씩 36회 = 180초 대기
                    # 1) 사진 모드일 경우 주기적으로 탭 전환 재확인
                    if media_type != "video" and attempt % 3 == 0:
                        self._ensure_photo_tab(page)

                    # 2) 메인 프레임 탐색
                    direct_inputs = page.locator("input[type='file']")
                    if direct_inputs.count() > 0:
                        file_input = direct_inputs.first
                        break
                    
                    # 3) iframe 내부 탐색
                    for frame in page.frames:
                        frame_inputs = frame.locator("input[type='file']")
                        if frame_inputs.count() > 0:
                            file_input = frame_inputs.first
                            break
                    if file_input:
                        break

                    # 로그인 필요 안내
                    if attempt == 0 or attempt % 6 == 0:
                        if "login" in page.url:
                            self.logger.info("TikTok 로그인이 필요합니다. 브라우저에서 Google 계정 등으로 로그인해 주세요 (대기 중)...")
                        else:
                            self.logger.info("업로드 준비 중... 로그인 또는 페이지 로딩 대기 중입니다.")
                    page.wait_for_timeout(5000)

                if not file_input:
                    self.logger.warning("업로드 파일 선택 영역을 찾지 못했습니다. 브라우저 창에서 로그인을 확인해 주세요.")
                    page.wait_for_timeout(10000)
                    browser.close()
                    return False

                # 파일 첨부 전 최종 [사진] 탭 확인
                if media_type != "video":
                    self._ensure_photo_tab(page)
                    page.wait_for_timeout(1000)

                self.logger.info(f"파일 업로드 인풋 발견! {media_type.upper()} 업로드를 시작합니다...")
                file_input.set_input_files(str(media_path.resolve()))
                
                # 오류 방어: '지원하지 않은 파일 형식' 토스트 발생 시 자동 복구
                page.wait_for_timeout(2000)
                err_toast = page.locator("text='지원하지 않은 파일 형식', text='지원하지 않는', text='Unsupported'")
                if err_toast.count() > 0 and err_toast.first.is_visible():
                    self.logger.warning("⚠️ 파일 형식 오류 감지! [사진] 탭 강제 전환 후 재첨부를 시도합니다...")
                    self._ensure_photo_tab(page)
                    page.wait_for_timeout(2000)
                    retry_inputs = page.locator("input[type='file']")
                    if retry_inputs.count() > 0:
                        retry_inputs.first.set_input_files(str(media_path.resolve()))
                        self.logger.info("사진 파일 재첨부 완료!")

                # 영상/사진 업로드 완료 상태 대기 (최대 60초)
                self.logger.info("미디어 파일 업로드 및 서버 처리 대기 중...")
                for _ in range(12):
                    page.wait_for_timeout(3000)
                    # 1) 사진 모드 URL 전환 감지 또는 업로드 완료 텍스트 확인
                    is_photo_loaded = (
                        "photo" in page.url
                        or page.locator("text='사진 1장이 업로드되었습니다', text='업로드됨', text='Uploaded', text='눈에 띄는 제목 추가'").count() > 0
                    )
                    if is_photo_loaded:
                        self.logger.info("미디어 파일 업로드 완료 확인!")
                        break

                # 캡션 및 제목 입력
                title = metadata.get("title", "")
                content = metadata.get("content", "")
                tags = metadata.get("tags", "")
                full_caption = metadata.get("full_caption", "")
                desc_text = f"{content}\n\n{tags}".strip() if (content or tags) else full_caption

                self.logger.info("제목 및 설명 입력 중...")
                page.wait_for_timeout(1000)

                # 1) 사진 모드용 제목(Title) 입력칸 탐색
                title_inputs = page.locator("input[placeholder*='제목'], input[placeholder*='title']")
                if title_inputs.count() > 0 and title:
                    try:
                        title_inputs.first.fill(title[:90])  # 틱톡 제목 90자 제한
                        page.wait_for_timeout(500)
                        self.logger.info(f"제목 입력 완료: {title[:30]}...")
                    except Exception as e:
                        self.logger.warning(f"제목 입력 오류 (무시): {e}")

                # 2) 설명/본문 입력창 탐색
                caption_boxes = page.locator("div.public-DraftEditor-content, div[contenteditable='true'], div[role='combobox'], textarea")
                if caption_boxes.count() == 0:
                    for frame in page.frames:
                        frame_caption = frame.locator("div.public-DraftEditor-content, div[contenteditable='true'], div[role='combobox'], textarea")
                        if frame_caption.count() > 0:
                            caption_boxes = frame_caption
                            break

                if caption_boxes.count() > 0:
                    # 제목 입력칸과 구분하기 위해 가장 마지막 또는 설명 칸 선택
                    target_box = caption_boxes.last if caption_boxes.count() > 1 else caption_boxes.first
                    try:
                        target_box.fill(desc_text or full_caption)
                        page.wait_for_timeout(1500)
                        self.logger.info("설명 입력 완료!")
                    except Exception as e:
                        self.logger.warning(f"설명 입력 오류: {e}")

                # 페이지 맨 아래로 스크롤하여 [게시] 버튼 노출
                self.logger.info("페이지 하단으로 스크롤하여 [게시] 버튼을 탐색합니다...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                for frame in page.frames:
                    try:
                        frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    except Exception:
                        pass
                page.wait_for_timeout(2000)



                # 게시(Post) 버튼 정확히 찾기
                post_btn = None
                # 후보 선택자 목록 (우선순위 순)
                selectors = [
                    "div[class*='btn-post'] button",
                    "div[class*='button-group'] button:has-text('게시')",
                    "button[class*='primary']:has-text('게시')",
                    "button[class*='TuxButton--primary']",
                    "button:text-is('게시')",
                    "button:text-is('Post')",
                    "button:has-text('게시')",
                    "button:has-text('Post')",
                ]

                for sel in selectors:
                    btns = page.locator(sel)
                    if btns.count() > 0:
                        # 여러 개 중 맨 마지막(보통 폼 맨 하단) 버튼 선택
                        target = btns.last
                        try:
                            if target.is_visible():
                                post_btn = target
                                break
                        except Exception:
                            pass
                    # iframe 내부도 확인
                    if not post_btn:
                        for frame in page.frames:
                            frame_btns = frame.locator(sel)
                            if frame_btns.count() > 0:
                                target = frame_btns.last
                                try:
                                    if target.is_visible():
                                        post_btn = target
                                        break
                                except Exception:
                                    pass
                    if post_btn:
                        break

                if post_btn:
                    # 버튼이 화면에 보이도록 스크롤 및 활성화 대기
                    post_btn.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)

                    # 비활성화 상태가 풀릴 때까지 최대 15초 대기
                    for _ in range(15):
                        try:
                            if post_btn.is_enabled():
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)

                    self.logger.info("하단 [게시] 버튼 클릭 시도...")
                    post_btn.click()
                    self.logger.info("게시 버튼을 클릭했습니다. 서버 게시 완료 대기 (15초)...")

                    # 게시 완료 상태 확인 대기 (모달 또는 완료 텍스트 감지)
                    for _ in range(15):
                        page.wait_for_timeout(1000)
                        # 혹시 '끝낼까요?' 모달이 떴다면 '취소' 클릭
                        cancel_modal = page.locator("div[role='dialog'] button:text-is('취소'), button:text-is('취소')")
                        if cancel_modal.count() > 0 and cancel_modal.first.is_visible():
                            # 모달 취소 누르고 재시도 방지
                            pass

                        # 완료 확인 텍스트 탐색
                        success_indicators = page.locator(
                            "div:has-text('게시되었습니다'), div:has-text('업로드 완료'), "
                            "div:has-text('동영상이 게시되었습니다'), button:has-text('다른 동영상 업로드'), "
                            "button:has-text('게시물 관리'), a:has-text('게시물 관리')"
                        )
                        if success_indicators.count() > 0:
                            self.logger.info("🎉 TikTok 게시 완료 확인!")
                            break

                    page.wait_for_timeout(5000)
                    self.logger.info("TikTok 업로드 성공 완료!")
                    browser.close()
                    return True

                self.logger.warning("게시 버튼을 자동으로 클릭하지 못했습니다. 수동으로 확인 후 브라우저를 닫아주세요.")
                page.wait_for_timeout(15000)
                browser.close()
                return True
        except Exception as e:
            self.logger.error(f"Playwright TikTok 업로드 실패: {e}")
            return False



