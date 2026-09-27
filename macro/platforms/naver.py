"""네이버 클립 크리에이터 PC 웹의 동영상 업로더."""

from datetime import datetime, timedelta
from pathlib import Path
import re
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import (
    LOGIN_TIMEOUT_SECONDS,
    NAVER_CLIP_CATEGORY,
    NAVER_CLIP_AI_LABEL_ENABLED,
    NAVER_CLIP_MAX_BODY_LENGTH,
    NAVER_CLIP_MAX_HASHTAGS,
    NAVER_CLIP_SCHEDULE_MAX_DAYS,
    NAVER_CLIP_URL,
    NAVER_CLIP_UI_TIMEOUT_SECONDS,
    NAVER_CLIP_NAVIGATION_TIMEOUT_SECONDS,
    NAVER_CLIP_POLL_INTERVAL_MS,
    NAVER_CLIP_STEP_DELAY_MS,
    NAVER_CLIP_CONFIRM_DELAY_MS,
    NAVER_CLIP_BODY_READ_TIMEOUT_MS,
    SESSION_DIR,
    VIDEO_EXTENSIONS,
    get_dynamic_upload_timeout,
)
from platforms.base import BaseUploader
from platforms.scheduling import (
    _get_calendar_displayed_month,
    choose_calendar_date,
    get_scheduled_at,
)


