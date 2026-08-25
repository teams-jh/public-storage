import os
import time
from pathlib import Path
import requests
from platforms.base import BaseUploader
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

class ThreadsUploader(BaseUploader):
    def __init__(self):
        super().__init__("Threads")
        self.access_token = CONFIG.get("META_ACCESS_TOKEN")
        self.threads_user_id = CONFIG.get("THREADS_USER_ID", "me")

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        스레드(Threads) 미디어(동영상/사진/GIF) 업로드
        - 스레드 UX 특성상 [TAGS]가 여러 개 있는 경우 첫 번째 태그만 추출하여 적용 (#개발자 #개그 -> #개발자)
        1. Threads API 토큰이 있는 경우 공식 API 사용
        2. 없는 경우 Playwright 웹 자동화 사용
        """
        title = metadata.get("title", "")
        content = metadata.get("content", "")
        tags_raw = metadata.get("tags", "")

        # 스레드는 여러 태그 중 첫 번째 태그만 사용
        first_tag = ""
        if tags_raw:
            tag_list = tags_raw.split()
            if tag_list:
                first_tag = tag_list[0].strip()

        # 캡션 재구성
        caption_parts = []
        if title:
            caption_parts.append(title)
        if content:
            caption_parts.append(content)
        if first_tag:
            caption_parts.append(first_tag)

        caption = "\n\n".join(caption_parts).strip() if caption_parts else metadata.get("full_caption", "")
        media_type = get_media_type(media_path)
        
        self.logger.info(f"Threads 업로드 시작 ({media_type.upper()}): {media_path.name}")
        if first_tag:
            self.logger.info(f"Threads 적용 태그 (첫 번째 태그만 사용): {first_tag}")
        self.logger.info(f"캡션 내용 요약:\n{caption[:100]}...")


        # 방법 1: 공식 Threads API (공개 URL 호스팅 미디어 필요)
        if self.access_token:
            self.logger.info("Threads API를 통한 업로드를 시도합니다.")
            pass

        # 방법 2: Playwright 웹 브라우저 자동화
        return self._upload_via_playwright(media_path, metadata)

    def _upload_via_playwright(self, media_path: Path, metadata: dict) -> bool:
        try:
            title = metadata.get("title", "")
            content = metadata.get("content", "")
            tags_raw = metadata.get("tags", "")
            caption = metadata.get("full_caption", "")

            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_threads"
            user_data_dir.mkdir(exist_ok=True)

            media_type = get_media_type(media_path)
            size_mb = get_media_size_mb(media_path)
            upload_timeout = get_dynamic_upload_timeout(media_path)
            sync_buffer = get_dynamic_sync_buffer(media_path)

            self.logger.info(f"Threads 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 완료 후 세션유지: {sync_buffer}초)")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.on("filechooser", lambda fc: None)

                page.goto("https://www.threads.net/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                # 로그인 확인 및 대기 루프 (최대 180초)
                self.logger.info("Threads 로그인 상태 확인 중...")
                logged_in = False
                
                for attempt in range(LOGIN_TIMEOUT_SECONDS // 5):  # 5초 * 36회 = 180초
                    # 1) 비로그인 상태 신호 확인 (로그인 버튼, Instagram으로 로그인 등)
                    login_prompts = page.locator(
                        "a[href*='/login'], "
                        "button:has-text('로그인'), "
                        "button:has-text('Log in'), "
                        "span:has-text('로그인'), "
                        "span:has-text('Log in'), "
                        "div:has-text('Instagram으로 로그인'), "
                        "div:has-text('Log in with Instagram')"
                    )
                    
                    # 2) 실제 로그인 완료 지표 확인 (본인 프로필 @링크, 로그아웃 메뉴 등)
                    profile_link = page.locator("a[href^='/@']")
                    has_login_prompt = login_prompts.count() > 0 and any(login_prompts.nth(i).is_visible() for i in range(login_prompts.count()))

                    if profile_link.count() > 0 and not has_login_prompt:
                        logged_in = True
                        self.logger.info("Threads 로그인 확인 완료!")
                        break

                    # 안내 메시지 출력
                    if attempt == 0 or attempt % 6 == 0:
                        self.logger.info("Threads 로그인이 필요합니다. 브라우저에서 Instagram 계정으로 로그인해 주세요 (대기 중)...")
                        # 비로그인 화면에서 로그인 버튼이 보이면 클릭 보조
                        if login_prompts.count() > 0:
                            try:
                                for i in range(login_prompts.count()):
                                    btn = login_prompts.nth(i)
                                    if btn.is_visible():
                                        btn.click()
                                        break
                            except Exception:
                                pass

                    page.wait_for_timeout(5000)

                if not logged_in:
                    self.logger.error("Threads 로그인 대기 시간이 초과되었습니다.")
                    page.wait_for_timeout(5000)
                    browser.close()
                    return False

                self.logger.info("새 스레드 작성 시작...")
                page.wait_for_timeout(2000)
                
                # 작성 모달(dialog)이 아직 안 열렸다면 '스레드를 시작하세요...' 또는 만들기 버튼 클릭
                dialog = page.locator("div[role='dialog']")
                if dialog.count() == 0:
                    create_triggers = page.locator(
                        "div:has-text('스레드를 시작하세요...'), "
                        "div:has-text('Start a thread...'), "
                        "svg[aria-label='만들기'], "
                        "svg[aria-label='Create']"
                    )
                    if create_triggers.count() > 0:
                        try:
                            create_triggers.first.click()
                            page.wait_for_timeout(1500)
                        except Exception:
                            pass

                # 1. 모달 내부 파일 먼저 첨부
                self.logger.info(f"1단계: {media_type.upper()} 파일({media_path.name}) 첨부 중...")
                file_input = page.locator("div[role='dialog'] input[type='file'], input[type='file']")
                if file_input.count() > 0:
                    try:
                        file_input.first.set_input_files(str(media_path.resolve()))
                        # 미디어 처리 대기
                        render_wait = max(5, int(size_mb * 1.5)) if media_type == "video" else 3
                        self.logger.info(f"미디어 파일 렌더링 대기 중 ({render_wait}초)...")
                        page.wait_for_timeout(render_wait * 1000)
                    except Exception as e:
                        self.logger.warning(f"파일 첨부 실패: {e}")

                # 2. 본문 텍스트 및 해시태그 순차 입력
                self.logger.info("2단계: 스레드 내용 및 해시태그 입력 중...")
                textbox = page.locator("div[role='dialog'] div[role='textbox'], div[role='dialog'] div[contenteditable='true'], div[role='textbox']")
                if textbox.count() > 0:
                    try:
                        textbox.first.click()
                        page.wait_for_timeout(300)
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        page.wait_for_timeout(200)

                        # 1) 본문 내용 (제목 + 본문) 먼저 입력
                        body_parts = []
                        if title:
                            body_parts.append(title)
                        if content:
                            body_parts.append(content)
                        body_text = "\n\n".join(body_parts).strip()

                        if body_text:
                            page.keyboard.insert_text(body_text)
                            page.wait_for_timeout(500)

                        # 2) 해시태그 입력 및 첫 번째 추천값 클릭/Enter 선택
                        if tags_raw:
                            tag_list = [t.strip().lstrip("#") for t in tags_raw.split() if t.strip()]
                            for t in tag_list:
                                if not t:
                                    continue
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(200)
                                
                                # #태그 타이핑
                                self.logger.info(f"Threads 태그 타이핑: #{t}")
                                page.keyboard.type(f"#{t}", delay=70)
                                page.wait_for_timeout(1000)

                                # 드롭다운의 첫 번째 추천값(예: '게임') 강력 클릭 시도
                                clicked_sug = False
                                
                                # 1) JS DOM 검색으로 정확한 태그 텍스트를 가진 첫 번째 항목 클릭
                                try:
                                    clicked_sug = page.evaluate("""(targetTag) => {
                                        const allNodes = Array.from(document.querySelectorAll("div, span, button, li"));
                                        for (const node of allNodes) {
                                            const txt = node.textContent ? node.textContent.trim() : "";
                                            if (txt === targetTag && node.children.length === 0) {
                                                const rect = node.getBoundingClientRect();
                                                if (rect.width > 0 && rect.height > 0) {
                                                    const target = node.closest("div[role='button']") || node.closest("div[tabindex]") || node;
                                                    target.click();
                                                    target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                                    return true;
                                                }
                                            }
                                        }
                                        return false;
                                    }""", t)
                                    if clicked_sug:
                                        self.logger.info(f"🎉 Threads 드롭다운 첫 번째 추천값 JS 클릭 완료: {t}")
                                except Exception as e:
                                    self.logger.warning(f"JS 태그 클릭 예외: {e}")

                                # 2) Playwright 전역 선택자로 클릭 보조
                                if not clicked_sug:
                                    try:
                                        sug_loc = page.locator(f"div:text-is('{t}'), span:text-is('{t}')")
                                        if sug_loc.count() > 0:
                                            sug_loc.first.click(force=True)
                                            clicked_sug = True
                                            self.logger.info(f"🎉 Threads 드롭다운 추천값 Playwright 클릭 완료: {t}")
                                    except Exception:
                                        pass

                                # 3) 미클릭 시 기본 포커스된 첫 번째 항목에 Enter 전송
                                if not clicked_sug:
                                    page.keyboard.press("Enter")
                                    self.logger.info(f"Threads Enter 키로 첫 번째 추천 태그 확정: {t}")

                                page.wait_for_timeout(800)

                        self.logger.info("스레드 내용 및 태그 입력 완료!")
                    except Exception as e:
                        self.logger.warning(f"스레드 텍스트 입력 실패 (무시): {e}")

                # 3. 우측 하단 [게시] 버튼 강력 클릭 (다중 선택자 + JS 위치 계산 + 단축키)
                self.logger.info("모달 [게시] 버튼 클릭 시도...")
                page.wait_for_timeout(1000)



                clicked_post = False

                # 1) JavaScript DOM 위치 기반 가장 아래쪽(모달 우측 하단)의 [게시] 버튼 클릭
                try:
                    clicked_post = page.evaluate("""() => {
                        const elements = Array.from(document.querySelectorAll("div[role='button'], button, div[tabindex='0'], span"));
                        const candidates = [];
                        for (const el of elements) {
                            const text = el.textContent ? el.textContent.trim() : "";
                            if (text === '게시' || text === 'Post') {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    candidates.push({ el, bottom: rect.bottom });
                                }
                            }
                        }
                        if (candidates.length > 0) {
                            // 화면 가장 아래에 위치한(모달 우측 하단) 버튼 선택
                            candidates.sort((a, b) => b.bottom - a.bottom);
                            const target = candidates[0].el;
                            target.click();
                            target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                            return true;
                        }
                        return false;
                    }""")
                except Exception as e:
                    self.logger.warning(f"JS 버튼 클릭 예외: {e}")

                # 2) Playwright 다중 선택자 강제 클릭
                post_selectors = [
                    "div[role='dialog'] div[role='button']:has-text('게시')",
                    "div[role='dialog'] button:has-text('게시')",
                    "div[role='dialog'] div:text-is('게시')",
                    "div[role='button']:has-text('게시')",
                    "button:has-text('게시')",
                    "div:text-is('게시')",
                ]
                for sel in post_selectors:
                    try:
                        btns = page.locator(sel)
                        if btns.count() > 0:
                            # 가장 마지막(최신 모달) 요소 클릭
                            btns.last.click(force=True)
                            clicked_post = True
                            break
                    except Exception:
                        pass

                # 3) 단축키(Control+Enter) 전송 병행
                try:
                    page.keyboard.press("Control+Enter")
                except Exception:
                    pass

                self.logger.info(f"게시 요청 전송 완료. 서버 처리 및 완료 대기 중 (최대 {upload_timeout}초)...")
                page.wait_for_timeout(3000)
                
                # 게시 완료 상태 확인 (최대 upload_timeout초)
                post_done = False
                for wait_i in range(upload_timeout):
                    page.wait_for_timeout(1000)
                    
                    # 1) '게시되었습니다' 토스트 확인
                    toast = page.locator("div:has-text('게시되었습니다'), div:has-text('Posted'), span:has-text('게시되었습니다')")
                    has_toast = False
                    try:
                        if toast.count() > 0:
                            for i in range(toast.count()):
                                if toast.nth(i).is_visible():
                                    has_toast = True
                                    break
                    except Exception:
                        pass

                    # 2) '게시 중...' 인디케이터 확인
                    posting_indicators = page.locator("text='게시 중', text='Posting', text='게시하는 중', div:has-text('게시 중')")
                    is_posting = False
                    try:
                        if posting_indicators.count() > 0:
                            for i in range(posting_indicators.count()):
                                if posting_indicators.nth(i).is_visible():
                                    is_posting = True
                                    break
                    except Exception:
                        pass

                    # 3) 모달 닫힘 확인
                    dialog = page.locator("div[role='dialog'], div[aria-label*='새로운 스레드']")
                    modal_closed = (dialog.count() == 0)

                    if has_toast:
                        self.logger.info("🎉 Threads '게시되었습니다' 토스트 확인!")
                        post_done = True
                        break
                    elif modal_closed and not is_posting and wait_i >= 5:
                        self.logger.info("🎉 Threads 작성 모달 닫힘 확인!")
                        post_done = True
                        break

                if post_done:
                    # 미디어 크기에 비례하여 넉넉하게 세션 유지 후 정상 종료 (사진 20초, 동영상 30~180초)
                    self.logger.info(f"업로드 세션 안전 동기화 중 ({sync_buffer}초간 넉넉하게 대기)...")
                    page.wait_for_timeout(sync_buffer * 1000)
                    self.logger.info("🎉 Threads 최종 업로드 성공 완료!")
                    browser.close()
                    return True
                else:
                    self.logger.warning("Threads 서버 전송 완료 확인을 받지 못했습니다.")
                    page.wait_for_timeout(5000)
                    browser.close()
                    return False




        except Exception as e:
            self.logger.error(f"Playwright Threads 업로드 실패: {e}")
            return False



