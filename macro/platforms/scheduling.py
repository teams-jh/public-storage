import re
from datetime import datetime

from config import parse_scheduled_time


def get_scheduled_at(metadata: dict) -> datetime | None:
    """검증된 예약 시각을 가져오며, 업로더 단독 호출 시에도 [TIME]을 파싱합니다."""
    scheduled_at = metadata.get("scheduled_at")
    if isinstance(scheduled_at, datetime):
        return scheduled_at if scheduled_at > datetime.now() else None

    scheduled_time_text = metadata.get("time", "")
    try:
        scheduled_at = parse_scheduled_time(scheduled_time_text)
    except ValueError:
        return None
    return scheduled_at if scheduled_at and scheduled_at > datetime.now() else None


def _fill_visible(locator, value: str) -> bool:
    """첫 번째 보이는 입력 요소에 값을 채웁니다."""
    for index in range(locator.count()):
        target = locator.nth(index)
        try:
            if target.is_visible():
                target.fill(value)
                target.dispatch_event("input")
                target.dispatch_event("change")
                return True
        except Exception:
            continue
    return False


def fill_native_date_time(scope, scheduled_at: datetime) -> bool:
    """예약 화면의 네이티브 date/time 입력을 채웁니다."""
    date_filled = _fill_visible(
        scope.locator("input[type='date'], input[name*='date' i], input[aria-label*='날짜'], input[aria-label*='date' i]"),
        scheduled_at.strftime("%Y-%m-%d"),
    )
    time_filled = _fill_visible(
        scope.locator("input[type='time'], input[name*='time' i], input[aria-label*='시간'], input[aria-label*='time' i]"),
        scheduled_at.strftime("%H:%M"),
    )
    return date_filled and time_filled