class NaverClipUploader(BaseUploader):
    def __init__(self):
        super().__init__("Naver Clip")

    def _pause(self, page, stage: str) -> None:
        self.logger.info(f"{stage} — 화면을 확인할 수 있도록 잠시 기다려요.")
        page.wait_for_timeout(NAVER_CLIP_STEP_DELAY_MS)

    @staticmethod
    def _visible(locator):
        """첫 번째 보이는 요소를 반환합니다."""
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible():
                return candidate
        return None

    def _wait_for_login(self, page) -> bool:
        if "nid.naver.com" not in page.url:
            return True
        self.logger.info(
            "네이버 로그인이 필요해요. 열린 브라우저에서 로그인해 주세요 "
            f"(최대 {LOGIN_TIMEOUT_SECONDS}초 대기)."
        )
        try:
            page.wait_for_url(
                "https://clipcreators.naver.com/web/**",
                timeout=LOGIN_TIMEOUT_SECONDS * 1000,
            )
            return True
        except PlaywrightTimeoutError:
            self.logger.error("네이버 로그인 대기 시간이 지났어요.")
            return False

    def _open_upload_form(self, page) -> bool:
        # React Aria 버튼의 실제 속성을 사용합니다. 텍스트 검색은 제목이나 메뉴를
        # 잘못 선택할 수 있어 이 단계에서는 사용하지 않습니다.
        upload = page.locator(
            "button[aria-label='업로드'][aria-haspopup='true'], "
            "button[class*='UploadButton_trigger'][aria-label='업로드']"
        ).first
        try:
            upload.wait_for(
                state="visible", timeout=NAVER_CLIP_UI_TIMEOUT_SECONDS * 1000
            )
        except PlaywrightTimeoutError:
            self.logger.error(f"[업로드] 버튼을 찾지 못했어요. 현재 주소: {page.url}")
            self.save_result_screenshot(page, "upload_button_missing")
            return False

        video_menu = page.get_by_text("동영상 업로드", exact=True)
        for click_mode in ("normal", "force", "dom"):
            try:
                if click_mode == "normal":
                    upload.click(timeout=NAVER_CLIP_UI_TIMEOUT_SECONDS * 1000)
                elif click_mode == "force":
                    upload.click(force=True, timeout=NAVER_CLIP_UI_TIMEOUT_SECONDS * 1000)
                else:
                    upload.evaluate("button => button.click()")
                self._pause(page, "업로드 메뉴 열기")
                if upload.get_attribute("aria-expanded") == "true" or self._visible(video_menu):
                    break
            except Exception as error:
                self.logger.warning(f"[업로드] 버튼 {click_mode} 클릭을 확인하지 못했어요: {error}")
        else:
            self.logger.error(f"[업로드] 버튼을 눌렀지만 메뉴가 열리지 않았어요. 현재 주소: {page.url}")
            self.save_result_screenshot(page, "upload_menu_missing")
            return False

        deadline = time.monotonic() + NAVER_CLIP_UI_TIMEOUT_SECONDS
        video_upload = None
        while video_upload is None and time.monotonic() < deadline:
            video_upload = self._visible(video_menu)
            if video_upload is None:
                page.wait_for_timeout(NAVER_CLIP_POLL_INTERVAL_MS)
        if video_upload is None:
            self.logger.error("[동영상 업로드] 메뉴를 찾지 못했어요.")
            self.save_result_screenshot(page, "video_upload_menu_missing")
            return False
        video_upload.click()
        self._pause(page, "동영상 업로드 화면 열기")
        return True

    def _make_body(self, metadata: dict) -> str | None:
        # 네이버 PC 웹은 별도 제목 대신 최대 300자의 본문과 해시태그를 받습니다.
        parts = [metadata.get("title", "").strip(), metadata.get("content", "").strip()]
        tags = re.findall(r"#[\w가-힣]+", metadata.get("tags", ""))
        if len(tags) > NAVER_CLIP_MAX_HASHTAGS:
            self.logger.warning(f"네이버 클립 해시태그는 최대 {NAVER_CLIP_MAX_HASHTAGS}개라 앞의 {NAVER_CLIP_MAX_HASHTAGS}개만 넣어요.")
        parts.append(" ".join(tags[:NAVER_CLIP_MAX_HASHTAGS]))
        body = "\n\n".join(part for part in parts if part)
        if not body or len(body) > NAVER_CLIP_MAX_BODY_LENGTH:
            self.logger.error(
                f"네이버 클립 본문을 {NAVER_CLIP_MAX_BODY_LENGTH}자 이내로 입력해 주세요 "
                f"(현재 {len(body)}자)."
            )
            return None
        return body

    def _fill_body(self, page, body: str) -> bool:
        selectors = [
            "textarea#content-description",
            "textarea[name='description']",
            "textarea[placeholder*='본문']",
            "textarea[aria-label*='본문']",
            "[contenteditable='true'][data-placeholder*='본문']",
            "[contenteditable='true'][aria-label*='본문']",
            "textarea",
            "[contenteditable='true']",
        ]
        for selector in selectors:
            field = self._visible(page.locator(selector))
            if field is not None:
                field.fill(body)
                self.logger.info("네이버 클립 본문을 입력했어요.")
                return True
        self.logger.error("네이버 클립 본문 입력칸을 찾지 못했어요.")
        return False

    def _select_first_cover(self, page, timeout_seconds: int) -> bool:
        """업로드 타일을 건너뛰고 생성된 첫 번째 커버 사진을 선택합니다."""
        cover = page.locator(
            "div[class*='ClipDetailForm_coverStrip'] > "
            ":not([class*='coverUploadBtn']):not([class*='coverSkeleton']):not(input)"
        ).first
        try:
            cover.wait_for(state="visible", timeout=timeout_seconds * 1000)
            cover.scroll_into_view_if_needed()
            self._pause(page, "첫 번째 커버 사진 확인")
            cover.click()
            self._pause(page, "첫 번째 커버 사진 선택")
            self.logger.info("첫 번째 커버 사진을 선택했어요.")
            return True
        except Exception as error:
            self.logger.error(f"첫 번째 커버 사진을 선택하지 못했어요: {error}")
            return False

    def _enable_ai_label(self, page) -> bool:
        if not NAVER_CLIP_AI_LABEL_ENABLED:
            return True
        toggle = self._visible(page.get_by_role("switch", name="AI 활용 설정"))
        if toggle is None:
            self.logger.error("[AI 활용 설정] 토글을 찾지 못했어요.")
            return False
        toggle.scroll_into_view_if_needed()
        self._pause(page, "AI 활용 설정 확인")
        if toggle.get_attribute("aria-checked") != "true":
            toggle.click()
            self._pause(page, "AI 활용 설정 켜기")
        if toggle.get_attribute("aria-checked") != "true":
            self.logger.error("AI 활용 설정이 켜지지 않았어요.")
            return False
        self.logger.info("AI 활용 설정을 켰어요.")
        return True

    def _click_category_choice(self, page, name: str) -> bool:
        deadline = time.monotonic() + NAVER_CLIP_UI_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            for candidate in (
                page.get_by_role("option", name=name, exact=True),
                page.get_by_role("menuitem", name=name, exact=True),
                page.get_by_role("button", name=name, exact=True),
                page.get_by_text(name, exact=True),
            ):
                choice = self._visible(candidate)
                if choice is not None:
                    choice.click()
                    return True
            page.wait_for_timeout(NAVER_CLIP_POLL_INTERVAL_MS)
        return False

    @staticmethod
    def _category_selected(page, primary: str, secondary: str) -> bool:
        first = page.locator("button[class*='ClipDetailForm_dropdownPrimary']")
        second = page.locator("button[class*='ClipDetailForm_dropdownSecondary']")
        if first.count() == 0 or primary not in first.first.inner_text():
            return False
        return not secondary or (second.count() > 0 and secondary in second.first.inner_text())

    def _select_category(self, page, category: str) -> bool:
        primary, separator, secondary = category.partition(">")
        primary = primary.strip()
        secondary = secondary.strip()
        if not primary:
            self.logger.error("NAVER_CLIP_CATEGORY에 1차 카테고리를 입력해 주세요.")
            return False

        # 업로드 폼이 추천 카테고리를 제시하면 정확히 일치하는 항목을 먼저 사용합니다.
        for chip in page.locator("button[class*='ClipDetailForm_categoryTag']").all():
            if not chip.is_visible():
                continue
            labels = chip.locator("span[class*='categoryTagText']").all_text_contents()
            if labels and labels[0].strip() == primary and (
                (secondary and labels[-1].strip() == secondary)
                or (not secondary and labels[-1].strip() == primary)
            ):
                chip.click()
                if self._category_selected(page, primary, secondary):
                    self.logger.info(f"네이버 클립 추천 카테고리 [{category}]를 선택했어요.")
                    return True

        first = self._visible(page.get_by_role("button", name="1차 카테고리", exact=True))
        if first is None:
            self.logger.error("[1차 카테고리] 버튼을 찾지 못했어요.")
            return False
        first.click()
        if not self._click_category_choice(page, primary):
            self.logger.error(f"1차 카테고리 [{primary}]를 찾지 못했어요.")
            return False

        second = self._visible(page.get_by_role("button", name="2차 카테고리", exact=True))
        if second is not None and second.is_enabled():
            if not separator or not secondary:
                self.logger.error(
                    "2차 카테고리가 필요해요. NAVER_CLIP_CATEGORY를 "
                    "'1차>2차' 형식으로 설정해 주세요."
                )
                return False
            second.click()
            if not self._click_category_choice(page, secondary):
                self.logger.error(f"2차 카테고리 [{secondary}]를 찾지 못했어요.")
                return False
        if not self._category_selected(page, primary, secondary):
            self.logger.error(f"카테고리 [{category}] 선택 결과를 확인하지 못했어요.")
            return False
        self.logger.info(f"네이버 클립 카테고리 [{category}]를 선택했어요.")
        return True

    @staticmethod
    def _date_matches(value: str, scheduled_at: datetime) -> bool:
        numbers = re.findall(r"\d+", value)
        return len(numbers) >= 3 and tuple(map(int, numbers[:3])) == (
            scheduled_at.year, scheduled_at.month, scheduled_at.day
        )

    def _advance_calendar_month(self, page, scheduled_at: datetime) -> bool:
        """달력의 현재 월에서 목표 월까지 오른쪽 화살표로 이동합니다."""
        displayed = _get_calendar_displayed_month(page)
        if displayed is None:
            self.logger.warning("달력의 표시 월을 읽지 못해 공통 날짜 선택기로 계속 진행해요.")
            return True

        month_delta = (
            (scheduled_at.year - displayed["year"]) * 12
            + scheduled_at.month - displayed["month"]
        )
        if month_delta < 0:
            self.logger.error("예약 달력이 목표 월보다 뒤에 있어요. 이전 달 이동을 확인하지 못해 중단해요.")
            return False
        for _ in range(month_delta):
            previous_month = (displayed["year"], displayed["month"])
            expected_month = (
                previous_month[0] + (previous_month[1] // 12),
                previous_month[1] % 12 + 1,
            )
            next_button = self._visible(page.get_by_role(
                "button", name=re.compile(r"다음\s*달|다음\s*월|Next\s*month", re.I)
            ))
            if next_button is not None:
                next_button.click()
            else:
                clicked = page.evaluate(r"""() => {
                    const visible = el => {
                        const rect = el.getBoundingClientRect();
                        const style = getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 &&
                            style.visibility !== 'hidden' && style.display !== 'none';
                    };
                    const monthPattern = /^(\d{4})년\s*\d{1,2}월$|^\d{4}\.\s*\d{1,2}\.?$/;
                    const heading = Array.from(document.querySelectorAll('span, div, button'))
                        .filter(visible)
                        .find(el => monthPattern.test((el.textContent || '').trim()));
                    if (!heading) return false;
                    for (let parent = heading.parentElement; parent && parent !== document.body;
                         parent = parent.parentElement) {
                        const buttons = Array.from(parent.querySelectorAll('button')).filter(visible);
                        if (buttons.length < 2 || buttons.length > 4) continue;
                        const headingRight = heading.getBoundingClientRect().right;
                        const rightButtons = buttons.filter(button =>
                            button.getBoundingClientRect().left >= headingRight
                        );
                        if (rightButtons.length) {
                            rightButtons.sort((a, b) =>
                                a.getBoundingClientRect().left - b.getBoundingClientRect().left
                            );
                            rightButtons[0].click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if not clicked:
                    self.logger.error("예약 달력의 [>] 다음 달 버튼을 찾지 못했어요.")
                    return False
            self._pause(page, "예약 달력 다음 달로 이동")
            displayed = _get_calendar_displayed_month(page)
            if displayed is None or (displayed["year"], displayed["month"]) != expected_month:
                self.logger.error("[>] 버튼을 눌렀지만 달력이 다음 달로 이동하지 않았어요.")
                return False
        return True

    def _schedule_controls(self, page):
        date_pattern = re.compile(r"^\s*\d{4}\.\d{1,2}\.\d{1,2}\s*$")
        date_button = self._visible(
            page.locator("button:visible").filter(has_text=date_pattern)
        )
        if date_button is None:
            return None
        for ancestor in ("xpath=..", "xpath=../..", "xpath=../../..", "xpath=../../../.."):
            buttons = date_button.locator(ancestor).locator("button:visible").all()
            for index, button in enumerate(buttons):
                if not date_pattern.fullmatch(button.inner_text().strip()):
                    continue
                nearby = buttons[index + 1:index + 3]
                if len(nearby) == 2 and all(
                    re.fullmatch(r"\d{1,2}", item.inner_text().strip())
                    for item in nearby
                ):
                    return button, nearby[0], nearby[1]
        return None

    def _save_schedule_date(self, page) -> bool:
        """달력에서 선택한 날짜를 저장해 예약 폼에 반영합니다."""
        deadline = time.monotonic() + NAVER_CLIP_UI_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            save_button = self._visible(page.get_by_role("button", name="저장", exact=True))
            if save_button is not None and save_button.is_enabled() and (
                save_button.get_attribute("aria-disabled") != "true"
            ):
                save_button.click()
                self._pause(page, "예약 날짜 저장")
                self.logger.info("선택한 예약 날짜를 저장했어요.")
                return True
            page.wait_for_timeout(NAVER_CLIP_POLL_INTERVAL_MS)
        self.logger.error("예약 달력의 [저장] 버튼을 누르지 못했어요. 즉시 등록하지 않아요.")
        return False

    def _select_schedule_time(self, page, position: int, value: str, label: str) -> bool:
        buttons = self._schedule_controls(page)
        if buttons is None:
            self.logger.error("예약 날짜·시·분 선택 버튼을 찾지 못했어요.")
            return False
        trigger = buttons[position]
        if trigger.inner_text().strip() == value:
            self.logger.info(f"예약 {label}이(가) 이미 {value}(으)로 설정돼 있어요.")
            return True
        trigger.click()
        self._pause(page, f"예약 {label} 목록 열기")

        option = None
        for locator in (
            page.get_by_role("option", name=value, exact=True),
            page.get_by_role("menuitem", name=value, exact=True),
            page.locator("[role='listbox'] button").filter(has_text=re.compile(rf"^{re.escape(value)}$")),
        ):
            option = self._visible(locator)
            if option is not None:
                break
        if option is None:
            choices = page.get_by_text(value, exact=True)
            if choices.count() > 1:
                option = self._visible(choices.last)
        if option is None:
            self.logger.error(f"예약 {label} 목록에서 [{value}]를 찾지 못했어요.")
            return False
        option.click()
        self._pause(page, f"예약 {label} 선택")
        buttons = self._schedule_controls(page)
        return buttons is not None and buttons[position].inner_text().strip() == value

    def _set_schedule(self, page, scheduled_at: datetime) -> bool:
        if scheduled_at <= datetime.now() or scheduled_at - datetime.now() > timedelta(days=NAVER_CLIP_SCHEDULE_MAX_DAYS):
            self.logger.error(f"네이버 클립 등록 예약은 현재부터 {NAVER_CLIP_SCHEDULE_MAX_DAYS}일 이내만 가능해요.")
            return False

        schedule_label = self._visible(page.locator("label:has-text('등록 예약')"))
        if schedule_label is None:
            self.logger.error("[등록 예약] 항목을 찾지 못했어요. 즉시 등록하지 않아요.")
            return False
        schedule_label.scroll_into_view_if_needed()
        self._pause(page, "등록 예약 영역으로 스크롤")

        control = schedule_label.locator("input[type='checkbox']")
        if control.count() == 0:
            self.logger.error("등록 예약 체크박스를 찾지 못했어요.")
            return False
        if not control.first.is_checked():
            schedule_label.click()
        self._pause(page, "등록 예약 켜기")
        if not control.first.is_checked():
            self.logger.error("등록 예약 체크박스가 선택되지 않았어요.")
            return False

        buttons = self._schedule_controls(page)
        if buttons is None:
            self.logger.error("등록 예약 후 날짜·시·분 선택 버튼이 나타나지 않았어요.")
            return False
        date_button = buttons[0]
        if not self._date_matches(date_button.inner_text(), scheduled_at):
            date_button.click()
            self._pause(page, "예약 날짜 달력 열기")
            if not self._advance_calendar_month(page, scheduled_at):
                return False
            if not choose_calendar_date(page, scheduled_at, picker_already_open=True):
                self.logger.error("예약 달력에서 날짜를 선택하지 못했어요. 즉시 등록하지 않아요.")
                return False
            self._pause(page, "예약 날짜 선택")
            if not self._save_schedule_date(page):
                return False
        buttons = self._schedule_controls(page)
        if buttons is None or not self._date_matches(buttons[0].inner_text(), scheduled_at):
            self.logger.error("예약 날짜가 요청한 날짜와 달라요. 즉시 등록하지 않아요.")
            return False

        if not self._select_schedule_time(page, 1, f"{scheduled_at.hour:02d}", "시"):
            self.logger.error("예약 시각의 시를 선택하지 못했어요. 즉시 등록하지 않아요.")
            return False
        if not self._select_schedule_time(page, 2, f"{scheduled_at.minute:02d}", "분"):
            self.logger.error("예약 시각의 분을 선택하지 못했어요. 즉시 등록하지 않아요.")
            return False
        self.logger.info(f"네이버 클립 등록 예약 시각: {scheduled_at:%Y-%m-%d %H:%M}")
        return True

    def _submit(self, page, scheduled_at: datetime | None, timeout_seconds: int) -> bool:
        names = ("예약 등록", "예약하기", "등록") if scheduled_at else ("등록", "등록하기")
        button = self._visible(page.locator("form button[type='submit']"))
        for name in names:
            if button is not None:
                break
            button = self._visible(page.get_by_role("button", name=name, exact=True))
            if button is not None:
                break
        if button is None:
            self.logger.error("네이버 클립 등록 버튼을 찾지 못했어요.")
            return False
        deadline = time.monotonic() + timeout_seconds
        while (
            not button.is_enabled() or button.get_attribute("aria-disabled") == "true"
        ) and time.monotonic() < deadline:
            page.wait_for_timeout(NAVER_CLIP_POLL_INTERVAL_MS)
        if not button.is_enabled() or button.get_attribute("aria-disabled") == "true":
            self.logger.error("동영상 업로드를 기다렸지만 등록 버튼이 활성화되지 않았어요.")
            return False
        # 예약이면 '등록' 버튼이어도 예약 설정이 확인된 뒤에만 누릅니다.
        self._pause(page, "등록 전 입력 내용 확인")
        button.click()
        self.logger.info("등록 버튼을 눌렀어요. 완료 화면을 기다려요.")

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            completion_title = self._visible(page.get_by_text("등록 완료", exact=True))
            if completion_title is not None:
                confirm = self._visible(page.get_by_role("button", name="확인", exact=True))
                if confirm is not None and confirm.is_enabled():
                    self.logger.info("네이버 클립 등록 완료 화면을 10초 동안 보여줘요.")
                    page.wait_for_timeout(NAVER_CLIP_CONFIRM_DELAY_MS)
                    if not completion_title.is_visible():
                        self.logger.error("확인 버튼을 누르기 전에 등록 완료 화면이 닫혔어요.")
                        return False
                    confirm.click()
                    self.logger.info("등록 완료 화면에서 [확인]을 눌렀어요. 브라우저를 종료해요.")
                    return True
            visible_text = page.locator("body").inner_text(timeout=NAVER_CLIP_BODY_READ_TIMEOUT_MS)
            if any(message in visible_text for message in ("업로드 실패", "인코딩에 실패", "등록에 실패")):
                break
            page.wait_for_timeout(NAVER_CLIP_POLL_INTERVAL_MS)
        self.logger.error("네이버 클립 등록 완료를 확인하지 못했어요. 콘텐츠 목록을 확인해 주세요.")
        return False

    def upload(self, media_path: Path, metadata: dict) -> bool:
        if not media_path.is_file() or media_path.suffix.lower() not in VIDEO_EXTENSIONS:
            self.logger.error("네이버 클립 PC 웹에는 동영상 파일을 지정해 주세요.")
            return False

        scheduled_at = get_scheduled_at(metadata)
        body = self._make_body(metadata)
        if body is None:
            return False
        category = metadata.get("naver_category", NAVER_CLIP_CATEGORY)
        profile_dir = SESSION_DIR / "browser_naver"
        profile_dir.mkdir(parents=True, exist_ok=True)
        timeout_seconds = get_dynamic_upload_timeout(media_path)

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch_persistent_context(
                    str(profile_dir), headless=False, accept_downloads=True
                )
                try:
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    self.maximize_browser(page)
                    page.goto(
                        NAVER_CLIP_URL,
                        wait_until="domcontentloaded",
                        timeout=NAVER_CLIP_NAVIGATION_TIMEOUT_SECONDS * 1000,
                    )
                    if not self._wait_for_login(page) or not self._open_upload_form(page):
                        return False

                    video_input = page.locator("input[type='file']:not([accept*='image'])")
                    file_button = None
                    deadline = time.monotonic() + NAVER_CLIP_UI_TIMEOUT_SECONDS
                    while file_button is None and video_input.count() == 0 and time.monotonic() < deadline:
                        file_button = self._visible(
                            page.get_by_role("button", name="파일 선택", exact=True)
                        )
                        if file_button is None:
                            file_button = self._visible(page.get_by_text("파일 선택", exact=True))
                        if file_button is None and video_input.count() == 0:
                            page.wait_for_timeout(NAVER_CLIP_POLL_INTERVAL_MS)
                    if file_button is None:
                        file_button = self._visible(
                            page.get_by_role("button", name="파일 선택", exact=True)
                        )
                    if file_button is not None:
                        try:
                            with page.expect_file_chooser(timeout=NAVER_CLIP_UI_TIMEOUT_SECONDS * 1000) as chooser:
                                file_button.click()
                            chooser.value.set_files(str(media_path.resolve()))
                        except PlaywrightTimeoutError:
                            # 버튼이 숨겨진 파일 입력칸을 직접 사용하는 구현도 지원합니다.
                            video_input.first.set_input_files(str(media_path.resolve()))
                    else:
                        video_input.first.wait_for(
                            state="attached", timeout=NAVER_CLIP_UI_TIMEOUT_SECONDS * 1000
                        )
                        video_input.first.set_input_files(str(media_path.resolve()))
                    self.logger.info("네이버 클립 동영상 파일을 첨부했어요.")
                    self._pause(page, "동영상 파일 첨부")

                    body_field = page.locator("textarea:visible, [contenteditable='true']:visible")
                    body_field.first.wait_for(state="visible", timeout=timeout_seconds * 1000)
                    self._pause(page, "업로드 상세 정보 화면 확인")
                    if not self._fill_body(page, body):
                        return False
                    self._pause(page, "동영상 설명 입력")
                    if not self._select_first_cover(page, timeout_seconds):
                        self.save_result_screenshot(page, "cover_failed")
                        return False
                    if not self._select_category(page, category):
                        return False
                    self._pause(page, "카테고리 선택")
                    if not self._enable_ai_label(page):
                        self.save_result_screenshot(page, "ai_label_failed")
                        return False
                    if scheduled_at and not self._set_schedule(page, scheduled_at):
                        self.save_result_screenshot(page, "schedule_failed")
                        return False
                    success = self._submit(page, scheduled_at, timeout_seconds)
                    if success:
                        self.save_result_screenshot(page, "scheduled" if scheduled_at else "uploaded")
                    return success
                finally:
                    browser.close()
        except Exception as error:
            self.logger.error(f"네이버 클립 웹 업로드 중 문제가 생겼어요: {error}")
            return False
