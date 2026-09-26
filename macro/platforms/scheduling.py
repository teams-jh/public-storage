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


def scroll_calendar_into_view(page) -> None:
    """열려 있는 달력 팝업/컨테이너가 화면에 온전히 보이도록 스크롤을 내립니다."""
    try:
        page.evaluate(r"""() => {
            const isVisible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
            };

            // 1. 달력 관련 주요 컨테이너 탐색
            const calendarSelectors = [
                "[role='grid']",
                "[role='dialog'] table",
                "[aria-roledescription='calendar']",
                "ytcp-date-picker",
                "div[role='dialog'] div[tabindex='-1']",
                "div[role='dialog'] div:has(> [role='gridcell'])"
            ];
            let calendarEl = null;
            for (const sel of calendarSelectors) {
                const candidates = Array.from(document.querySelectorAll(sel)).filter(isVisible);
                if (candidates.length > 0) {
                    calendarEl = candidates[candidates.length - 1];
                    break;
                }
            }

            // 헤더 텍스트로 달력 부모 찾기 fallback
            if (!calendarEl) {
                const allElements = Array.from(document.querySelectorAll("div, span")).filter(isVisible);
                const monthNode = allElements.find(el => {
                    const text = (el.textContent || '').trim();
                    return /^\d{4}년\s*\d{1,2}월/.test(text) || /^(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}/i.test(text);
                });
                if (monthNode) {
                    calendarEl = monthNode.closest("[role='dialog'], [role='grid'], div") || monthNode.parentElement;
                }
            }

            if (calendarEl) {
                calendarEl.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
                const rect = calendarEl.getBoundingClientRect();
                const bottomDiff = rect.bottom - window.innerHeight;
                if (bottomDiff > 0) {
                    window.scrollBy(0, bottomDiff + 40);
                }

                // 부모 스크롤 컨테이너 탐색 및 스크롤
                let parent = calendarEl.parentElement;
                while (parent && parent !== document.body) {
                    const style = window.getComputedStyle(parent);
                    const overflowY = style.overflowY;
                    if ((overflowY === 'auto' || overflowY === 'scroll') && parent.scrollHeight > parent.clientHeight) {
                        const pRect = parent.getBoundingClientRect();
                        const pOverflow = rect.bottom - pRect.bottom;
                        if (pOverflow > -30) {
                            parent.scrollTop += (pOverflow + 50);
                        }
                    }
                    parent = parent.parentElement;
                }
            }

            // 모달(dialog) 내부의 스크롤 컨테이너 아래로 보정 스크롤
            const dialog = document.querySelector("div[role='dialog']");
            if (dialog) {
                const scrollables = Array.from(dialog.querySelectorAll("*")).filter(el => {
                    const style = window.getComputedStyle(el);
                    const overflowY = style.overflowY;
                    return (overflowY === 'auto' || overflowY === 'scroll') && el.scrollHeight > el.clientHeight;
                });
                for (const el of scrollables) {
                    if (el.scrollHeight - el.scrollTop - el.clientHeight > 10) {
                        el.scrollTop += 250;
                    }
                }
            }
        }""")
        page.wait_for_timeout(300)
    except Exception:
        pass


