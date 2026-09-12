import os
import time
from pathlib import Path
import requests
from platforms.base import BaseUploader
from platforms.scheduling import (
    get_scheduled_at,
)
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

class ThreadsUploader(BaseUploader):
    def __init__(self):
        super().__init__("Threads")
        self.access_token = CONFIG.get("META_ACCESS_TOKEN")
        self.threads_user_id = CONFIG.get("THREADS_USER_ID", "me")

    def _configure_native_schedule(self, page, scheduled_at) -> bool:
        """Threads 웹 작성 창의 자체 예약 기능을 설정합니다."""
        more_icons = page.locator(
            "svg[aria-label='더 보기'], "
            "svg[aria-label='More'], "
            "svg:has(title:text-is('더 보기')), "
            "svg:has(title:text-is('More'))"
        )
        if more_icons.count() == 0:
            self.logger.error("Threads [더 보기] 버튼을 찾지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False

        more_clicked = False
        for index in range(more_icons.count() - 1, -1, -1):
            more_icon = more_icons.nth(index)
            try:
                if not more_icon.is_visible():
                    continue

                # 실제 화면에서 aria-label은 SVG에 있고 클릭 이벤트는 바깥
                # role=button 요소에 걸려 있어요. SVG 중심을 누르면 두 구조를
                # 모두 처리하면서 중간 래퍼 div의 변화에도 영향을 받지 않아요.
                more_icon.scroll_into_view_if_needed()
                box = more_icon.bounding_box()
                if box:
                    page.mouse.click(
                        box["x"] + box["width"] / 2,
                        box["y"] + box["height"] / 2,
                    )
                else:
                    more_icon.click(force=True)
                more_clicked = True
                break
            except Exception:
                continue

        if not more_clicked:
            self.logger.error("Threads [더 보기] 버튼이 보이지만 클릭하지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False
        page.wait_for_timeout(500)

        if not self._click_threads_menu_item(page, ["예약...", "예약…", "Schedule...", "Schedule…"]):
            self.logger.error("Threads [예약...] 메뉴를 찾지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False
        page.wait_for_timeout(700)

        self.logger.info(f"Threads 예약 입력 시작: {scheduled_at:%Y-%m-%d %H:%M}")
        try:
            date_set = self._select_threads_calendar_date(page, scheduled_at)
        except Exception as error:
            self.logger.error(f"Threads 예약 날짜 처리 중 문제가 생겼어요: {error}")
            date_set = False
        try:
            time_set = self._fill_threads_schedule_time(page, scheduled_at)
        except Exception as error:
            self.logger.error(f"Threads 예약 시간 처리 중 문제가 생겼어요: {error}")
            time_set = False
        self.logger.info(
            f"Threads 예약 입력 결과 - 날짜: {'완료' if date_set else '실패'}, "
            f"시간: {'완료' if time_set else '실패'}"
        )
        if not date_set or not time_set:
            self.logger.error("Threads 예약 날짜 또는 시간을 입력하지 못했어요. 즉시 게시하지 않고 중단해요.")
            return False

        if not self._click_threads_menu_item(page, ["완료", "Done"]):
            self.logger.error("Threads 예약 달력의 [완료] 버튼을 찾지 못했어요.")
            return False
        page.wait_for_timeout(700)

        if self._get_threads_final_schedule_point(page) is None:
            self.logger.error("Threads 작성 창에 최종 [예약] 버튼이 나타나지 않았어요.")
            return False

        self.logger.info(f"Threads 자체 예약 설정 완료: {scheduled_at:%Y-%m-%d %H:%M}")
        return True

    def _click_threads_menu_item(self, page, labels: list[str]) -> bool:
        """보이는 Threads 메뉴/달력에서 정확한 문구의 클릭 요소를 누릅니다."""
        try:
            return page.evaluate("""(targetLabels) => {
                const elements = Array.from(document.querySelectorAll("button, [role='button'], [role='menuitem'], div, span"));
                const matches = [];
                const seen = new Set();
                for (const element of elements) {
                    const text = element.textContent ? element.textContent.trim() : '';
                    if (!targetLabels.includes(text)) continue;
                    const clickable = element.closest("button, [role='button'], [role='menuitem'], [tabindex='0']") || element;
                    if (seen.has(clickable)) continue;
                    const rect = clickable.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    seen.add(clickable);
                    const semantic = clickable.matches("button, [role='button'], [role='menuitem'], [tabindex='0']");
                    matches.push({ clickable, semantic, area: rect.width * rect.height });
                }
                if (matches.length === 0) return false;
                matches.sort((a, b) => Number(b.semantic) - Number(a.semantic) || a.area - b.area);
                matches[0].clickable.click();
                return true;
            }""", labels)
        except Exception:
            return False

    @staticmethod
    def _get_threads_final_schedule_point(page):
        """시계 아이콘과 예약 문구가 함께 있는 최종 버튼의 중심 좌표를 찾아요."""
        try:
            return page.evaluate(r"""() => {
                const visible = element => {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width > 0 && rect.height > 0 &&
                        style.display !== 'none' && style.visibility !== 'hidden';
                };
                const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
                const candidates = Array.from(document.querySelectorAll('div'))
                    .filter(label => ['예약', 'Schedule'].includes(normalize(label.textContent)))
                    .map(label => {
                        const content = label.parentElement;
                        if (!content || !content.querySelector('svg')) return null;
                        const clickable = content.closest(
                            'button, [role="button"], [tabindex="0"], [data-pressable-container="true"]'
                        ) || content;
                        if (!visible(clickable)) return null;
                        const rect = clickable.getBoundingClientRect();
                        const semantic = clickable.matches(
                            'button, [role="button"], [tabindex="0"], [data-pressable-container="true"]'
                        );
                        return {
                            x: rect.x + rect.width / 2,
                            y: rect.y + rect.height / 2,
                            semantic,
                            area: rect.width * rect.height,
                        };
                    })
                    .filter(Boolean)
                    .sort((a, b) => Number(b.semantic) - Number(a.semantic) || a.area - b.area);
                return candidates.length > 0 ? { x: candidates[0].x, y: candidates[0].y } : null;
            }""")
        except Exception:
            return None

    def _click_threads_final_schedule(self, page) -> bool:
        """날짜와 시간을 확정한 뒤 시계 아이콘이 있는 최종 예약 버튼을 눌러요."""
        point = self._get_threads_final_schedule_point(page)
        if point is None:
            return False
        try:
            page.mouse.click(point["x"], point["y"])
            return True
        except Exception:
            return False

    def _fill_threads_schedule_time(self, page, scheduled_at) -> bool:
        """Threads 달력 하단의 24시간제 시·분 입력을 설정합니다."""
        # Threads의 예약 달력은 작성 dialog 바깥의 포털에 렌더링돼요.
        # 따라서 dialog로 범위를 제한하지 않고 페이지 전체의 보이는 필드를 찾아요.
        hours = page.locator(
            "input[placeholder='hh'], "
            "[role='spinbutton'][aria-label*='hour' i], "
            "[role='spinbutton'][aria-label*='시'], "
            "input[aria-label*='hour' i], input[aria-label*='시']"
        )
        minutes = page.locator(
            "input[placeholder='mm'], "
            "[role='spinbutton'][aria-label*='minute' i], "
            "[role='spinbutton'][aria-label*='분'], "
            "input[aria-label*='minute' i], input[aria-label*='분']"
        )

        visible_hour = self._last_visible(hours)
        visible_minute = self._last_visible(minutes)
        if visible_hour is not None and visible_minute is not None:
            hour_set = self._replace_threads_time_value(
                visible_hour, f"{scheduled_at.hour:02d}"
            )
            minute_set = self._replace_threads_time_value(
                visible_minute, f"{scheduled_at.minute:02d}"
            )
            if hour_set and minute_set:
                page.wait_for_timeout(300)
                return True

        # aria-label이 없는 구현에서는 시와 분이 연속된 두 숫자 필드로 나와요.
        numeric_fields = page.locator(
            "input[role='spinbutton'], [contenteditable='true'][role='spinbutton'], "
            "input[inputmode='numeric']"
        )
        visible_numeric_fields = []
        for index in range(numeric_fields.count()):
            field = numeric_fields.nth(index)
            try:
                if field.is_visible():
                    visible_numeric_fields.append(field)
            except Exception:
                continue
        if len(visible_numeric_fields) >= 2:
            hour_set = self._replace_threads_time_value(
                visible_numeric_fields[-2], f"{scheduled_at.hour:02d}"
            )
            minute_set = self._replace_threads_time_value(
                visible_numeric_fields[-1], f"{scheduled_at.minute:02d}"
            )
            if hour_set and minute_set:
                page.wait_for_timeout(300)
                return True

        time_inputs = page.locator(
            "input[type='time'], input[name*='time' i], "
            "input[aria-label='시간'], input[aria-label='Time' i]"
        )
        for index in range(time_inputs.count() - 1, -1, -1):
            field = time_inputs.nth(index)
            try:
                if not field.is_visible():
                    continue
                field.fill(scheduled_at.strftime("%H:%M"))
                field.dispatch_event("input")
                field.dispatch_event("change")
                field.press("Tab")
                return True
            except Exception:
                continue

        # 현재 Threads UI는 13 : 00처럼 시와 분을 별도 텍스트 조각으로
        # 렌더링하기도 해요. 두 숫자의 실제 화면 좌표를 눌러 값을 입력해요.
        time_segments = page.evaluate(r"""() => {
            const visible = element => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0 && rect.height > 0 &&
                    style.display !== 'none' && style.visibility !== 'hidden';
            };
            const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
            const elements = Array.from(document.querySelectorAll('div, span, button'));
            const timeRoots = elements.filter(element =>
                /^\d{1,2}\s*:\s*\d{2}$/.test(normalize(element.textContent)) && visible(element)
            );
            timeRoots.sort((a, b) => {
                const ar = a.getBoundingClientRect();
                const br = b.getBoundingClientRect();
                return ar.width * ar.height - br.width * br.height;
            });

            for (const root of timeRoots) {
                const parts = Array.from(root.querySelectorAll('*'))
                    .filter(element => /^\d{1,2}$/.test(normalize(element.textContent)) && visible(element))
                    .map(element => {
                        const rect = element.getBoundingClientRect();
                        return {
                            x: rect.x + rect.width / 2,
                            y: rect.y + rect.height / 2,
                            left: rect.left,
                            area: rect.width * rect.height,
                        };
                    })
                    .sort((a, b) => a.left - b.left || a.area - b.area);
                const distinct = [];
                for (const part of parts) {
                    if (!distinct.some(item => Math.abs(item.x - part.x) < 2)) distinct.push(part);
                }
                if (distinct.length >= 2) return distinct.slice(0, 2);
            }
            return [];
        }""")
        if len(time_segments) >= 2:
            try:
                for segment, value in zip(
                    time_segments,
                    (f"{scheduled_at.hour:02d}", f"{scheduled_at.minute:02d}"),
                ):
                    page.mouse.click(segment["x"], segment["y"])
                    page.keyboard.press("Control+A")
                    page.keyboard.type(value)
                    page.wait_for_timeout(200)
                page.keyboard.press("Tab")
                page.wait_for_timeout(300)
                return True
            except Exception:
                pass

        self.logger.error("Threads 달력 하단의 시간 입력 항목을 찾지 못했어요.")
        return False

    def _select_threads_calendar_date(self, page, scheduled_at) -> bool:
        """Threads 날짜 grid에서 연·월·일이 일치하는 gridcell 자체를 눌러요."""
        date_grid = page.locator(
            "[role='grid'][aria-label='날짜 선택'], "
            "[role='grid'][aria-label*='date' i]"
        )
        visible_grid = self._last_visible(date_grid)
        if visible_grid is None:
            self.logger.error("Threads [날짜 선택] 그리드를 찾지 못했어요.")
            return False

        displayed_month = self._get_threads_calendar_month(page)
        if displayed_month is None:
            self.logger.error("Threads 달력의 표시 연월을 읽지 못했어요.")
            return False

        displayed_year, displayed_month_number = displayed_month
        self.logger.info(
            f"Threads 현재 달력: {displayed_year:04d}-{displayed_month_number:02d}, "
            f"목표 달력: {scheduled_at.year:04d}-{scheduled_at.month:02d}"
        )
        month_steps = (
            (scheduled_at.year - displayed_year) * 12
            + scheduled_at.month
            - displayed_month_number
        )
        month_button_label = "다음 달" if month_steps >= 0 else "지난달"
        english_button_label = "Next month" if month_steps >= 0 else "Previous month"
        direction = 1 if month_steps >= 0 else -1
        displayed_month_index = displayed_year * 12 + displayed_month_number - 1
        for step in range(abs(month_steps)):
            expected_month_index = displayed_month_index + direction * (step + 1)
            expected_year, zero_based_month = divmod(expected_month_index, 12)
            expected_month = zero_based_month + 1
            month_changed = self._click_threads_month_button(
                page,
                month_button_label,
                english_button_label,
                expected_year,
                expected_month,
            )
            if not month_changed:
                self.logger.error(
                    f"Threads 달력이 {expected_year}년 {expected_month}월로 바뀌지 않았어요."
                )
                return False

        final_displayed_month = self._get_threads_calendar_month(page)
        if final_displayed_month != (scheduled_at.year, scheduled_at.month):
            self.logger.error(
                f"Threads 달력 월 이동에 실패했어요: "
                f"목표 {scheduled_at.year}년 {scheduled_at.month}월"
            )
            return False

        target_prefix = f"{scheduled_at.year}년 {scheduled_at.month}월 {scheduled_at.day}일"
        visible_grid = self._last_visible(date_grid)
        if visible_grid is None:
            self.logger.error("Threads 월 이동 후 [날짜 선택] 그리드를 찾지 못했어요.")
            return False
        cells = visible_grid.locator("[role='gridcell']")
        for index in range(cells.count()):
            cell = cells.nth(index)
            try:
                if not cell.is_visible() or cell.get_attribute("aria-disabled") == "true":
                    continue
                cell_text = " ".join(cell.inner_text().split())
                if target_prefix not in cell_text:
                    continue

                cell.scroll_into_view_if_needed()
                cell_box = cell.bounding_box()
                if cell_box is None:
                    continue
                page.mouse.click(
                    cell_box["x"] + cell_box["width"] / 2,
                    cell_box["y"] + cell_box["height"] / 2,
                )
                page.wait_for_timeout(400)
                self.logger.info(f"Threads 예약 날짜 선택 완료: {scheduled_at:%Y-%m-%d}")
                return True
            except Exception:
                continue

        self.logger.error(f"Threads 예약 날짜 셀을 찾지 못했어요: {scheduled_at:%Y-%m-%d}")
        return False

    def _click_threads_month_button(
        self,
        page,
        korean_label: str,
        english_label: str,
        expected_year: int,
        expected_month: int,
    ) -> bool:
        """aria-label이 지정된 달력 월 이동 버튼을 누르고 제목 변경을 확인해요."""
        for label in (korean_label, english_label):
            month_buttons = page.get_by_role("button", name=label, exact=True)
            month_button = self._last_visible(month_buttons)
            if month_button is None:
                continue

            for click_method in ("playwright", "javascript", "keyboard"):
                try:
                    month_button = self._last_visible(
                        page.get_by_role("button", name=label, exact=True)
                    )
                    if month_button is None:
                        break
                    month_button.scroll_into_view_if_needed()
                    if click_method == "playwright":
                        month_button.click(timeout=3000)
                    elif click_method == "javascript":
                        month_button.evaluate("element => element.click()")
                    else:
                        month_button.focus()
                        month_button.press("Enter")

                    for _ in range(6):
                        page.wait_for_timeout(250)
                        if self._get_threads_calendar_month(page) == (
                            expected_year,
                            expected_month,
                        ):
                            self.logger.info(
                                f"Threads 달력 월 이동 완료: "
                                f"{expected_year:04d}-{expected_month:02d}"
                            )
                            return True
                except Exception:
                    continue
        return False

    @staticmethod
    def _get_threads_calendar_month(page):
        """현재 화면에 표시된 Threads 달력의 (연도, 월)를 읽어요."""
        try:
            result = page.evaluate(r"""() => {
                const visible = element => {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width > 0 && rect.height > 0 &&
                        style.display !== 'none' && style.visibility !== 'hidden';
                };
                const headings = Array.from(document.querySelectorAll('h2, span'));
                for (const heading of headings) {
                    if (!visible(heading)) continue;
                    const text = (heading.textContent || '').replace(/\s+/g, ' ').trim();
                    const match = text.match(/^(\d{4})년\s*(\d{1,2})월$/);
                    if (match) return { year: Number(match[1]), month: Number(match[2]) };
                }
                return null;
            }""")
            if result is None:
                return None
            return result["year"], result["month"]
        except Exception:
            return None

    @staticmethod
    def _last_visible(locator):
        """로케이터 중 화면에 보이는 마지막 요소를 반환해요."""
        for index in range(locator.count() - 1, -1, -1):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible():
                    return candidate
            except Exception:
                continue
        return None

    @staticmethod
    def _replace_threads_time_value(field, value: str) -> bool:
        """Threads의 input 또는 contenteditable 시간 조각 값을 교체해요."""
        try:
            field.click(force=True)
            field.press("Control+A")
            try:
                field.fill(value)
            except Exception:
                field.press_sequentially(value)
            field.dispatch_event("input")
            field.dispatch_event("change")
            field.press("Tab")
            return True
        except Exception:
            return False

    @staticmethod
    def _find_threads_composer(page):
        """다른 게시글 대화창을 제외하고 보이는 새 스레드 작성창만 찾아요."""
        dialogs = page.locator("div[role='dialog']")
        composer_titles = ("새로운 스레드", "새 스레드", "New thread")
        for index in range(dialogs.count() - 1, -1, -1):
            dialog = dialogs.nth(index)
            try:
                if not dialog.is_visible():
                    continue
                dialog_text = " ".join(dialog.inner_text().split())
                if not any(title in dialog_text for title in composer_titles):
                    continue
                editors = dialog.locator(
                    "div[role='textbox'], div[contenteditable='true'], input[type='file']"
                )
                if editors.count() > 0:
                    return dialog
            except Exception:
                continue

        # Threads가 작성창에 role=dialog를 부여하지 않는 UI도 처리해요.
        title_elements = page.locator(
            "h1:text-is('새로운 스레드'), h2:text-is('새로운 스레드'), "
            "h1:text-is('새 스레드'), h2:text-is('새 스레드'), "
            "h1:text-is('New thread'), h2:text-is('New thread'), "
            "div:text-is('새로운 스레드'), span:text-is('새로운 스레드'), "
            "div:text-is('새 스레드'), span:text-is('새 스레드'), "
            "div:text-is('New thread'), span:text-is('New thread')"
        )
        for index in range(title_elements.count() - 1, -1, -1):
            title = title_elements.nth(index)
            try:
                if not title.is_visible():
                    continue
                container = title.locator(
                    "xpath=ancestor::div[.//*[@role='textbox' or @contenteditable='true']][1]"
                )
                if container.count() == 0 or not container.first.is_visible():
                    continue
                return container.first
            except Exception:
                continue
        return None

    def _open_threads_composer(self, page):
        """피드 게시글을 건드리지 않고 Threads 새 게시물 작성창을 열어요."""
        composer = self._find_threads_composer(page)
        if composer is not None:
            return composer

        create_triggers = page.locator(
            "svg[aria-label='만들기'], svg[aria-label='Create']"
        )
        for index in range(create_triggers.count()):
            trigger = create_triggers.nth(index)
            try:
                if not trigger.is_visible():
                    continue
                click_target = trigger.locator(
                    "xpath=ancestor-or-self::*[self::button or @role='button' or @tabindex='0'][1]"
                )
                if click_target.count() == 0:
                    click_target = trigger
                else:
                    click_target = click_target.first

                unsafe_target = click_target.evaluate(r"""element => Boolean(
                    element.closest('article, [role="article"], div[role="dialog"]') ||
                    element.closest('a[href*="/post/"], a[href*="/t/"]')
                )""")
                if unsafe_target:
                    self.logger.warning("Threads 피드 게시글 안의 요소는 작성 버튼 후보에서 제외했어요.")
                    continue

                click_target.scroll_into_view_if_needed()
                box = click_target.bounding_box()
                if box:
                    page.mouse.click(
                        box["x"] + box["width"] / 2,
                        box["y"] + box["height"] / 2,
                    )
                else:
                    click_target.click(force=True)

                for _ in range(10):
                    page.wait_for_timeout(300)
                    composer = self._find_threads_composer(page)
                    if composer is not None:
                        self.logger.info("Threads 새 게시물 작성창을 확인했어요.")
                        return composer
            except Exception:
                continue

        self.logger.error("Threads 새 게시물 작성창을 열지 못했어요. 피드에서는 아무것도 업로드하지 않아요.")
        return None

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
            scheduled_at = get_scheduled_at(metadata)

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
                
                composer = self._open_threads_composer(page)
                if composer is None:
                    browser.close()
                    return False

                # 1. 모달 내부 파일 먼저 첨부
                self.logger.info(f"1단계: {media_type.upper()} 파일({media_path.name}) 첨부 중...")
                file_input = composer.locator("input[type='file']")
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
                textbox = composer.locator("div[role='textbox'], div[contenteditable='true']")
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

                        # 2) 해시태그 입력 (스레드는 여러 태그 중 첫 번째 태그만 적용) 및 추천값 선택
                        if tags_raw:
                            tag_list = [t.strip().lstrip("#") for t in tags_raw.split() if t.strip()]
                            if tag_list:
                                t = tag_list[0]  # 첫 번째 태그만 사용
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(200)
                                
                                # #태그 타이핑
                                self.logger.info(f"Threads 태그 타이핑 (첫 번째 태그만 적용): #{t}")
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

                if scheduled_at and not self._configure_native_schedule(page, scheduled_at):
                    browser.close()
                    return False

                # 3. 우측 하단 [게시]/[예약] 버튼 클릭
                action_name = "예약" if scheduled_at else "게시"
                self.logger.info(f"모달 [{action_name}] 버튼 클릭 시도...")
                page.wait_for_timeout(1000)



                if scheduled_at:
                    final_clicked = self._click_threads_final_schedule(page)
                else:
                    final_clicked = self._click_threads_menu_item(page, ["게시", "Post"])
                if not final_clicked:
                    self.logger.error(f"Threads 최종 [{action_name}] 버튼을 찾지 못했어요.")
                    browser.close()
                    return False

                self.logger.info(f"게시 요청 전송 완료. 서버 처리 및 완료 대기 중 (최대 {upload_timeout}초)...")
                page.wait_for_timeout(3000)
                
                # 게시 완료 상태 확인 (최대 upload_timeout초)
                post_done = False
                for wait_i in range(upload_timeout):
                    page.wait_for_timeout(1000)
                    
                    # 1) '게시되었습니다' 토스트 확인
                    toast = page.locator(
                        "div:has-text('게시되었습니다'), div:has-text('Posted'), span:has-text('게시되었습니다'), "
                        "div:has-text('예약되었습니다'), div:has-text('Scheduled'), span:has-text('예약되었습니다')"
                    )
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
                    result_name = "예약 등록" if scheduled_at else "업로드"
                    self.logger.info(f"🎉 Threads 최종 {result_name} 완료!")
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