def choose_calendar_date(page, scheduled_at: datetime, picker_already_open: bool = False) -> bool:
    """라벨 기반 날짜 선택기를 열고 원하는 날짜를 선택합니다."""
    if not picker_already_open:
        trigger_candidates = page.locator(
            "div[role='button'][aria-haspopup='dialog'][aria-expanded][tabindex='0'], "
            "button[aria-label*='날짜'], button[aria-label*='date' i], "
            "div[role='button'][aria-label*='날짜'], div[role='button'][aria-label*='date' i], "
            "ytcp-datetime-picker #datepicker-trigger, "
            "ytcp-datetime-picker #datepicker-trigger ytcp-dropdown-trigger[role='button']"
        )
        date_trigger = None
        date_text_pattern = re.compile(
            r"(?:\d{4}년\s*\d{1,2}월\s*\d{1,2}일|\d{4}-\d{1,2}-\d{1,2}|"
            r"\d{1,2}/\d{1,2}/\d{4}|\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.)"
        )

        for index in range(trigger_candidates.count()):
            candidate = trigger_candidates.nth(index)
            try:
                candidate_text = " ".join(candidate.inner_text().split())
                aria_label = candidate.get_attribute("aria-label") or ""
                if candidate.is_visible() and (
                    date_text_pattern.search(candidate_text)
                    or "날짜" in aria_label
                    or "date" in aria_label.lower()
                ):
                    date_trigger = candidate
                    break
            except Exception:
                continue

        if date_trigger is None:
            labels = page.locator(
                "label:text-is('날짜'), label:text-is('Date'), div:text-is('날짜'), div:text-is('Date'), "
                "span:text-is('날짜'), span:text-is('Date')"
            )
            for index in range(labels.count()):
                label = labels.nth(index)
                try:
                    if not label.is_visible():
                        continue
                    candidate = label.locator("xpath=following::*[self::button or @role='button'][1]")
                    if candidate.count() > 0:
                        date_trigger = candidate.first
                        break
                except Exception:
                    continue

        if date_trigger is None:
            return False

        trigger_clicked = False
        for click_method in ("playwright", "javascript", "keyboard"):
            try:
                date_trigger.scroll_into_view_if_needed()
                if click_method == "playwright":
                    date_trigger.click(force=True)
                elif click_method == "javascript":
                    date_trigger.evaluate("element => element.click()")
                else:
                    date_trigger.focus()
                    date_trigger.press("Enter")
                page.wait_for_timeout(350)

                expanded = date_trigger.get_attribute("aria-expanded") == "true"
                month_header = page.locator(
                    f"span:text-is('{datetime.now().year}년 {datetime.now().month}월'), "
                    f"div:text-is('{datetime.now().year}년 {datetime.now().month}월')"
                )
                calendar_visible = any(
                    month_header.nth(index).is_visible()
                    for index in range(month_header.count())
                )
                if expanded or calendar_visible:
                    trigger_clicked = True
                    break
            except Exception:
                continue
        if not trigger_clicked:
            return False

    page.wait_for_timeout(500)
    today = datetime.now()
    month_steps = (scheduled_at.year - today.year) * 12 + scheduled_at.month - today.month
    direction_labels = (
        ("다음 달", "Next month") if month_steps >= 0 else ("이전 달", "Previous month")
    )
    for _ in range(abs(month_steps)):
        month_button = page.locator(
            ", ".join(
                f"button[aria-label*='{label}'], div[role='button'][aria-label*='{label}']"
                for label in direction_labels
            )
        )
        if month_button.count() == 0:
            return False
        month_button.last.click(force=True)
        page.wait_for_timeout(250)

    day_text = str(scheduled_at.day)
    try:
        day_clicked = page.evaluate("""(target) => {
            const isVisible = element => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
            };
            const monthLabels = [
                `${target.year}년 ${target.month}월`,
                `${target.month}월 ${target.year}`,
                `${target.year}-${String(target.month).padStart(2, '0')}`,
            ];
            const allElements = Array.from(document.querySelectorAll("div, span, button"));
            const monthHeader = allElements.find(element => {
                const text = element.textContent ? element.textContent.trim() : '';
                return monthLabels.includes(text) && isVisible(element);
            });
            if (!monthHeader) return false;

            let calendar = monthHeader.parentElement;
            while (calendar && calendar !== document.body) {
                const numericDays = Array.from(calendar.querySelectorAll("div, span, button, [tabindex]"))
                    .filter(element => {
                        const text = element.textContent ? element.textContent.trim() : '';
                        return /^(?:[1-9]|[12][0-9]|3[01])$/.test(text) && isVisible(element);
                    });
                if (numericDays.length >= 7) break;
                calendar = calendar.parentElement;
            }
            if (!calendar || calendar === document.body) return false;

            const isoDate = `${target.year}-${String(target.month).padStart(2, '0')}-${String(target.day).padStart(2, '0')}`;
            const fullDateControls = Array.from(calendar.querySelectorAll("button, [role='button'], [role='gridcell'], [aria-label], [data-date], [datetime]"))
                .filter(element => {
                    if (!isVisible(element)) return false;
                    const aria = element.getAttribute('aria-label') || '';
                    const dataDate = element.getAttribute('data-date') || '';
                    const dateTime = element.getAttribute('datetime') || '';
                    const koreanDate = `${target.year}년 ${target.month}월 ${target.day}일`;
                    return aria.includes(koreanDate) || dataDate === isoDate || dateTime.startsWith(isoDate);
                });
            if (fullDateControls.length > 0) {
                const clickable = fullDateControls[0].closest("button, [role='button'], [tabindex='0']") || fullDateControls[0];
                clickable.click();
                return true;
            }

            const matches = Array.from(calendar.querySelectorAll("button, [role='button'], [tabindex], div, span"))
                .filter(element => {
                    const text = element.textContent ? element.textContent.trim() : '';
                    return text === String(target.day) && isVisible(element);
                })
                .map(element => {
                    const clickable = element.closest("button, [role='button'], [tabindex='0']") || element;
                    const rect = clickable.getBoundingClientRect();
                    return { clickable, area: rect.width * rect.height };
                })
                .filter(item => calendar.contains(item.clickable));
            if (matches.length === 0) return false;

            matches.sort((a, b) => a.area - b.area);
            matches[0].clickable.click();
            return true;
        }""", {
            "year": scheduled_at.year,
            "month": scheduled_at.month,
            "day": scheduled_at.day,
        })
        if day_clicked:
            return True
    except Exception:
        pass

    day_candidates = page.locator(
        f"ytcp-date-picker button:text-is('{day_text}'), "
        f"ytcp-date-picker [role='button']:text-is('{day_text}'), "
        f"ytcp-date-picker [role='gridcell']:text-is('{day_text}'), "
        f"div[role='dialog'] button:text-is('{day_text}'), "
        f"div[role='dialog'] div[role='button']:text-is('{day_text}'), "
        f"div[role='dialog'] [role='gridcell']:text-is('{day_text}'), "
        f"div[role='dialog'] [tabindex='0']:text-is('{day_text}'), "
        f"button:text-is('{day_text}'), div[role='button']:text-is('{day_text}'), "
        f"[tabindex='0']:text-is('{day_text}')"
    )
    for index in range(day_candidates.count() - 1, -1, -1):
        candidate = day_candidates.nth(index)
        try:
            if candidate.is_visible():
                candidate.click(force=True)
                return True
        except Exception:
            continue
    return False


def fill_labeled_time(page, scheduled_at: datetime) -> bool:
    """예약 화면의 시간 입력을 24시간제 또는 오전/오후 표기로 채웁니다."""
    time_inputs = page.locator(
        "input[type='time'], input[name*='time' i], input[aria-label*='시간'], "
        "input[aria-label*='time' i], input[placeholder*='시간'], input[placeholder*='time' i]"
    )
    if time_inputs.count() == 0:
        labels = page.locator(
            "label:text-is('시간'), label:text-is('Time'), "
            "div:text-is('시간'), div:text-is('Time'), "
            "span:text-is('시간'), span:text-is('Time')"
        )
        for index in range(labels.count()):
            label = labels.nth(index)
            try:
                if not label.is_visible():
                    continue
                candidate = label.locator("xpath=following::input[1]")
                if candidate.count() > 0 and candidate.first.is_visible():
                    time_inputs = candidate
                    break
            except Exception:
                continue

    for index in range(time_inputs.count()):
        target = time_inputs.nth(index)
        try:
            if not target.is_visible():
                continue
            input_type = (target.get_attribute("type") or "text").lower()
            if input_type == "time":
                value = scheduled_at.strftime("%H:%M")
            else:
                hour_12 = scheduled_at.hour % 12 or 12
                meridiem = "AM" if scheduled_at.hour < 12 else "PM"
                value = f"{hour_12}:{scheduled_at.minute:02d} {meridiem}"

            target.click(force=True)
            target.fill(value)
            target.dispatch_event("input")
            target.dispatch_event("change")
            target.press("Tab")
            page.wait_for_timeout(300)
            if target.input_value().strip():
                return True
        except Exception:
            continue
    return False
