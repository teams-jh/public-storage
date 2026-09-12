import time
from datetime import datetime, timedelta
from pathlib import Path
from platforms.base import BaseUploader
from platforms.scheduling import (
    choose_calendar_date,
    get_scheduled_at,
)
from config import (
    CONFIG, INSTAGRAM_SCHEDULE_MAX_DAYS, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

class InstagramUploader(BaseUploader):
    def __init__(self):
        super().__init__("Instagram")
        self.username = CONFIG.get("INSTAGRAM_USERNAME")
        self.password = CONFIG.get("INSTAGRAM_PASSWORD")

    def _open_create_post_dialog(self, page, create_target) -> bool:
        """만들기 메뉴에서 게시물을 선택하고 파일 업로드 모달이 열릴 때까지 기다립니다."""
        try:
            create_target.locator("..").click()
        except Exception:
            try:
                create_target.click(force=True)
            except Exception as error:
                self.logger.error(f"Instagram 만들기 버튼을 누르지 못했어요: {error}")
                return False

        page.wait_for_timeout(700)
        file_input = page.locator("div[role='dialog'] input[type='file'], input[type='file']")
        if file_input.count() > 0:
            return True

        self.logger.info("만들기 메뉴에서 [게시물]을 선택해요...")
        post_option_clicked = False
        try:
            post_option_clicked = page.evaluate("""() => {
                const labels = new Set(['게시물', 'Post']);
                const elements = Array.from(document.querySelectorAll(
                    "[role='menuitem'], [role='menu'] div, [role='menu'] span, div, span"
                ));
                const candidates = [];

                for (const element of elements) {
                    const text = element.textContent ? element.textContent.trim() : '';
                    if (!labels.has(text)) continue;
                    const rect = element.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    const clickable = element.closest("[role='menuitem'], [role='button'], button, a") || element;
                    const clickableRect = clickable.getBoundingClientRect();
                    candidates.push({ element: clickable, area: clickableRect.width * clickableRect.height });
                }

                if (candidates.length === 0) return false;
                candidates.sort((a, b) => a.area - b.area);
                const target = candidates[0].element;
                target.click();
                return true;
            }""")
        except Exception as error:
            self.logger.warning(f"Instagram [게시물] 메뉴 선택 중 예외가 생겼어요: {error}")

        if not post_option_clicked:
            post_options = page.locator(
                "div[role='menuitem']:has-text('게시물'), div[role='menuitem']:has-text('Post'), "
                "div[role='button']:has(span:text-is('게시물')), "
                "div[role='button']:has(span:text-is('Post')), "
                "span:text-is('게시물'), span:text-is('Post')"
            )
            for index in range(post_options.count()):
                option = post_options.nth(index)
                try:
                    if option.is_visible():
                        option.click(force=True)
                        post_option_clicked = True
                        break
                except Exception:
                    continue

        if not post_option_clicked:
            self.logger.error("Instagram 만들기 메뉴에서 [게시물]을 찾지 못했어요.")
            return False

        try:
            file_input.first.wait_for(state="attached", timeout=10000)
            self.logger.info("Instagram 새 게시물 업로드 모달이 열렸어요.")
            return True
        except Exception:
            self.logger.error("Instagram [게시물]을 선택했지만 업로드 모달이 열리지 않았어요.")
            return False

    def _configure_native_schedule(self, page, scheduled_at: datetime) -> bool:
        """Instagram 고급 설정의 콘텐츠 예약 기능을 설정합니다."""
        if scheduled_at - datetime.now() > timedelta(days=INSTAGRAM_SCHEDULE_MAX_DAYS):
            self.logger.error(f"Instagram은 최대 {INSTAGRAM_SCHEDULE_MAX_DAYS}일 뒤까지만 예약할 수 있어요.")
            return False

        advanced_settings = page.locator(
            "div[role='dialog'] div:text-is('고급 설정'), "
            "div[role='dialog'] span:text-is('고급 설정'), "
            "div[role='dialog'] div:text-is('Advanced settings'), "
            "div[role='dialog'] span:text-is('Advanced settings')"
        )
        try:
            advanced_settings.last.click(force=True)
            page.wait_for_timeout(800)
        except Exception:
            self.logger.error("Instagram 고급 설정을 열지 못했어요.")
            return False

        schedule_labels = page.locator(
            "div[role='dialog'] div:text-is('콘텐츠 예약'), "
            "div[role='dialog'] span:text-is('콘텐츠 예약'), "
            "div[role='dialog'] div:text-is('Schedule this post'), "
            "div[role='dialog'] span:text-is('Schedule this post')"
        )
        toggle = None
        for index in range(schedule_labels.count()):
            label = schedule_labels.nth(index)
            try:
                if not label.is_visible():
                    continue
                candidate = label.locator(
                    "xpath=following::*[@role='switch' or self::input[@type='checkbox']][1]"
                )
                if candidate.count() > 0:
                    toggle = candidate.first
                    break
            except Exception:
                continue

        if toggle is None:
            fallback = page.locator("div[role='dialog'] [role='switch'], div[role='dialog'] input[type='checkbox']")
            if fallback.count() > 0:
                toggle = fallback.last

        if toggle is None:
            self.logger.error("Instagram 콘텐츠 예약 스위치를 찾지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False

        try:
            checked = toggle.get_attribute("aria-checked")
            if checked != "true" and not toggle.is_checked():
                toggle.click(force=True)
        except Exception:
            try:
                toggle.click(force=True)
            except Exception:
                self.logger.error("Instagram 콘텐츠 예약 스위치를 켜지 못했어요.")
                return False

        page.wait_for_timeout(700)
        # Instagram은 현재 날짜가 표시되어 있어도 달력을 열어 날짜를 직접 선택해야 합니다.
        date_set = choose_calendar_date(page, scheduled_at)
        page.wait_for_timeout(500)
        date_set = date_set and self._is_instagram_date_selected(page, scheduled_at)

        # Instagram 시간 입력은 Hours, Minutes, AM PM의 세 필드로 나뉩니다.
        time_set = self._fill_instagram_time(page, scheduled_at)
        if not date_set or not time_set:
            self.logger.error("Instagram 예약 날짜 또는 시간을 입력하지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False

        self.logger.info(f"Instagram 콘텐츠 예약 설정 완료: {scheduled_at:%Y-%m-%d %H:%M}")
        return True

    def _fill_instagram_time(self, page, scheduled_at: datetime) -> bool:
        """Instagram의 분리된 시간 spinbutton에 HH:MM AM/PM 값을 입력합니다."""
        hours = page.locator("input[role='spinbutton'][aria-label='Hours']")
        minutes = page.locator("input[role='spinbutton'][aria-label='Minutes']")
        meridiem = page.locator("input[role='spinbutton'][aria-label='AM PM']")
        if hours.count() == 0 or minutes.count() == 0 or meridiem.count() == 0:
            self.logger.error("Instagram의 Hours, Minutes, AM PM 시간 입력 항목을 찾지 못했어요.")
            return False

        hour_12 = scheduled_at.hour % 12 or 12
        hour_text = f"{hour_12:02d}"
        minute_text = f"{scheduled_at.minute:02d}"
        meridiem_text = "AM" if scheduled_at.hour < 12 else "PM"

        try:
            for field, value in ((hours.first, hour_text), (minutes.first, minute_text)):
                field.click(force=True)
                field.press("Control+A")
                field.type(value)
                field.press("Tab")
                page.wait_for_timeout(250)

            current_meridiem = (
                meridiem.first.get_attribute("aria-valuetext")
                or meridiem.first.locator("xpath=preceding-sibling::label[1]").inner_text()
            ).strip().upper()
            if current_meridiem != meridiem_text:
                meridiem.first.click(force=True)
                meridiem.first.press("ArrowDown")
                meridiem.first.press("Tab")
                page.wait_for_timeout(250)

            hour_value = hours.first.get_attribute("aria-valuenow") or ""
            minute_value = minutes.first.get_attribute("aria-valuenow") or ""
            final_meridiem = (meridiem.first.get_attribute("aria-valuetext") or "").upper()
            if (
                int(hour_value) != hour_12
                or int(minute_value) != scheduled_at.minute
                or final_meridiem != meridiem_text
            ):
                self.logger.error(
                    f"Instagram 시간 입력 검증에 실패했어요. 목표: {hour_text}:{minute_text} {meridiem_text}"
                )
                return False
        except Exception as error:
            self.logger.error(f"Instagram 시간 입력 중 문제가 생겼어요: {error}")
            return False

        self.logger.info(f"Instagram 예약 시간 입력 완료: {hour_text}:{minute_text} {meridiem_text}")
        return True

    def _is_instagram_date_selected(self, page, scheduled_at: datetime) -> bool:
        """Instagram 예약 영역에 목표 날짜가 이미 선택되어 있는지 확인합니다."""
        return page.evaluate("""(target) => {
            const dialog = document.querySelector("div[role='dialog']") || document.body;
            const text = dialog.innerText || '';
            const korean = `${target.year}년 ${target.month}월 ${target.day}일`;
            const iso = `${target.year}-${String(target.month).padStart(2, '0')}-${String(target.day).padStart(2, '0')}`;
            const slash = `${String(target.month).padStart(2, '0')}/${String(target.day).padStart(2, '0')}/${target.year}`;
            return text.includes(korean) || text.includes(iso) || text.includes(slash);
        }""", {
            "year": scheduled_at.year,
            "month": scheduled_at.month,
            "day": scheduled_at.day,
        })

    def _click_final_post_action(self, page, scheduled: bool) -> bool:
        """작성 모달 우측 상단의 예약 또는 공유하기 버튼을 한 번 클릭합니다."""
        labels = ["예약", "예약하기", "Schedule"] if scheduled else ["공유하기", "Share"]
        try:
            result = page.evaluate("""(targetLabels) => {
                const dialogs = Array.from(document.querySelectorAll("div[role='dialog']"));
                const dialog = dialogs.find(item => {
                    const rect = item.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });
                if (!dialog) return { clicked: false, text: '' };

                const dialogRect = dialog.getBoundingClientRect();
                const elements = Array.from(dialog.querySelectorAll("button, [role='button'], span"));
                const clickables = [];
                const seen = new Set();

                for (const element of elements) {
                    const text = element.textContent ? element.textContent.trim() : '';
                    const isExact = targetLabels.includes(text);
                    if (!isExact) continue;

                    const clickable = element.closest("button, [role='button']") || element;
                    if (seen.has(clickable) || clickable.getAttribute('aria-disabled') === 'true') continue;
                    const rect = clickable.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    seen.add(clickable);

                    const inHeader = rect.top < dialogRect.top + dialogRect.height * 0.25;
                    const onRight = rect.left > dialogRect.left + dialogRect.width * 0.5;
                    const score = (isExact ? 100 : 0) + (inHeader ? 20 : 0) + (onRight ? 10 : 0) - rect.width * rect.height / 100000;
                    clickables.push({ element: clickable, text, score });
                }

                if (clickables.length === 0) return { clicked: false, text: '' };
                clickables.sort((a, b) => b.score - a.score);
                const target = clickables[0];
                target.element.click();
                return { clicked: true, text: target.text };
            }""", labels)
        except Exception as error:
            self.logger.error(f"Instagram 최종 저장 버튼 탐색 중 문제가 생겼어요: {error}")
            return False

        if not result or not result.get("clicked"):
            action_name = "예약" if scheduled else "공유하기"
            self.logger.error(f"Instagram 최종 {action_name} 버튼을 찾지 못했어요.")
            return False

        self.logger.info(f"Instagram 최종 버튼 클릭 완료: {result.get('text')}")
        return True

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        Instagram 릴스/사진/GIF 업로드
        1. instagrapi 라이브러리가 있는 경우 모바일 API 세션으로 업로드 시도 (사진/릴스 분기)
        2. 없는 경우 Playwright 웹 자동화로 대체
        """
        caption = metadata.get("full_caption", "")
        media_type = get_media_type(media_path)
        scheduled_at = get_scheduled_at(metadata)
        self.logger.info(f"Instagram 업로드 시작 ({media_type.upper()}): {media_path.name}")
        self.logger.info(f"캡션 내용 요약:\n{caption[:100]}...")

        # 예약 게시에는 Instagram 자체 예약 UI가 필요하므로 모바일 API를 사용하지 않습니다.
        if scheduled_at:
            self.logger.info("Instagram 자체 콘텐츠 예약 기능을 사용하기 위해 Playwright 모드로 진행해요.")
        else:
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
        return self._upload_via_playwright(media_path, metadata)

    def _upload_via_playwright(self, media_path: Path, metadata: dict) -> bool:
        try:
            caption = metadata.get("full_caption", "")
            target_ratio = metadata.get("ratio", "9:16").strip()
            scheduled_at = get_scheduled_at(metadata)

            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_insta"
            user_data_dir.mkdir(exist_ok=True)

            media_type = get_media_type(media_path)
            size_mb = get_media_size_mb(media_path)
            upload_timeout = get_dynamic_upload_timeout(media_path)
            sync_buffer = get_dynamic_sync_buffer(media_path)

            self.logger.info(f"Playwright 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 세션 유지: {sync_buffer}초, 설정 비율: {target_ratio})")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,  # 첫 로그인/인증을 위해 브라우저 표시
                    permissions=["clipboard-read", "clipboard-write"],
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
                    self.log_wait_progress("Instagram 로그인 대기", attempt * 5, 180)
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
                    if not self._open_create_post_dialog(page, create_target):
                        browser.close()
                        return False

                    # 1. 파일 업로드 인풋 주입
                    file_input = page.locator("div[role='dialog'] input[type='file'], input[type='file']")
                    if file_input.count() > 0:
                        self.logger.info("미디어 파일 첨부 중...")
                        file_input.first.set_input_files(str(media_path.resolve()))
                        page.wait_for_timeout(3000)

                    # 1-1. 화면 비율(9:16 등) 선택 (자르기 화면)
                    if target_ratio:
                        self.logger.info(f"화면 비율 설정 시도 ({target_ratio})...")
                        try:
                            # 1) 모달 내 좌측 하단의 '자르기 선택' (Crop) 버튼 클릭
                            crop_clicked = False
                            try:
                                crop_clicked = page.evaluate("""() => {
                                    const dialog = document.querySelector("div[role='dialog']");
                                    if (!dialog) return false;
                                    
                                    // 1. svg aria-label 검사
                                    const svgs = Array.from(dialog.querySelectorAll("svg"));
                                    for (const svg of svgs) {
                                        const label = (svg.getAttribute("aria-label") || "").toLowerCase();
                                        if (label.includes("자르기") || label.includes("crop") || label.includes("비율") || label.includes("ratio")) {
                                            const btn = svg.closest("button") || svg.closest("div[role='button']") || svg;
                                            btn.click();
                                            btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                            return true;
                                        }
                                    }
                                    
                                    // 2. 모달 좌측 하단 둥근 버튼 검색
                                    const buttons = Array.from(dialog.querySelectorAll("button, div[role='button']"));
                                    const dRect = dialog.getBoundingClientRect();
                                    for (const btn of buttons) {
                                        const bRect = btn.getBoundingClientRect();
                                        if (
                                            bRect.left - dRect.left < dRect.width * 0.35 &&
                                            bRect.bottom > dRect.top + dRect.height * 0.65 &&
                                            bRect.width >= 20 && bRect.width <= 70 &&
                                            bRect.height >= 20 && bRect.height <= 70
                                        ) {
                                            btn.click();
                                            btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                            return true;
                                        }
                                    }
                                    return false;
                                }""")
                            except Exception as e:
                                self.logger.warning(f"JS 자르기 버튼 클릭 예외: {e}")

                            if not crop_clicked:
                                crop_loc = page.locator(
                                    "div[role='dialog'] svg[aria-label*='자르기'], "
                                    "div[role='dialog'] svg[aria-label*='Crop'], "
                                    "div[role='dialog'] svg[aria-label*='crop']"
                                )
                                if crop_loc.count() > 0:
                                    crop_loc.first.click(force=True)
                                    crop_clicked = True

                            page.wait_for_timeout(800)

                            # 2) 팝업 메뉴에서 지정된 비율 (예: '9:16') 클릭
                            ratio_clicked = False
                            try:
                                ratio_clicked = page.evaluate("""(targetRatio) => {
                                    const dialog = document.querySelector("div[role='dialog']") || document.body;
                                    const elements = Array.from(dialog.querySelectorAll("button, div[role='button'], div, span"));
                                    for (const el of elements) {
                                        const txt = el.textContent ? el.textContent.trim() : "";
                                        if (txt === targetRatio) {
                                            const clickable = el.closest("button") || el.closest("div[role='button']") || el;
                                            clickable.click();
                                            clickable.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                            return true;
                                        }
                                    }
                                    return false;
                                }""", target_ratio)
                            except Exception as e:
                                self.logger.warning(f"JS 비율 선택 예외: {e}")

                            if not ratio_clicked:
                                ratio_loc = page.locator(
                                    f"div[role='dialog'] span:text-is('{target_ratio}'), "
                                    f"div[role='dialog'] div:text-is('{target_ratio}'), "
                                    f"div[role='dialog'] button:has-text('{target_ratio}'), "
                                    f"span:text-is('{target_ratio}'), "
                                    f"div:text-is('{target_ratio}')"
                                )
                                if ratio_loc.count() > 0:
                                    ratio_loc.first.click(force=True)
                                    ratio_clicked = True

                            if ratio_clicked:
                                self.logger.info(f"🎉 Instagram 화면 비율 설정 완료: {target_ratio}")
                            else:
                                self.logger.warning(f"Instagram 화면 비율({target_ratio}) 버튼을 찾지 못했습니다.")

                            page.wait_for_timeout(1000)
                        except Exception as e:
                            self.logger.warning(f"비율 설정 중 예외 발생 (무시): {e}")

                    # 2. [자르기 -> 필터 -> 캡션] 화면으로 순차 이동
                    self.logger.info("자르기 및 필터 단계를 거쳐 캡션(문구 입력) 화면으로 이동합니다...")
                    
                    # 헬퍼: 모달 우측 상단의 액션 버튼(다음/공유하기) 클릭 함수
                    def click_header_action(btn_text: str):
                        try:
                            # 1) JS DOM 이벤트 전송
                            page.evaluate("""(targetText) => {
                                const dialog = document.querySelector("div[role='dialog']");
                                if (!dialog) return false;
                                const elements = Array.from(dialog.querySelectorAll("div[role='button'], button, span"));
                                for (const el of elements) {
                                    const text = el.textContent ? el.textContent.trim() : "";
                                    if (text === targetText || (targetText === '다음' && text === 'Next') || (targetText === '공유하기' && text === 'Share')) {
                                        el.click();
                                        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                        return true;
                                    }
                                }
                                return false;
                            }""", btn_text)
                        except Exception:
                            pass
                        
                        # 2) Playwright 클릭
                        btn_loc = page.locator(
                            f"div[role='dialog'] div[role='button']:has-text('{btn_text}'), "
                            f"div[role='dialog'] button:has-text('{btn_text}'), "
                            f"div[role='dialog'] div:text-is('{btn_text}')"
                        )
                        if btn_loc.count() > 0:
                            try:
                                btn_loc.first.click(force=True)
                            except Exception:
                                pass

                    # 1번째 '다음' 클릭 (자르기 -> 필터)
                    self.logger.info("1단계: 자르기 화면에서 [다음] 클릭...")
                    click_header_action("다음")
                    page.wait_for_timeout(2500)

                    # 2번째 '다음' 클릭 (필터 -> 캡션 입력)
                    self.logger.info("2단계: 필터 화면에서 [다음] 클릭...")
                    click_header_action("다음")
                    page.wait_for_timeout(2500)

                    # 3단계: [공유하기] 버튼 또는 캡션 입력창이 나타날 때까지 대기
                    self.logger.info("3단계: 캡션 입력 및 [공유하기] 화면 도달 대기 중...")
                    for _ in range(10):
                        has_share = page.locator("div[role='dialog'] div[role='button']:has-text('공유하기'), div[role='dialog'] button:has-text('공유하기'), div[role='dialog'] div:text-is('공유하기')")
                        if has_share.count() > 0 and has_share.first.is_visible():
                            break
                        # 혹시 아직 필터 화면에 머물러 있다면 한 번 더 다음 클릭
                        click_header_action("다음")
                        page.wait_for_timeout(1000)

                    # 3. 캡션(문구) 입력창 찾기 및 클립보드(Control+V) 강력 주입
                    self.logger.info("캡션(문구) 입력창 탐색 및 텍스트 주입 시도...")
                    
                    # 브라우저 클립보드에 캡션 복사
                    try:
                        page.evaluate("""(text) => navigator.clipboard.writeText(text)""", caption)
                    except Exception as e:
                        self.logger.warning(f"클립보드 복사 실패 (무시): {e}")

                    caption_box = page.locator(
                        "div[role='dialog'] div[contenteditable='true'], "
                        "div[role='dialog'] div[aria-label*='문구'], "
                        "div[role='dialog'] div[aria-label*='caption'], "
                        "div[role='dialog'] div[role='textbox']"
                    )

                    if caption_box.count() > 0:
                        try:
                            target_box = caption_box.first
                            target_box.click(force=True)
                            page.wait_for_timeout(500)
                            
                            # 1) Control+A 후 Backspace
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            page.wait_for_timeout(200)

                            # 2) 클립보드 붙여넣기 (Control+V)
                            # 해시태그 입력 후 자동완성 팝업 방지를 위해 끝에 공백 1칸 추가
                            safe_caption = caption.rstrip() + " "
                            try:
                                page.evaluate("""(text) => navigator.clipboard.writeText(text)""", safe_caption)
                            except Exception:
                                pass

                            page.keyboard.press("Control+V")
                            page.wait_for_timeout(1000)

                            # 3) 만약 내용이 안 들어갔다면 insert_text fallback
                            entered_text = target_box.inner_text().strip()
                            if not entered_text and caption.strip():
                                self.logger.info("Control+V 미반영 감지 -> insert_text 시도...")
                                page.keyboard.insert_text(safe_caption)
                                page.wait_for_timeout(1000)
                                entered_text = target_box.inner_text().strip()

                            # 4) 그래도 안 들어갔다면 execCommand fallback
                            if not entered_text and caption.strip():
                                self.logger.info("insert_text 미반영 감지 -> JS execCommand 직접 주입 시도...")
                                page.evaluate("""(text) => {
                                    const editor = document.querySelector("div[role='dialog'] div[contenteditable='true']");
                                    if (editor) {
                                        editor.focus();
                                        document.execCommand('selectAll', false, null);
                                        document.execCommand('insertText', false, text);
                                    }
                                }""", safe_caption)
                                page.wait_for_timeout(1000)
                                entered_text = target_box.inner_text().strip()

                            # 5) 중요: 해시태그 추천 드롭다운 팝업 닫기 및 포커스 해제 (Blur)
                            self.logger.info("해시태그 자동완성 추천 팝업 닫기 및 포커스 정리 중...")
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(300)
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(300)
                            
                            # 에디터 포커스 강제 해제 및 모달 빈 영역 클릭
                            page.evaluate("""() => {
                                if (document.activeElement && document.activeElement.blur) {
                                    document.activeElement.blur();
                                }
                            }""")
                            page.wait_for_timeout(500)

                            self.logger.info(f"🎉 Instagram 캡션 입력 완료! (입력된 글자 수: {len(entered_text)}자)")
                        except Exception as e:
                            self.logger.warning(f"캡션 입력 중 오류: {e}")
                    else:
                        self.logger.warning("⚠️ 캡션 입력창(contenteditable)을 찾지 못했습니다.")

                    if scheduled_at and not self._configure_native_schedule(page, scheduled_at):
                        browser.close()
                        return False

                    # 4. 우측 상단 [공유하기]/[예약] 버튼 클릭
                    action_name = "예약" if scheduled_at else "공유하기"
                    self.logger.info(f"최종 [{action_name}] 버튼 클릭 시도...")
                    page.wait_for_timeout(1500)
                    if not self._click_final_post_action(page, scheduled=bool(scheduled_at)):
                        browser.close()
                        return False
                    page.wait_for_timeout(1500)

                    # 5. 실제 업로드 완료 엄격 검증 (오직 업로드 모달 내부에서 확인)
                    upload_success = False
                    self.logger.info(f"모달 내부에서 실제 업로드 완료 화면을 대기합니다 (최대 {upload_timeout}초 = {upload_timeout // 60}분)...")
                    
                    for wait_i in range(upload_timeout):
                        self.log_wait_progress(
                            "Instagram 업로드 완료 확인", wait_i, upload_timeout
                        )
                        page.wait_for_timeout(1000)
                        
                        # 업로드 모달(div[role='dialog']) 내부의 텍스트만 엄격하게 검사
                        is_completed = False
                        try:
                            is_completed = page.evaluate("""() => {
                                const dialogs = Array.from(document.querySelectorAll("div[role='dialog']"));
                                const bodyText = document.body.innerText || "";
                                if (
                                    bodyText.includes("게시물이 예약되었습니다") ||
                                    bodyText.includes("콘텐츠가 예약되었습니다") ||
                                    bodyText.includes("예약되었어요") ||
                                    bodyText.includes("has been scheduled")
                                ) {
                                    return true;
                                }
                                for (const dialog of dialogs) {
                                    const text = dialog.innerText || "";
                                    // 오직 모달 내부에서 완료 문구가 명확히 떴을 때만 감지
                                    if (
                                        text.includes("게시물이 공유되었습니다") ||
                                        text.includes("동영상이 공유되었습니다") ||
                                        text.includes("릴스가 공유되었습니다") ||
                                        text.includes("Your post has been shared") ||
                                        text.includes("Your reel has been shared") ||
                                        text.includes("예약되었습니다") ||
                                        text.includes("예약되었어요") ||
                                        text.includes("has been scheduled") ||
                                        (text.includes("공유되었습니다") && !text.includes("공유하기"))
                                    ) {
                                        return true;
                                    }
                                }
                                return dialogs.length === 0;
                            }""")
                        except Exception:
                            pass

                        if is_completed:
                            upload_success = True
                            self.logger.info("🎉 Instagram 모달 완료 화면 감지: 게시물이 성공적으로 공유되었습니다!")
                            break

                        # 버튼 클릭이 반영되지 않은 경우에만 동일한 최종 액션을 한 번 더 시도
                        if wait_i == 8 or wait_i == 20:
                            self.logger.info(f"{action_name} 버튼 재클릭 시도...")
                            self._click_final_post_action(page, scheduled=bool(scheduled_at))

                    if upload_success:
                        self.wait_with_countdown(
                            page, sync_buffer, "Instagram 업로드 세션 안전 동기화"
                        )
                        self.logger.info("🎉 Instagram 업로드 최종 성공 완료!")
                        self.save_result_screenshot(
                            page, "scheduled" if scheduled_at else "uploaded"
                        )
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



