import os
import time
from pathlib import Path
from platforms.base import BaseUploader
from platforms.scheduling import get_scheduled_at
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

    def _click_visible_button(self, page, selectors: str, description: str):
        """숨겨진 복제 요소를 제외하고 현재 화면의 버튼 하나만 클릭합니다."""
        candidates = page.locator(selectors)
        for index in range(candidates.count() - 1, -1, -1):
            candidate = candidates.nth(index)
            try:
                if not candidate.is_visible():
                    continue
                candidate.scroll_into_view_if_needed()
                candidate.click(timeout=5000)
                self.logger.info(f"X [{description}] 버튼 클릭 완료")
                return candidate
            except Exception:
                try:
                    candidate.click(force=True, timeout=3000)
                    self.logger.info(f"X [{description}] 버튼 강제 클릭 완료")
                    return candidate
                except Exception:
                    try:
                        candidate.evaluate("element => element.click()")
                        self.logger.info(f"X [{description}] 버튼 DOM 클릭 완료")
                        return candidate
                    except Exception:
                        continue
        return None

    def _click_schedule_icon_fallback(self, page) -> bool:
        """X의 속성이 바뀐 경우 달력+시계 SVG 모양으로 예약 아이콘을 찾습니다."""
        try:
            return bool(page.evaluate("""() => {
                const isVisible = element => {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width > 0 && rect.height > 0
                        && style.display !== 'none'
                        && style.visibility !== 'hidden';
                };

                const composeRoots = Array.from(document.querySelectorAll('[role="dialog"]'))
                    .filter(root => isVisible(root) && root.querySelector('[data-testid="tweetTextarea_0"], [role="textbox"]'));
                const root = composeRoots.at(-1) || document;
                const controls = Array.from(root.querySelectorAll('button, [role="button"]'))
                    .filter(isVisible);

                const scheduleControl = controls.find(control => {
                    const testId = (control.getAttribute('data-testid') || '').toLowerCase();
                    const label = (control.getAttribute('aria-label') || '').toLowerCase();
                    const title = (control.getAttribute('title') || '').toLowerCase();
                    const paths = Array.from(control.querySelectorAll('svg path'))
                        .map(path => (path.getAttribute('d') || '').replace(/\\s+/g, ''))
                        .join(' ');
                    const semanticMatch = testId === 'scheduleoption'
                        || label.includes('schedule') || label.includes('예약')
                        || title.includes('schedule') || title.includes('예약');
                    const calendarClockMatch = paths.includes('M6 3V2h2v1h6V2h2v1')
                        || (paths.includes('M15.5 11') && paths.includes('4.5'));
                    return semanticMatch || calendarClockMatch;
                });

                if (!scheduleControl) return false;
                scheduleControl.scrollIntoView({ block: 'center', inline: 'center' });
                scheduleControl.click();
                return true;
            }"""))
        except Exception:
            return False

    def _click_exact_schedule_svg(self, page) -> bool:
        """X의 달력+시계 path에서 실제 클릭 가능한 상위 버튼을 역으로 찾습니다."""
        paths = page.locator(
            "svg path[d^='M6 3V2h2v1h6V2h2v1h1.5'], "
            "svg path[d*='M9 15.5C9 11.91']"
        )
        self.logger.info(f"X 달력+시계 SVG 탐색 결과: {paths.count()}개")

        for index in range(paths.count() - 1, -1, -1):
            path = paths.nth(index)
            try:
                svg = path.locator("xpath=ancestor::svg[1]")
                if svg.count() == 0 or not svg.is_visible():
                    continue

                button = path.locator(
                    "xpath=ancestor::*[self::button or @role='button'][1]"
                )
                if button.count() > 0 and button.is_visible():
                    button.scroll_into_view_if_needed()
                    try:
                        button.click(timeout=5000)
                    except Exception:
                        button.click(force=True, timeout=3000)
                    self.logger.info("X 달력+시계 SVG의 상위 버튼 클릭 완료")
                    return True

                # X의 마크업이 button 조상을 제거한 경우 SVG 중앙을 실제 마우스로 눌러요.
                svg.scroll_into_view_if_needed()
                box = svg.bounding_box()
                if box:
                    page.mouse.click(
                        box["x"] + box["width"] / 2,
                        box["y"] + box["height"] / 2,
                    )
                    self.logger.info("X 달력+시계 SVG 중앙 좌표 클릭 완료")
                    return True
            except Exception as error:
                self.logger.warning(f"X 달력+시계 SVG 클릭 재시도 중: {error}")
        return False

    def _log_visible_compose_buttons(self, page):
        """예약 아이콘 탐색 실패 시 현재 작성창 버튼 속성을 진단 로그에 남깁니다."""
        try:
            buttons = page.evaluate("""() => Array.from(document.querySelectorAll('button, [role="button"]'))
                .filter(element => {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width > 0 && rect.height > 0
                        && style.display !== 'none' && style.visibility !== 'hidden';
                })
                .map(element => ({
                    testid: element.getAttribute('data-testid') || '',
                    aria: element.getAttribute('aria-label') || '',
                    text: (element.innerText || '').trim().slice(0, 40),
                }))
                .filter(item => item.testid || item.aria || item.text)
                .slice(-30)""")
            self.logger.error(f"X 화면의 버튼 목록: {buttons}")
        except Exception as error:
            self.logger.error(f"X 버튼 목록 확인에도 실패했어요: {error}")

    def _configure_native_schedule(self, page, scheduled_at) -> bool:
        """X 작성 창의 캘린더에서 예약 날짜와 시간을 설정합니다."""
        schedule_dialog_selector = (
            "div[role='dialog']:has(button[data-testid='scheduledConfirmationPrimaryAction']):visible"
        )
        schedule_dialog_opened = False
        for attempt in range(3):
            if attempt == 0:
                clicked = self._click_exact_schedule_svg(page)
            elif attempt == 1:
                clicked = self._click_visible_button(
                    page,
                    "div[role='dialog']:visible button[data-testid='scheduleOption']:visible, "
                    "button[data-testid='scheduleOption'][aria-label='Schedule post']:visible, "
                    "[data-testid='scheduleOption']:visible, "
                    "[role='button'][aria-label*='Schedule' i]:visible, "
                    "[role='button'][aria-label*='예약']:visible",
                    "Schedule post",
                ) is not None
            else:
                clicked = self._click_schedule_icon_fallback(page)

            if not clicked:
                continue
            try:
                page.locator(schedule_dialog_selector).last.wait_for(
                    state="visible", timeout=5000
                )
                schedule_dialog_opened = True
                break
            except Exception:
                self.logger.warning(
                    f"X Schedule 아이콘 클릭 후 설정창이 열리지 않아 재시도해요 ({attempt + 1}/3)"
                )

        if not schedule_dialog_opened:
            self._log_visible_compose_buttons(page)
            self.logger.error("X 예약 캘린더 버튼을 클릭하지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False

        dialog = page.locator(schedule_dialog_selector).last
        if dialog.count() == 0:
            self.logger.error("X Schedule 설정 창을 찾지 못했어요.")
            return False

        date_selects = dialog.locator("div[role='group'][aria-label='Date'] select")
        time_selects = dialog.locator("div[role='group'][aria-label='Time'] select")
        try:
            if date_selects.count() != 3 or time_selects.count() != 3:
                self.logger.error("X 예약 날짜·시간 입력 항목을 찾지 못했어요. 즉시 게시하지 않고 중단해요.")
                return False

            # Date 그룹: Month, Day, Year. 연도를 먼저 바꿔 날짜 옵션 갱신을 안정화해요.
            date_selects.nth(2).select_option(value=str(scheduled_at.year))
            date_selects.nth(0).select_option(value=str(scheduled_at.month))
            date_selects.nth(1).select_option(value=str(scheduled_at.day))

            # Time 그룹: Hour, Minute, AM/PM.
            hour_12 = scheduled_at.hour % 12 or 12
            meridiem = "am" if scheduled_at.hour < 12 else "pm"
            time_selects.nth(0).select_option(value=str(hour_12))
            time_selects.nth(1).select_option(value=str(scheduled_at.minute))
            time_selects.nth(2).select_option(value=meridiem)

            expected_values = (
                str(scheduled_at.month),
                str(scheduled_at.day),
                str(scheduled_at.year),
                str(hour_12),
                str(scheduled_at.minute),
                meridiem,
            )
            actual_values = tuple(
                locator.input_value()
                for locator in (
                    date_selects.nth(0),
                    date_selects.nth(1),
                    date_selects.nth(2),
                    time_selects.nth(0),
                    time_selects.nth(1),
                    time_selects.nth(2),
                )
            )
            if actual_values != expected_values:
                self.logger.error(
                    f"X 예약값 확인에 실패했어요: 기대 {expected_values}, 실제 {actual_values}"
                )
                return False
        except Exception as error:
            self.logger.error(f"X 예약 날짜·시간 입력에 실패했어요: {error}")
            return False

        confirm = self._click_visible_button(
            page,
            "div[role='dialog']:visible button[data-testid='scheduledConfirmationPrimaryAction']:visible, "
            "button[data-testid='scheduledConfirmationPrimaryAction']:visible",
            "Confirm",
        )
        if confirm is None:
            self.logger.error("X 예약 확인 버튼을 찾지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False

        try:
            dialog.wait_for(state="hidden", timeout=10000)
        except Exception:
            self.logger.error("X Confirm 클릭 후 Schedule 설정 창이 닫히지 않았어요.")
            return False

        self.logger.info(f"X 자체 예약 설정 완료: {scheduled_at:%Y-%m-%d %H:%M}")
        return True

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
        scheduled_at = get_scheduled_at(metadata)
        self.logger.info(f"X(Twitter) 업로드 시작 ({media_type.upper()}): {media_path.name}")

        # 방법 1: Tweepy를 통한 API 업로드
        if scheduled_at:
            self.logger.info("X 자체 예약 기능을 사용하기 위해 Playwright 모드로 진행해요.")
        elif all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
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
        return self._upload_via_playwright(media_path, caption, scheduled_at)

    def _upload_via_playwright(self, media_path: Path, caption: str, scheduled_at=None) -> bool:
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
                    self.log_wait_progress("X 로그인 대기", attempt * 5, 180)
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
                    for wait_i in range(upload_timeout // 2):
                        self.log_wait_progress(
                            "X 미디어 처리·렌더링", wait_i * 2, upload_timeout
                        )
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

                if scheduled_at and not self._configure_native_schedule(page, scheduled_at):
                    browser.close()
                    return False

                if scheduled_at:
                    final_button_selector = (
                        "button[data-testid='tweetButton']:has-text('Schedule'):visible, "
                        "div[role='dialog']:visible button[data-testid='tweetButton']:has-text('Schedule'):visible, "
                        "div[role='dialog']:visible button[data-testid='tweetButtonInline']:has-text('Schedule'):visible, "
                        "div[role='dialog']:visible button[data-testid='tweetButton']:has-text('예약'):visible, "
                        "div[role='dialog']:visible button[data-testid='tweetButtonInline']:has-text('예약'):visible, "
                        "div[role='dialog']:visible button[aria-label='Schedule']:visible, "
                        "div[role='dialog']:visible button:text-is('Schedule'):visible, "
                        "div[role='dialog']:visible button:text-is('예약'):visible, "
                        "div[role='dialog']:visible button:text-is('예약하기'):visible"
                    )
                else:
                    final_button_selector = (
                        "div[role='dialog']:visible button[data-testid='tweetButton']:visible, "
                        "button[data-testid='tweetButton']:visible, "
                        "button[data-testid='tweetButtonInline']:visible, "
                        "div[data-testid='tweetButtonInline']:visible, "
                        "div[data-testid='tweetButton']:visible, "
                        "button:has-text('Post'):visible, "
                        "button:has-text('게시하기'):visible"
                    )

                post_btn = page.locator(final_button_selector)
                try:
                    post_btn.last.wait_for(state="visible", timeout=30000)
                except Exception:
                    pass

                if post_btn.count() > 0:
                    # X는 닫힌 작성창을 DOM에 남길 수 있어서 화면에 보이는 마지막 버튼을 사용해요.
                    target_btn = post_btn.last
                    # 비활성화 해제 대기 (최대 30초)
                    button_ready = False
                    for wait_i in range(30):
                        self.log_wait_progress("X 최종 버튼 활성화 대기", wait_i, 30)
                        try:
                            aria_disabled = target_btn.get_attribute("aria-disabled")
                            if target_btn.is_enabled() and aria_disabled != "true":
                                button_ready = True
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)

                    if not button_ready:
                        self.logger.error("X 최종 버튼이 활성화되지 않았어요. 클릭하지 않고 중단해요.")
                        browser.close()
                        return False

                    action_name = "예약" if scheduled_at else "게시하기"
                    try:
                        visible_button_text = target_btn.inner_text().strip()
                    except Exception:
                        visible_button_text = ""
                    if scheduled_at and visible_button_text.casefold() != "schedule":
                        self.logger.error(
                            f"X 최종 버튼이 Schedule로 바뀌지 않았어요: {visible_button_text or '문구 없음'}"
                        )
                        browser.close()
                        return False
                    self.logger.info(
                        f"하단 {action_name} 실행 중... "
                        f"(화면 버튼 문구: {visible_button_text or '확인 불가'})"
                    )

                    final_clicked = False
                    if scheduled_at:
                        # 화면에 보이는 Schedule 버튼의 중앙을 실제 마우스로 눌러요.
                        try:
                            target_btn.scroll_into_view_if_needed()
                            button_box = target_btn.bounding_box()
                            if button_box:
                                page.mouse.click(
                                    button_box["x"] + button_box["width"] / 2,
                                    button_box["y"] + button_box["height"] / 2,
                                )
                                self.logger.info("X 최종 Schedule 버튼 중앙 좌표 클릭 완료")
                                page.wait_for_timeout(2500)
                                try:
                                    final_clicked = (
                                        not target_btn.is_visible()
                                        or not target_btn.is_enabled()
                                        or target_btn.get_attribute("aria-disabled") == "true"
                                    )
                                except Exception:
                                    # 클릭으로 작성 모달이 제거되면 기존 locator 접근이 실패해요.
                                    final_clicked = True
                        except Exception as error:
                            self.logger.warning(f"X Schedule 좌표 클릭 확인 실패: {error}")

                        if not final_clicked:
                            try:
                                target_btn.click(timeout=5000)
                                self.logger.info("X 최종 Schedule 버튼 Playwright 클릭 완료")
                                page.wait_for_timeout(2500)
                                try:
                                    final_clicked = (
                                        not target_btn.is_visible()
                                        or not target_btn.is_enabled()
                                        or target_btn.get_attribute("aria-disabled") == "true"
                                    )
                                except Exception:
                                    final_clicked = True
                            except Exception:
                                pass

                        if not final_clicked:
                            try:
                                target_btn.evaluate("element => element.click()")
                                self.logger.info("X 최종 Schedule 버튼 DOM 클릭 완료")
                                page.wait_for_timeout(2500)
                                try:
                                    final_clicked = (
                                        not target_btn.is_visible()
                                        or not target_btn.is_enabled()
                                        or target_btn.get_attribute("aria-disabled") == "true"
                                    )
                                except Exception:
                                    final_clicked = True
                            except Exception:
                                pass
                    else:
                        try:
                            target_btn.click(force=True)
                            final_clicked = True
                        except Exception:
                            pass

                        if not final_clicked:
                            try:
                                final_clicked = target_btn.evaluate(
                                    "element => { element.click(); return true; }"
                                )
                            except Exception:
                                pass

                    if not final_clicked:
                        self.logger.error(f"X 최종 [{action_name}] 버튼을 클릭하지 못했어요.")
                        browser.close()
                        return False

                    # 즉시 게시일 때만 전송 단축키를 보조로 사용해요.
                    if not scheduled_at:
                        try:
                            page.keyboard.press("Control+Enter")
                        except Exception:
                            pass

                    self.logger.info(f"게시 요청 전송 완료. 서버 처리 및 완료 대기 중 (최대 {upload_timeout}초)...")
                    
                    # 완료 대기 (모달 닫힘 또는 토스트 메시지 감지, 최대 upload_timeout초)
                    tweet_sent = False
                    for wait_i in range(upload_timeout):
                        self.log_wait_progress(
                            "X 게시 완료 확인", wait_i, upload_timeout
                        )
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
                        self.wait_with_countdown(
                            page, sync_buffer, "X 업로드 세션 안전 동기화"
                        )
                        result_name = "예약 등록" if scheduled_at else "업로드"
                        self.logger.info(f"🎉 X(Twitter) {result_name} 최종 완료!")
                        self.save_result_screenshot(
                            page, "scheduled" if scheduled_at else "uploaded"
                        )
                        browser.close()
                        return True
                    else:
                        self.logger.warning("X(Twitter) 서버 완료 상태를 감지하지 못했습니다.")
                        page.wait_for_timeout(5000)
                        browser.close()
                        return False

                missing_action_name = "Schedule" if scheduled_at else "게시하기"
                self.logger.error(f"X(Twitter) 최종 {missing_action_name} 버튼을 찾을 수 없어요.")
                page.wait_for_timeout(5000)
                browser.close()
                return False



        except Exception as e:
            self.logger.error(f"Playwright X(Twitter) 업로드 실패: {e}")
            return False