def _get_calendar_displayed_month(page) -> dict | None:
    """달력에 현재 표시된 연/월 정보를 읽어옵니다."""
    try:
        return page.evaluate(r"""() => {
            const isVisible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
            };
            const youtubePickers = Array.from(document.querySelectorAll('ytcp-date-picker')).filter(isVisible);
            const root = youtubePickers.length ? youtubePickers[youtubePickers.length - 1] : document;

            // 1. Next/Previous 버튼과 같은 컨테이너의 텍스트 탐색
            const nextBtns = Array.from(root.querySelectorAll("button[aria-label*='Next' i], button[aria-label*='다음']")).filter(isVisible);
            for (const btn of nextBtns) {
                const parent = btn.parentElement;
                if (parent) {
                    const spans = Array.from(parent.querySelectorAll("span, div")).filter(isVisible);
                    for (const s of spans) {
                        const txt = (s.textContent || '').trim();
                        const m = txt.match(/(\d{4})년\s*(\d{1,2})월/);
                        if (m) return { year: parseInt(m[1]), month: parseInt(m[2]), text: txt };
                    }
                }
            }

            // 2. 전체 페이지 내 모든 span/div에서 'YYYY년 M월' 패턴 탐색
            const allElements = Array.from(root.querySelectorAll("span, div")).filter(isVisible);
            for (const el of allElements) {
                const txt = (el.textContent || '').trim();
                const m = txt.match(/^(\d{4})년\s*(\d{1,2})월$/);
                if (m) return { year: parseInt(m[1]), month: parseInt(m[2]), text: txt };
            }

            // 3. 영문 Month YYYY 패턴 탐색
            const monthsEng = {
                january: 1, jan: 1, february: 2, feb: 2, march: 3, mar: 3,
                april: 4, apr: 4, may: 5, june: 6, jun: 6,
                july: 7, jul: 7, august: 8, aug: 8, september: 9, sep: 9,
                october: 10, oct: 10, november: 11, nov: 11, december: 12, dec: 12
            };
            for (const el of allElements) {
                const txt = (el.textContent || '').trim().toLowerCase();
                const mEng = txt.match(/^([a-z]+)\s+(\d{4})$/);
                if (mEng && monthsEng[mEng[1]]) {
                    return { year: parseInt(mEng[2]), month: monthsEng[mEng[1]], text: txt };
                }
            }

            // YouTube의 언어/날짜 형식에 따라 월과 연도의 순서가 달라져요.
            for (const el of allElements) {
                const txt = (el.textContent || '').trim();
                const korean = txt.match(/^(\d{1,2})월\s*(\d{4})년?$/);
                if (korean) return { year: Number(korean[2]), month: Number(korean[1]), text: txt };
                const dotted = txt.match(/^(\d{4})\.\s*(\d{1,2})\.?$/);
                if (dotted) return { year: Number(dotted[1]), month: Number(dotted[2]), text: txt };
            }

            return null;
        }""")
    except Exception:
        return None


def _scroll_youtube_calendar_to_month(page, scheduled_at: datetime, direction: int) -> bool:
    """YouTube의 스크롤형 달력에서 목표 월 제목을 찾아 화면에 표시해요."""
    for _ in range(24):
        state = page.evaluate(r"""(target) => {
            const calendars = Array.from(document.querySelectorAll('ytcp-scrollable-calendar'));
            const root = calendars.filter(el => {
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            }).pop();
            if (!root) return 'unavailable';

            const monthName = new Intl.DateTimeFormat('en-US', {month: 'long'})
                .format(new Date(target.year, target.month - 1, 1));
            const shortMonthName = new Intl.DateTimeFormat('en-US', {month: 'short'})
                .format(new Date(target.year, target.month - 1, 1));
            const labels = [
                `${target.year}년 ${target.month}월`,
                `${target.month}월 ${target.year}년`,
                `${target.month}월 ${target.year}`,
                `${target.year}. ${target.month}.`,
                `${monthName} ${target.year}`,
                `${shortMonthName} ${target.year}`,
            ];
            const header = Array.from(root.querySelectorAll('.calendar-month-label'))
                .find(el => labels.some(label => label.toLowerCase() === (el.textContent || '').trim().toLowerCase()));
            if (header) {
                header.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'});
                return 'found';
            }

            const listScrollTarget = root.querySelector('tp-yt-iron-list')?.scrollTarget;
            const scrollables = [listScrollTarget, root, ...root.querySelectorAll('*')].filter(el => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return /auto|scroll/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 5;
            });
            const scroller = (scrollables.includes(listScrollTarget) && listScrollTarget)
                || scrollables.sort((a, b) =>
                (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight))[0];
            if (!scroller) return 'unavailable';
            const before = scroller.scrollTop;
            scroller.scrollTop += Math.sign(target.direction) * Math.max(scroller.clientHeight * 0.8, 100);
            scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
            return scroller.scrollTop === before ? 'end' : 'moved';
        }""", {
            "year": scheduled_at.year,
            "month": scheduled_at.month,
            "direction": direction,
        })
        if state == "found":
            return True
        if state != "moved":
            return False
        page.wait_for_timeout(200)
    return False


