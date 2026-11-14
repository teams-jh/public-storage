"""기존 YouTube 브라우저 세션으로 이미지 게시글을 작성합니다."""

import re
from datetime import datetime
from pathlib import Path

from config import LOGIN_TIMEOUT_SECONDS, SESSION_DIR, UPLOAD_TIMEOUT_SECONDS
from image_selection import set_and_verify_images
from platforms.base import BaseUploader
from upload_pause import upload_monotonic


def _visible(locator):
    """선택자에 맞는 요소 중 화면에 보이는 첫 요소를 찾습니다."""
    for index in range(locator.count()):
        candidate = locator.nth(index)
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            continue
    return None


class YouTubeImagePostUploader(BaseUploader):
    def __init__(self):
        super().__init__("YouTube 게시글")

    def _wait_visible(self, page, selector: str, timeout_seconds: int):
        deadline = upload_monotonic() + timeout_seconds
        while upload_monotonic() < deadline:
            target = _visible(page.locator(selector))
            if target is not None:
                return target
            page.wait_for_timeout(500)
        return None

    def _composer(self, page):
        candidates = page.locator(
            "ytd-backstage-post-dialog-renderer, "
            "ytd-backstage-post-creation-renderer, "
            "ytcp-post-dialog, "
            "tp-yt-paper-dialog, "
            "[role='dialog']"
        )
        for index in range(candidates.count()):
            candidate = candidates.nth(index)
            try:
                if candidate.is_visible() and candidate.locator("[contenteditable='true']").count():
                    return candidate
            except Exception:
                continue
        return None

    def _open_composer(self, page):
        create_button = self._wait_visible(
            page,
            "button[aria-label='만들기'], button[aria-label='Create'], "
            "button[aria-label='만들기:'], button[aria-label='Create:'], "
            "ytd-topbar-menu-button-renderer button[aria-label*='만들기'], "
            "ytd-topbar-menu-button-renderer button[aria-label*='Create']",
            LOGIN_TIMEOUT_SECONDS,
        )
        if create_button is None:
            raise RuntimeError("YouTube 로그인을 확인하지 못했어요. 브라우저에서 로그인해 주세요.")
        create_button.click()

        create_post = self._wait_visible(
            page,
            "ytd-menu-service-item-renderer:has-text('게시물 작성'), "
            "ytd-menu-service-item-renderer:has-text('Create post'), "
            "tp-yt-paper-item:has-text('게시물 작성'), "
            "tp-yt-paper-item:has-text('Create post'), "
            "[role='menuitem']:has-text('게시물 작성'), "
            "[role='menuitem']:has-text('Create post')",
            LOGIN_TIMEOUT_SECONDS,
        )
        if create_post is None:
            raise RuntimeError("'게시물 작성' 메뉴를 찾지 못했어요. 채널의 게시글 사용 권한을 확인해 주세요.")
        create_post.click()

        deadline = upload_monotonic() + LOGIN_TIMEOUT_SECONDS
        while upload_monotonic() < deadline:
            composer = self._composer(page)
            if composer is not None:
                return composer
            page.wait_for_timeout(500)
        raise RuntimeError("YouTube 게시글 작성창이 열리지 않았어요.")

    def _image_button(self, page, composer):
        """정확한 이미지 문구에서 바깥의 클릭 대상까지 찾아요."""
        name = re.compile(r"^\s*(?:이미지(?: 추가)?|(?:Add )?Image)\s*$", re.IGNORECASE)
        deadline = upload_monotonic() + LOGIN_TIMEOUT_SECONDS
        while upload_monotonic() < deadline:
            button = _visible(composer.locator("#image-button button"))
            if button is not None:
                return button
            button = _visible(composer.get_by_role("button", name=name))
            if button is not None:
                return button
            # 터치 효과 div는 여러 버튼에 공통으로 있어요. '이미지' 문구로
            # 범위를 정한 뒤 효과 요소를 포함하는 가장 가까운 래퍼를 찾아요.
            labels = composer.get_by_text(name, exact=True)
            button = _visible(labels.locator(
                "xpath=ancestor-or-self::*[self::button or @role='button' "
                "or self::yt-button-shape or self::ytd-button-renderer "
                "or .//*[contains(concat(' ', normalize-space(@class), ' '), "
                "' ytSpecTouchFeedbackShapeFill ')]][1]"
            ))
            if button is not None:
                return button
            # 숨겨진 첫 요소에 대기하지 않고 보이는 후보들을 매번 확인해요.
            page.wait_for_timeout(500)
        raise RuntimeError("이미지 추가 버튼을 찾지 못했어요. 게시글 작성창을 확인해 주세요.")

    def _attach_images(self, page, composer, images: list[Path]) -> None:
        # 숨겨진 input이 미리 있어도 이미지 모드를 먼저 열어야 해요.
        image_button = self._image_button(page, composer)
        self.logger.info("이미지 버튼을 찾았어요. 이미지 선택창을 열고 있어요.")
        image_button.scroll_into_view_if_needed()
        image_button.click()
        # 같은 작성창에 숨겨진 추가용 input도 있어요. 열린 이미지 선택창의
        # 여러 장 선택용 input만 사용해서 다른 입력창에 파일을 넣지 않아요.
        image_select = composer.locator("#image-select")
        image_select.wait_for(state="visible", timeout=UPLOAD_TIMEOUT_SECONDS * 1000)
        file_input = image_select.locator("input[type='file'][accept*='image'][multiple]")
        file_input.first.wait_for(state="attached", timeout=UPLOAD_TIMEOUT_SECONDS * 1000)

        target = file_input.first
        if len(images) > 1 and target.get_attribute("multiple") is None:
            raise RuntimeError("현재 YouTube 이미지 선택창이 여러 장 첨부를 지원하지 않아요.")
        set_and_verify_images(target, images)
        self.logger.info("이미지 파일을 전달했어요. 작성창의 첨부 완료를 확인하고 있어요.")
        self._wait_images_ready(page, composer, images)

    def _wait_images_ready(self, page, composer, images: list[Path]) -> None:
        """파일 선택 이벤트와 별개로 작성창의 이미지 로딩 완료를 확인해요."""
        deadline = upload_monotonic() + UPLOAD_TIMEOUT_SECONDS
        while upload_monotonic() < deadline:
            ready_images = composer.locator(
                "#image-select #thumbnail-drag-drop-area img, "
                "ytd-backstage-image-renderer img, "
                "ytd-backstage-image-upload-renderer img, "
                "#attachment-preview img"
            ).evaluate_all("""elements => elements.filter(image =>
                image.getClientRects().length && image.complete && image.naturalWidth > 0
            ).length""")
            post_button = self._post_button(composer)
            processing = _visible(composer.locator(
                "[role='progressbar'], tp-yt-paper-spinner[active], "
                "tp-yt-paper-spinner-lite[active]"
            ))
            if (ready_images >= len(images) and processing is None and post_button is not None
                    and post_button.is_enabled() and post_button.get_attribute("aria-disabled") != "true"):
                self.logger.info("이미지 %s장의 첨부를 확인했어요.", len(images))
                return
            page.wait_for_timeout(500)
        raise RuntimeError("작성창에서 이미지 첨부 완료를 확인하지 못했어요. 이미지를 확인한 뒤 다시 시도해 주세요.")

    def _post_button(self, composer):
        button = _visible(composer.locator("#submit-button button, #post-button button"))
        if button is not None:
            return button
        buttons = composer.locator("button, [role='button']")
        for index in range(buttons.count()):
            button = buttons.nth(index)
            try:
                if button.is_visible() and re.fullmatch(
                    r"게시|Post", button.inner_text().strip(), re.IGNORECASE
                ):
                    return button
            except Exception:
                continue
        return None

    def _schedule_control(self, scope, kind):
        """입력칸과 드롭다운의 현재 날짜/시간 문구로 컨트롤을 찾아요."""
        control = _visible(scope.locator("#date-picker" if kind == "date" else "#time-picker"))
        if control is not None:
            return control
        controls = scope.locator(
            "input, button, [role='button'], [role='combobox'], "
            "tp-yt-paper-dropdown-menu, tp-yt-paper-input, "
            "#datepicker-trigger, #date-picker-trigger"
        )
        for index in range(controls.count()):
            control = controls.nth(index)
            if not control.is_visible():
                continue
            value = " ".join(control.evaluate("el => el.value || el.innerText || ''").split())
            hint = " ".join(control.get_attribute(attr) or "" for attr in ("type", "name", "id", "aria-label"))
            if re.search(r"timezone|time-zone|시간대|GMT|UTC", hint + value, re.IGNORECASE):
                continue
            if kind == "date":
                matches = re.search(r"date|날짜", hint, re.IGNORECASE) or re.fullmatch(
                    r"(?:[A-Za-z]+ \d{1,2}, \d{4}|\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2}[.일]?)", value
                )
            else:
                matches = re.search(r"time|시간", hint, re.IGNORECASE) or re.fullmatch(
                    r"(?:(?:오전|오후)\s*)?\d{1,2}:\d{2}\s*(?:AM|PM)?", value, re.IGNORECASE
                )
            if matches:
                return control
        return None

    def _choose_post_date(self, page, trigger, scheduled_at):
        """게시글 달력이 열린 뒤 상단 날짜 입력칸에 날짜를 직접 넣어요."""
        trigger.click()
        deadline = upload_monotonic() + LOGIN_TIMEOUT_SECONDS
        while upload_monotonic() < deadline:
            # 팝업은 작성창 밖에 붙고 dialog 역할이 없을 수도 있어요.
            # 표시된 값으로 날짜 입력칸만 골라 시간 입력칸을 제외해요.
            inputs = page.locator("input")
            for index in range(inputs.count()):
                field = inputs.nth(index)
                if not field.is_visible() or not field.is_editable():
                    continue
                value = field.input_value().strip()
                hint = " ".join(field.get_attribute(attr) or "" for attr in ("type", "aria-label", "placeholder"))
                if not (re.search(r"date|날짜", hint, re.IGNORECASE) or re.fullmatch(
                    r"[A-Za-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2}", value
                )):
                    continue
                target = scheduled_at.strftime("%Y-%m-%d")
                if re.search(r"[A-Za-z]", value):
                    target = page.evaluate("s => new Date(s + 'T00:00:00').toLocaleDateString('en-US', {month:'short',day:'numeric',year:'numeric'})", target)
                field.fill(target)
                field.press("Enter")
                self.logger.info("달력 상단 입력칸에 예약 날짜를 입력했어요: %s", target)
                return

            page.wait_for_timeout(500)
        raise RuntimeError("예약 달력에서 날짜를 선택하지 못했어요. 실패 화면을 확인해 주세요.")

    def _fill_schedule_panel(self, page, panel, scheduled_at):
        date = self._schedule_control(panel, "date")
        time = self._schedule_control(panel, "time")
        if date is None or time is None:
            raise RuntimeError("예약 날짜와 시간 선택칸을 찾지 못했어요.")
        date.scroll_into_view_if_needed()
        if date.evaluate("el => el.tagName === 'INPUT' && !el.readOnly"):
            current = date.input_value()
            value = scheduled_at.strftime("%Y-%m-%d")
            if re.search(r"[A-Za-z]", current):
                value = page.evaluate("value => new Date(value + 'T00:00:00').toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'})", value)
            date.fill(value)
            date.press("Tab")
        else:
            self._choose_post_date(page, date, scheduled_at)

        # 날짜 선택으로 예약 패널이 다시 그려질 수 있어요.
        date = self._schedule_control(panel, "date")
        time = self._schedule_control(panel, "time")
        if date is None or time is None:
            raise RuntimeError("날짜 선택 후 예약 입력칸을 확인하지 못했어요.")
        time.scroll_into_view_if_needed()
        current = time.evaluate("el => el.value || el.innerText || ''").strip()
        time_value = scheduled_at.strftime("%H:%M")
        if re.search(r"AM|PM", current, re.IGNORECASE):
            time_value = scheduled_at.strftime("%I:%M%p").lstrip("0")
        elif "오전" in current or "오후" in current:
            time_value = scheduled_at.strftime("%I:%M").lstrip("0")
            time_value = ("오후 " if scheduled_at.strftime("%p") == "PM" else "오전 ") + time_value
        if not time.evaluate("el => el.tagName === 'INPUT' && !el.readOnly"):
            time.click()
            # 실제 항목은 '7:00\u202fPM'처럼 좁은 줄바꿈 방지 공백을 포함해요.
            # 시간 목록 안에서만 찾고 화면 밖 항목은 스크롤한 뒤 클릭해요.
            pattern = re.compile(r"^\s*" + r"\s*".join(
                re.escape(part) for part in re.findall(r"\d+:\d+|AM|PM|오전|오후", time_value)
            ) + r"\s*$", re.IGNORECASE)
            listbox = panel.locator("#time-listbox")
            if listbox.count():
                listbox.wait_for(state="visible", timeout=LOGIN_TIMEOUT_SECONDS * 1000)
                option = listbox.get_by_role("option", name=pattern)
                if option.count() != 1:
                    raise RuntimeError(f"시간 목록에 {time_value} 항목이 없어요. 목록에서 지원하는 예약 시간을 지정해 주세요.")
            else:
                option = page.get_by_role("option", name=pattern)
                option.first.wait_for(state="visible", timeout=LOGIN_TIMEOUT_SECONDS * 1000)
            option = option.first
            option.scroll_into_view_if_needed()
            option.click()
            from playwright.sync_api import expect
            expect(time).to_have_text(pattern, timeout=LOGIN_TIMEOUT_SECONDS * 1000)
        else:
            time.fill(time_value)
            time.press("Tab")

        # 기본값이 남아 있는데 예약하는 일을 막기 위해 입력 후 값을 다시 읽어요.
        deadline = upload_monotonic() + LOGIN_TIMEOUT_SECONDS
        selected_date = None
        while upload_monotonic() < deadline:
            date = self._schedule_control(panel, "date")
            if date is not None:
                selected_date = date.evaluate("""el => {
                    let value = (el.value || el.innerText || '').trim();
                    value = value.replace(/년|월/g, '-').replace(/일/g, '').replace(/\\s+/g, ' ').trim();
                    let parsed = new Date(value);
                    return [parsed.getFullYear(), parsed.getMonth() + 1, parsed.getDate()];
                }""")
                if selected_date == [scheduled_at.year, scheduled_at.month, scheduled_at.day]:
                    break
            page.wait_for_timeout(500)
        selected_time = time.evaluate("el => el.value || el.innerText || ''").strip()
        normalized_time = selected_time.replace("오전", "AM").replace("오후", "PM")
        normalized_time = re.sub(r"^(AM|PM)\s*(.*)$", r"\2\1", normalized_time)
        normalized_time = re.sub(r"\s+", "", normalized_time).upper()
        try:
            parsed_time = datetime.strptime(normalized_time, "%I:%M%p" if re.search(r"AM|PM", normalized_time) else "%H:%M")
        except ValueError:
            raise RuntimeError("예약 시간의 입력 결과를 확인하지 못했어요.")
        if selected_date != [scheduled_at.year, scheduled_at.month, scheduled_at.day] or (
                parsed_time.hour, parsed_time.minute) != (scheduled_at.hour, scheduled_at.minute):
            raise RuntimeError("요청한 예약 날짜·시간과 화면의 값이 달라요. 예약을 진행하지 않았어요.")
        self.logger.info("예약 날짜·시간을 확인했어요: %s", scheduled_at.strftime("%Y-%m-%d %H:%M"))

    def _schedule(self, page, composer, scheduled_at) -> None:
        panel = _visible(composer.locator("#scheduling-panel"))
        if panel is not None and self._schedule_control(panel, "date") is not None:
            self._submit_schedule(page, composer, panel, scheduled_at)
            return
        post_button = self._post_button(composer)
        if post_button is None:
            raise RuntimeError("게시글 예약 메뉴를 찾지 못했어요.")

        dropdown = _visible(composer.locator("#option-menu #button-shape button"))
        if dropdown is None:
            dropdown = _visible(post_button.locator("xpath=following-sibling::button[1]"))
        if dropdown is None:
            dropdown = _visible(composer.locator(
            "button[aria-label*='게시물 예약'], button[aria-label*='Schedule post'], "
            "button[aria-label*='예약 옵션'], button[aria-label*='Schedule options'], "
            "button[aria-haspopup='menu']"
            ))
        if dropdown is None:
            # 새 UI는 게시 버튼과 화살표 버튼을 서로 다른 래퍼에 넣어요.
            group = post_button.locator("xpath=ancestor::*[count(.//button) > 1][1]")
            candidates = group.locator("button")
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if (candidate.is_visible() and candidate.is_enabled()
                        and not candidate.inner_text().strip()
                        and candidate.locator("svg, yt-icon").count()):
                    dropdown = candidate
                    break
        if dropdown is None or dropdown.evaluate(
            "(element, postButton) => element === postButton", post_button.element_handle()
        ):
            raise RuntimeError("게시 버튼 옆의 예약 메뉴를 찾지 못했어요.")
        dropdown.click()

        schedule_option = self._wait_visible(
            page,
            "[role='menuitem']:has-text('게시물 예약'), "
            "[role='menuitem']:has-text('Schedule post'), "
            "tp-yt-paper-item:has-text('게시물 예약'), "
            "tp-yt-paper-item:has-text('Schedule post')",
            10,
        )
        if schedule_option is None:
            raise RuntimeError("'게시물 예약' 메뉴를 찾지 못했어요.")
        schedule_option.click()

        schedule_dialog = None
        deadline = upload_monotonic() + LOGIN_TIMEOUT_SECONDS
        while upload_monotonic() < deadline and schedule_dialog is None:
            dialogs = page.locator("#scheduling-panel, [role='dialog'], tp-yt-paper-dialog")
            for index in reversed(range(dialogs.count())):
                candidate = dialogs.nth(index)
                if candidate.is_visible() and self._schedule_control(candidate, "date") is not None:
                    schedule_dialog = candidate
                    break
            if schedule_dialog is None:
                page.wait_for_timeout(500)
        if schedule_dialog is None:
            raise RuntimeError("게시글 예약 날짜와 시간을 입력하지 못했어요.")

        self._submit_schedule(page, composer, schedule_dialog, scheduled_at)

    def _submit_schedule(self, page, composer, panel, scheduled_at):
        self._fill_schedule_panel(page, panel, scheduled_at)
        # 인라인 패널의 예약 버튼은 날짜 패널 위, 작성창 안에 있어요.
        # text-is는 중첩된 span의 문구를 button의 직접 텍스트로 보지 않아요.
        # 실제 제출 영역과 접근성 이름으로 찾고 활성화를 기다려요.
        name = re.compile(r"^\s*(?:예약|Schedule)\s*$", re.IGNORECASE)
        buttons = composer.locator("#submit-button").get_by_role("button", name=name)
        if buttons.count() == 0:
            buttons = composer.get_by_role("button", name=name)
        if buttons.count() == 0:
            buttons = panel.get_by_role("button", name=name)
        if buttons.count() == 0:
            raise RuntimeError("게시글 예약 버튼을 사용할 수 없어요.")
        schedule_button = buttons.first
        # 날짜·시간 변경 후 버튼 활성화까지 비동기로 반영될 수 있어요.
        schedule_button.scroll_into_view_if_needed()
        schedule_button.click(timeout=UPLOAD_TIMEOUT_SECONDS * 1000)
        self.logger.info("최종 예약 버튼을 눌렀어요. 예약 완료 화면을 확인하고 있어요.")

    def _publish(self, page, composer) -> None:
        post_button = self._post_button(composer)
        if post_button is None:
            raise RuntimeError("게시글의 '게시' 버튼을 찾지 못했어요.")
        deadline = upload_monotonic() + UPLOAD_TIMEOUT_SECONDS
        while upload_monotonic() < deadline:
            if post_button.is_enabled() and post_button.get_attribute("aria-disabled") != "true":
                post_button.click()
                return
            page.wait_for_timeout(500)
        raise RuntimeError("이미지 처리가 끝나지 않아 게시 버튼이 활성화되지 않았어요.")

    def upload(self, images: list[Path], metadata: dict) -> bool:
        """이미지를 하나의 YouTube 게시글로 올리거나 예약합니다."""
        if len(images) > 10:
            raise ValueError("YouTube 게시글에는 이미지를 최대 10장까지 넣을 수 있어요.")
        for image in images:
            if image.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                raise ValueError(f"YouTube가 지원하지 않는 이미지 형식이에요: {image.name}")
            if image.stat().st_size > 16 * 1024 * 1024:
                raise ValueError(f"YouTube의 16MB 크기 제한을 넘었어요: {image.name}")

        from playwright.sync_api import sync_playwright

        session_dir = SESSION_DIR / "browser_youtube"
        session_dir.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=False,
                no_viewport=True,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            )
            try:
                page = browser.new_page()
                self.maximize_browser(page)
                page.goto("https://www.youtube.com/", wait_until="domcontentloaded", timeout=60000)
                composer = self._open_composer(page)
                # 초기 화면의 commentbox는 hidden 상태예요. 이미지 버튼으로
                # 작성창을 펼치고 첨부한 뒤 본문 입력칸을 찾아요.
                self._attach_images(page, composer, images)
                caption = metadata.get("full_caption", "").strip()
                editor = _visible(composer.locator("[contenteditable='true']"))
                if editor is None:
                    raise RuntimeError("게시글 입력칸을 찾지 못했어요.")
                if caption:
                    editor.fill(caption)

                scheduled_at = metadata.get("scheduled_at")
                if scheduled_at:
                    self._schedule(page, composer, scheduled_at)
                else:
                    self._publish(page, composer)

                deadline = upload_monotonic() + UPLOAD_TIMEOUT_SECONDS
                while upload_monotonic() < deadline:
                    if not composer.is_visible() or (
                        _visible(composer.locator("#unopened-dialog")) is not None
                        and _visible(composer.locator("[contenteditable='true']")) is None
                    ):
                        self.logger.info("YouTube 게시글 작성이 끝나 작성창이 닫히거나 초기화됐어요.")
                        self.save_result_screenshot(page, "scheduled" if scheduled_at else "uploaded")
                        return True
                    page.wait_for_timeout(500)
                self.logger.error("게시글 완료 화면을 확인하지 못했어요. 중복 게시를 피하려면 먼저 채널에서 확인해 주세요.")
                return False
            except Exception as exc:
                self.logger.error(f"YouTube 이미지 게시글 업로드 실패: {exc}")
                screenshot = self.save_result_screenshot(page, "failed")
                if screenshot is not None:
                    try:
                        screenshot.with_suffix(".html").write_text(page.content(), encoding="utf-8")
                        self.logger.info("실패 화면과 HTML을 저장했어요: %s", screenshot)
                    except Exception as diagnostic_error:
                        self.logger.warning("실패 HTML을 저장하지 못했어요: %s", diagnostic_error)
                return False
            finally:
                browser.close()
