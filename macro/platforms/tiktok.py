import os
import time
from pathlib import Path
from platforms.base import BaseUploader
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

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
        self.logger.info("상단 [사진] 탭 전환 확인 중...")
        
        # 1. 이미 사진 탭이 활성화되어 있는지 확인
        try:
            is_active = page.evaluate("""() => {
                const inputs = Array.from(document.querySelectorAll("input[type='file']"));
                for (const inp of inputs) {
                    if (inp.accept && inp.accept.includes("image")) return true;
                }
                return false;
            }""")
            if is_active:
                self.logger.info("이미 [사진] 탭이 활성화되어 있습니다.")
                return True
        except Exception:
            pass

        # 2. JavaScript DOM 탐색 및 강제 클릭
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
                self.logger.info("JavaScript DOM 이벤트로 [사진] 탭 클릭 성공")
        except Exception as e:
            self.logger.warning(f"JS 탭 클릭 예외: {e}")

        # 3. Playwright 다중 선택자 강제 클릭
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
                            self.logger.info(f"선택자({sel})로 [사진] 탭 클릭 완료")
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
            size_mb = get_media_size_mb(media_path)
            upload_timeout = get_dynamic_upload_timeout(media_path)
            sync_buffer = get_dynamic_sync_buffer(media_path)

            self.logger.info(f"TikTok 업로드 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 세션 유지: {sync_buffer}초)")
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

                # 사진 업로드인 경우 상단 [사진] 탭 전환
                if media_type != "video":
                    self._ensure_photo_tab(page)

                file_input = None
                for attempt in range(36):  # 5초씩 36회 = 180초 대기
                    # 1) 사진 모드일 경우 주기적으로 탭 전환 재확인
                    if media_type != "video" and attempt % 3 == 0:
                        self._ensure_photo_tab(page)

                    # 2) 사진 모드 전용 input 우선 탐색
                    if media_type != "video":
                        photo_inputs = page.locator("input[type='file'][accept*='image'], input[type='file']")
                        if photo_inputs.count() > 0:
                            file_input = photo_inputs.first
                            break
                    else:
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

                # 영상/사진 업로드 완료 및 세부정보 화면 전환 대기 (최대 upload_timeout초)
                self.logger.info(f"미디어 파일 업로드 및 세부정보 화면 진입 대기 중 (최대 {upload_timeout}초)...")
                for _ in range(upload_timeout // 2):
                    page.wait_for_timeout(2000)
                    is_loaded = (
                        "photo" in page.url
                        or page.locator("text='사진 1장이 업로드되었습니다', text='업로드됨', text='Uploaded', text='눈에 띄는 제목 추가'").count() > 0
                        or page.locator("input[placeholder*='제목'], div[contenteditable='true']").count() > 0
                    )
                    if is_loaded:
                        self.logger.info("미디어 파일 업로드 완료 및 세부정보 화면 진입 확인!")
                        break

                # 캡션 및 제목 데이터 준비
                title = metadata.get("title", "")
                content = metadata.get("content", "")
                tags = metadata.get("tags", "")
                full_caption = metadata.get("full_caption", "")

                self.logger.info("제목 및 설명(본문) 입력 시작...")
                page.wait_for_timeout(1500)

                # 1) 사진 모드일 경우: 상단 [제목] 필드 + 하단 [설명] 필드 분리 입력
                if media_type != "video":
                    title_inputs = page.locator("input[placeholder*='제목'], input[placeholder*='title'], input[placeholder*='눈에 띄는 제목']")
                    if title_inputs.count() > 0 and title:
                        try:
                            title_inputs.first.click()
                            page.wait_for_timeout(300)
                            title_inputs.first.fill(title[:90])
                            self.logger.info(f"사진 제목 입력 완료: {title[:30]}...")
                        except Exception:
                            pass
                    
                    base_desc = content.strip() if content else ""
                else:
                    # 동영상 모드일 경우: 본문(제목 + 내용)
                    body_parts = []
                    if title:
                        body_parts.append(title)
                    if content:
                        body_parts.append(content)
                    base_desc = "\n\n".join(body_parts).strip()

                # 2) 설명/본문(Description) 필드 입력 (DraftJS 에디터)
                caption_candidates = page.locator(
                    "div.public-DraftEditor-content, div[contenteditable='true'], div[role='combobox'], textarea"
                )
                if caption_candidates.count() == 0:
                    for frame in page.frames:
                        frame_cands = frame.locator(
                            "div.public-DraftEditor-content, div[contenteditable='true'], div[role='combobox'], textarea"
                        )
                        if frame_cands.count() > 0:
                            caption_candidates = frame_cands
                            break

                if caption_candidates.count() > 0:
                    target_box = caption_candidates.first
                    try:
                        target_box.click()
                        page.wait_for_timeout(500)
                        # 기존 텍스트 완전 삭제
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        page.wait_for_timeout(300)

                        # 본문 먼저 입력 후 콘텐츠 아래로 엔터(개행) 입력
                        if base_desc:
                            page.keyboard.insert_text(base_desc)
                            page.wait_for_timeout(500)
                            # 콘텐츠 아래에 확실하게 엔터(Enter) 입력
                            self.logger.info("콘텐츠 아래로 엔터(Enter) 개행 입력...")
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(200)
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(300)

                        # 헬퍼: 커서를 contenteditable 에디터 맨 끝으로 강제 이동
                        def move_cursor_to_end():
                            try:
                                page.evaluate("""() => {
                                    const editor = document.querySelector("div.public-DraftEditor-content") || document.querySelector("div[contenteditable='true']");
                                    if (editor) {
                                        editor.focus();
                                        const range = document.createRange();
                                        range.selectNodeContents(editor);
                                        range.collapse(false);
                                        const sel = window.getSelection();
                                        sel.removeAllRanges();
                                        sel.addRange(range);
                                    }
                                }""")
                            except Exception:
                                pass
                            page.wait_for_timeout(300)

                        # 해시태그 순차 입력 시퀀스
                        if tags:
                            tag_list = [t.strip().lstrip("#") for t in tags.split() if t.strip()]
                            for idx, t in enumerate(tag_list):
                                if not t:
                                    continue
                                
                                # 매 태그 입력 전 커서를 무조건 에디터 맨 끝으로 이동
                                move_cursor_to_end()
                                page.keyboard.insert_text(" ")
                                page.wait_for_timeout(200)

                                # 1) #[해시할태그] 입력
                                self.logger.info(f"1) TikTok 해시태그 입력 ({idx + 1}/{len(tag_list)}): #{t}")
                                page.keyboard.type(f"#{t}", delay=70)

                                # 2) 3초 뒤에 Tab 키 전송
                                self.logger.info("2) 3초 대기 후 Tab 키 전송...")
                                page.wait_for_timeout(3000)
                                page.keyboard.press("Tab")

                                # 3) 1초 뒤에 아래 버튼 전송
                                self.logger.info("3) 1초 대기 후 아래(ArrowDown) 버튼 전송...")
                                page.wait_for_timeout(1000)
                                page.keyboard.press("ArrowDown")

                                # 4) 1초 뒤에 위 버튼 전송
                                self.logger.info("4) 1초 대기 후 위(ArrowUp) 버튼 전송...")
                                page.wait_for_timeout(1000)
                                page.keyboard.press("ArrowUp")

                                # 5) 1초 뒤에 엔터 버튼 전송
                                self.logger.info("5) 1초 대기 후 엔터(Enter) 버튼 전송...")
                                page.wait_for_timeout(1000)
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(1000)

                                # 엔터 선택 후에도 커서를 에디터 맨 끝으로 즉시 고정
                                move_cursor_to_end()

                        self.logger.info("🎉 TikTok 본문 및 해시태그 입력 시퀀스 완료!")


                    except Exception as e:
                        self.logger.warning(f"키보드 텍스트 입력 실패, fill 재시도: {e}")
                        try:
                            target_box.fill(f"{base_desc}\n\n{tags}".strip())
                        except Exception:
                            pass





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
                        target = btns.last
                        try:
                            if target.is_visible():
                                post_btn = target
                                break
                        except Exception:
                            pass
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
                    post_btn.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)

                    # 비활성화 상태가 풀릴 때까지 대기
                    for _ in range(30):
                        try:
                            if post_btn.is_enabled():
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)

                    self.logger.info("하단 [게시] 버튼 클릭 시도...")
                    post_btn.click(force=True)
                    self.logger.info(f"게시 버튼을 클릭했습니다. 서버 처리 및 완료 대기 중 (최대 {upload_timeout}초)...")

                    # 게시 완료 상태 확인 대기 (최대 upload_timeout초)
                    post_completed = False
                    for _ in range(upload_timeout):
                        page.wait_for_timeout(1000)

                        # 1) '계속 게시할까요?' / '잠재적 문제에 대한 검사' 팝업 감지 시 [지금 게시] 자동 클릭
                        try:
                            handled_popup = page.evaluate("""() => {
                                const dialogs = Array.from(document.querySelectorAll("div[role='dialog'], div[class*='modal'], div[class*='popup'], div[class*='TuxModal']"));
                                for (const d of dialogs) {
                                    const text = d.textContent || "";
                                    if (text.includes("계속 게시") || text.includes("검사") || text.includes("Post anyway") || text.includes("Continue posting")) {
                                        const btns = Array.from(d.querySelectorAll("button"));
                                        for (const b of btns) {
                                            const btnText = b.textContent ? b.textContent.trim() : "";
                                            if (btnText.includes("지금 게시") || btnText.includes("Post now") || btnText.includes("Post anyway") || btnText === "게시") {
                                                b.click();
                                                b.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                                return true;
                                            }
                                        }
                                    }
                                }
                                return false;
                            }""")
                            if handled_popup:
                                self.logger.info("⚠️ TikTok '계속 게시할까요?' 확인 팝업 감지 -> [지금 게시] 버튼 자동 클릭 완료!")
                                page.wait_for_timeout(1000)
                        except Exception:
                            pass

                        # Playwright 선택자로도 [지금 게시] 보조 클릭
                        post_now_btn = page.locator(
                            "button:text-is('지금 게시'), "
                            "button:has-text('지금 게시'), "
                            "div[role='dialog'] button:has-text('지금 게시'), "
                            "div[role='dialog'] button:has-text('Post now'), "
                            "div[role='dialog'] button:has-text('Post anyway')"
                        )
                        if post_now_btn.count() > 0 and post_now_btn.first.is_visible():
                            try:
                                self.logger.info("⚠️ [지금 게시] 팝업 버튼 선택자 감지 -> 클릭!")
                                post_now_btn.first.click(force=True)
                                page.wait_for_timeout(1000)
                            except Exception:
                                pass

                        # 2) 완료 확인 텍스트 탐색
                        success_indicators = page.locator(
                            "div:has-text('게시되었습니다'), div:has-text('업로드 완료'), "
                            "div:has-text('동영상이 게시되었습니다'), button:has-text('다른 동영상 업로드'), "
                            "button:has-text('게시물 관리'), a:has-text('게시물 관리')"
                        )
                        if success_indicators.count() > 0 and success_indicators.first.is_visible():
                            self.logger.info("🎉 TikTok 게시 완료 확인!")
                            post_completed = True
                            break

                    if post_completed:
                        self.logger.info(f"업로드 세션 안전 동기화 중 ({sync_buffer}초간 넉넉하게 대기)...")
                        page.wait_for_timeout(sync_buffer * 1000)
                        self.logger.info("🎉 TikTok 최종 업로드 성공 완료!")
                        browser.close()
                        return True
                    else:
                        self.logger.warning("TikTok 서버 전송 완료 확인을 받지 못했습니다.")
                        page.wait_for_timeout(5000)
                        browser.close()
                        return False


                self.logger.error("게시 버튼을 찾지 못했습니다.")
                page.wait_for_timeout(5000)
                browser.close()
                return False

        except Exception as e:
            self.logger.error(f"Playwright TikTok 업로드 실패: {e}")
            return False