def _select_youtube_calendar_day(page, scheduled_at: datetime) -> bool:
    """YouTube 가상 목록에서 목표 월의 활성 날짜 칸을 실제 마우스로 눌러요."""
    month_text = f"{scheduled_at.year}년 {scheduled_at.month}월"
    month = page.locator(
        "ytcp-scrollable-calendar:visible "
        f".calendar-month:has(> .calendar-month-label:text-is('{month_text}'))"
    )
    if month.count() == 0:
        displayed_month = _get_calendar_displayed_month(page)
        direction = 1 if displayed_month is None or (
            scheduled_at.year, scheduled_at.month
        ) >= (displayed_month["year"], displayed_month["month"]) else -1
        if not _scroll_youtube_calendar_to_month(page, scheduled_at, direction):
            return False

    day = month.locator(
        f"span.calendar-day:not(.disabled):not(.invisible):text-is('{scheduled_at.day}')"
    )
    try:
        if day.count() != 1:
            return False
        day.scroll_into_view_if_needed()
        day.click(timeout=3000)
        return True
    except Exception:
        return False


def _click_calendar_next_button(page) -> bool:
    """달력 상단의 다음 달(>) 버튼을 찾아 클릭합니다."""
    # 1. Playwright Locator 탐색 후 실제 물리 마우스 클릭
    next_selectors = [
        "button[aria-label='Next month']",
        "button[aria-label*='Next' i]",
        "button[aria-label*='다음']",
        "div[role='button'][aria-label*='다음']",
        "span:has-text('월') ~ button",
        "div:has(> span:has-text('월')) button:last-of-type"
    ]
    for sel in next_selectors:
        loc = page.locator(sel)
        for i in range(loc.count()):
            btn = loc.nth(i)
            try:
                if btn.is_visible() and not btn.is_disabled():
                    btn.scroll_into_view_if_needed()
                    page.wait_for_timeout(100)
                    box = btn.bounding_box()
                    if box:
                        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    else:
                        btn.click(force=True)
                    page.wait_for_timeout(350)
                    return True
            except Exception:
                continue

    # 2. JS evaluate로 DOM 상의 다음 달(>) 버튼 탐색 및 전체 마우스 이벤트 발화
    try:
        clicked = page.evaluate(r"""() => {
            const isVisible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
            };

            let targetBtn = document.querySelector("button[aria-label='Next month'], button[aria-label*='Next' i], button[aria-label*='다음']");
            if (!targetBtn || !isVisible(targetBtn)) {
                const spans = Array.from(document.querySelectorAll("span")).filter(isVisible);
                for (const s of spans) {
                    if (/(\d{4})년\s*(\d{1,2})월/.test((s.textContent || '').trim())) {
                        const buttons = Array.from(s.parentElement.querySelectorAll("button")).filter(isVisible);
                        if (buttons.length >= 2) {
                            targetBtn = buttons[buttons.length - 1];
                            break;
                        }
                    }
                }
            }

            if (!targetBtn) return false;

            targetBtn.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(name => {
                targetBtn.dispatchEvent(new MouseEvent(name, {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    buttons: 1
                }));
            });
            targetBtn.click();
            return true;
        }""")
        if clicked:
            page.wait_for_timeout(350)
            return True
    except Exception:
        pass

    return False


def _navigate_instagram_to_target_month(page, scheduled_at: datetime) -> bool:
    """현재 달력의 월을 확인하며 목표 연/월에 도달할 때까지 > (다음 달) 버튼을 넘깁니다."""
    target_year = scheduled_at.year
    target_month = scheduled_at.month

    # 최대 12회 (1년치) 이동 시도
    for attempt in range(12):
        month_info = _get_calendar_displayed_month(page)
        if month_info:
            cur_year = month_info["year"]
            cur_month = month_info["month"]
            month_diff = (target_year - cur_year) * 12 + (target_month - cur_month)
            if month_diff == 0:
                # 목표 연/월에 도달 완료!
                return True
            elif month_diff > 0:
                # 다음 달(>) 버튼 클릭
                _click_calendar_next_button(page)
                page.wait_for_timeout(400)
            else:
                # 이전 달(<) 버튼 클릭
                prev_btn = page.locator("button[aria-label='Previous month'], button[aria-label*='이전']")
                if prev_btn.count() > 0 and prev_btn.first.is_visible() and not prev_btn.first.is_disabled():
                    prev_btn.first.scroll_into_view_if_needed()
                    prev_btn.first.click(force=True)
                    page.wait_for_timeout(400)
                else:
                    break
        else:
            # 월 헤더 텍스트를 감지하지 못한 경우 현재 달과 비교하여 강제 다음 달(>) 클릭
            now = datetime.now()
            month_diff = (target_year - now.year) * 12 + (target_month - now.month)
            if month_diff > 0:
                for _ in range(month_diff):
                    _click_calendar_next_button(page)
                    page.wait_for_timeout(400)
            return True

    return False


def _select_instagram_calendar_day(page, scheduled_at: datetime) -> bool:
    """Instagram 달력 DOM (role='grid' 및 button[role='gridcell'])에서 목표 연/월 이동 및 날짜를 선택합니다."""
    # 1. 달이 다른 경우 > 버튼을 눌러 목표 월로 이동
    _navigate_instagram_to_target_month(page, scheduled_at)
    page.wait_for_timeout(350)

    day_str = str(scheduled_at.day)

    # 2. role='grid' 내의 활성화된 button[role='gridcell'] 중에서 해당 날짜 클릭
    # 방법 1: Playwright Locator로 bounding_box 구해서 실제 물리 마우스 클릭
    try:
        active_cells = page.locator(
            "[role='grid'] button[role='gridcell']:not([aria-disabled='true']), "
            "[role='grid'] button:not([aria-disabled='true'])"
        )
        for i in range(active_cells.count()):
            cell = active_cells.nth(i)
            try:
                txt = cell.inner_text().strip()
                if txt == day_str:
                    cell.scroll_into_view_if_needed()
                    page.wait_for_timeout(100)
                    box = cell.bounding_box()
                    if box:
                        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    else:
                        cell.click(force=True)
                    page.wait_for_timeout(400)
                    return True
            except Exception:
                continue
    except Exception:
        pass

    # 방법 2: JS evaluate로 정확한 타겟 버튼 탐색 및 React Synthetic/Mouse Event 디스패치
    try:
        clicked = page.evaluate(r"""(targetDay) => {
            const isVisible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
            };

            const grids = Array.from(document.querySelectorAll("[role='grid']")).filter(isVisible);
            for (const grid of grids) {
                const buttons = Array.from(grid.querySelectorAll("button[role='gridcell'], button")).filter(isVisible);
                for (const btn of buttons) {
                    if (btn.getAttribute('aria-disabled') === 'true') continue;
                    const spans = Array.from(btn.querySelectorAll("span"));
                    const spanTexts = spans.map(s => (s.textContent || '').trim());
                    const btnText = (btn.textContent || '').trim();
                    if (btnText === String(targetDay) || spanTexts.includes(String(targetDay))) {
                        btn.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
                        const events = ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'];
                        for (const name of events) {
                            btn.dispatchEvent(new MouseEvent(name, {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                buttons: 1
                            }));
                        }
                        btn.click();
                        return true;
                    }
                }
            }
            return false;
        }""", scheduled_at.day)

        if clicked:
            page.wait_for_timeout(400)
            return True
    except Exception:
        pass

    return False


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
                grid_visible = page.locator("[role='grid']").count() > 0
                month_header = page.locator(
                    f"span:text-is('{datetime.now().year}년 {datetime.now().month}월'), "
                    f"div:text-is('{datetime.now().year}년 {datetime.now().month}월')"
                )
                calendar_visible = any(
                    month_header.nth(index).is_visible()
                    for index in range(month_header.count())
                )
                if expanded or grid_visible or calendar_visible:
                    trigger_clicked = True
                    break
            except Exception:
                continue
        if not trigger_clicked:
            return False

    page.wait_for_timeout(400)
    if page.locator("ytcp-scrollable-calendar:visible").count() > 0:
        return _select_youtube_calendar_day(page, scheduled_at)

    # 달력이 켜진 후 달력 및 부모 스크롤 컨테이너를 아래로 스크롤하여 달력 전체 노출
    scroll_calendar_into_view(page)

    # YouTube 달력에 Instagram용 월 이동을 먼저 적용하면 월이 중복으로 넘어갈 수 있어요.
    youtube_picker = page.locator("ytcp-date-picker:visible")
    is_youtube_calendar = youtube_picker.count() > 0

    # 1. Instagram role='grid' 구조 최적화 클릭 우선 시도
    if not is_youtube_calendar and _select_instagram_calendar_day(page, scheduled_at):
        return True

    # 2. 범용 달력(YouTube Studio 등) fallback 로직
    displayed_month = _get_calendar_displayed_month(page)
    month_delta = (
        (scheduled_at.year - displayed_month["year"]) * 12
        + scheduled_at.month - displayed_month["month"]
    ) if displayed_month else 0
    youtube_month_found = is_youtube_calendar and (
        (displayed_month is not None and month_delta == 0)
        or _scroll_youtube_calendar_to_month(
            page, scheduled_at, 1 if month_delta > 0 else -1
        )
    )
    if displayed_month is None and not youtube_month_found:
        return False
    month_steps = 0 if youtube_month_found else month_delta
    direction_labels = (
        ("다음 달", "Next month") if month_steps >= 0
        else ("이전 달", "지난달", "Previous month")
    )
    for _ in range(abs(month_steps)):
        calendar_scope = youtube_picker.last if is_youtube_calendar else page
        month_button = calendar_scope.locator(
            ", ".join(
                f"button[aria-label*='{label}' i], div[role='button'][aria-label*='{label}' i], "
                f"ytcp-icon-button[aria-label*='{label}' i]"
                for label in direction_labels
            )
        )
        if month_button.count() == 0:
            return False
        month_button.last.scroll_into_view_if_needed()
        month_button.last.click(force=True)
        previous_month = (displayed_month["year"], displayed_month["month"])
        for _ in range(6):
            page.wait_for_timeout(250)
            displayed_month = _get_calendar_displayed_month(page)
            if displayed_month and (
                displayed_month["year"], displayed_month["month"]
            ) != previous_month:
                break
        else:
            return False

    if not youtube_month_found and (displayed_month["year"], displayed_month["month"]) != (
        scheduled_at.year, scheduled_at.month
    ):
        return False

    # 월 변경 후에도 달력 위치 스크롤 재보정
    if not youtube_month_found:
        scroll_calendar_into_view(page)

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
                `${target.month}월 ${target.year}년`,
                `${target.month}월 ${target.year}`,
                `${target.year}-${String(target.month).padStart(2, '0')}`,
                `${target.year}. ${target.month}.`,
                new Intl.DateTimeFormat('en-US', {month: 'long'}).format(new Date(target.year, target.month - 1, 1)) + ` ${target.year}`,
                new Intl.DateTimeFormat('en-US', {month: 'short'}).format(new Date(target.year, target.month - 1, 1)) + ` ${target.year}`,
            ];
            const youtubePickers = Array.from(document.querySelectorAll('ytcp-date-picker')).filter(isVisible);
            const root = youtubePickers.length ? youtubePickers[youtubePickers.length - 1] : document;
            const allElements = Array.from(root.querySelectorAll("div, span, button"));
            const monthHeader = allElements.find(element => {
                const text = element.textContent ? element.textContent.trim() : '';
                return monthLabels.some(label => label.toLowerCase() === text.toLowerCase()) && isVisible(element);
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
                clickable.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
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
            const clickable = matches[0].clickable;
            clickable.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
            clickable.click();
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
            candidate.scroll_into_view_if_needed()
            if candidate.is_visible():
                candidate.click(force=True)
                return True
        except Exception:
            continue

    # 추가 방어: 마우스 휠로 살짝 스크롤 후 다시 시도
    try:
        page.mouse.wheel(0, 200)
        page.wait_for_timeout(300)
        for index in range(day_candidates.count() - 1, -1, -1):
            candidate = day_candidates.nth(index)
            if candidate.is_visible():
                candidate.click(force=True)
                return True
    except Exception:
        pass

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
