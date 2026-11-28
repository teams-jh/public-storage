"""두 번째 YouTube 계정의 재생목록에서 중복 제목을 정리해요."""

import argparse
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from time import monotonic
from typing import Generic, TypeVar
from urllib.parse import parse_qs, urlsplit, urlunsplit

from playwright.sync_api import Error as PlaywrightError, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from global_constants import YOUTUBE_BROWSER_CONFIG, load_macro_settings


@dataclass(frozen=True)
class Video:
    title: str
    video_id: str
    playlist_item_id: str = ""


@dataclass(frozen=True)
class PlaylistEntry:
    url: str
    title: str


Row = TypeVar("Row")


@dataclass(frozen=True)
class StudioListPage(Generic[Row]):
    items: tuple[Row, ...]
    start: int | None = None
    end: int | None = None
    total: int | None = None


def playlist_url(value: str, settings: dict, *, all_playlists: bool = False) -> str:
    parts = urlsplit(value.strip())
    origin = urlsplit(settings["studio_origin"])
    path_key = "channel_playlists_path_pattern" if all_playlists else "playlist_path_pattern"
    if (parts.scheme, parts.netloc) != (origin.scheme, origin.netloc) or not re.fullmatch(
        settings[path_key], parts.path
    ):
        if all_playlists:
            raise ValueError("YouTube Studio 채널 콘텐츠의 재생목록 탭 주소를 입력해 주세요.")
        raise ValueError("YouTube Studio 재생목록의 동영상 탭 주소를 입력해 주세요.")
    query = parts.query if all_playlists else ""
    return urlunsplit((origin.scheme, origin.netloc, parts.path.rstrip("/"), query, ""))


def account_profile(account: str) -> Path:
    account_settings = load_macro_settings("AUTO_BULK_UPLOAD_CONFIG")["accounts"][account]
    if "MACRO_SESSION_DIR" in account_settings:
        session_dir = Path(__file__).resolve().parent / account_settings["MACRO_SESSION_DIR"]
    else:
        from config import SESSION_DIR

        session_dir = SESSION_DIR
    return session_dir / YOUTUBE_BROWSER_CONFIG["profile_directory"]


def video_id(href: str) -> str:
    url = urlsplit(href)
    if url.path == "/watch":
        return next(iter(parse_qs(url.query).get("v", [])), "")
    match = re.fullmatch(r"/(?:video/|shorts/)?([\w-]+)(?:/edit)?/?", url.path)
    return match.group(1) if match else ""


def page_range(text: str) -> tuple[int | None, int | None, int | None]:
    number = r"(\d[\d,]*)"
    span = rf"{number}\s*[-–—−~∼]\s*{number}\s*(?:개)?"
    english = re.search(rf"{span}\s*(?:of|/)\s*(about\s*|약\s*)?{number}", text, re.I)
    korean = re.search(rf"(약\s*)?{number}\s*(?:개)?\s*중\s*{span}", text)
    if english:
        start, end, approximate, total = english.groups()
    elif korean:
        approximate, total, start, end = korean.groups()
    else:
        return None, None, None
    return int(start.replace(",", "")), int(end.replace(",", "")), None if approximate else int(total.replace(",", ""))


class StudioPages(ABC, Generic[Row]):
    def __init__(self, page: Page, url: str, settings: dict, *, empty_text_key: str):
        self.page = page
        self.url = url
        self.settings = settings
        self.selectors = settings["selectors"]
        self.empty = page.get_by_text(self.pattern(empty_text_key)).first
        self.footer = page.locator(f":is({self.selectors['pagination']}):visible")
        self.loading = page.locator(f":is({self.selectors['pagination_loading']}):visible").first
        next_text = self.pattern("next_text")
        next_controls = page.locator(self.selectors["next"]).or_(
            page.get_by_role("button", name=next_text)
        ).or_(page.get_by_role("link", name=next_text)).or_(page.get_by_label(next_text))
        self.next_controls = next_controls.and_(page.locator(":visible"))
        self.enabled_next = self.next_controls.and_(page.locator(
            ":not(:disabled, [disabled], [disabled] *, [aria-disabled='true'], [aria-disabled='true'] *, [inert], [inert] *)"
        )).first
        self.has_seen_next = False

    def pattern(self, key: str) -> re.Pattern:
        return re.compile(self.selectors[key], re.IGNORECASE)

    def open(self) -> None:
        self.page.goto(self.url, wait_until="domcontentloaded")
        if urlsplit(self.page.url).hostname == self.settings["login_host"]:
            print("브라우저에서 재생목록을 관리하는 YouTube 계정에 로그인해 주세요.", flush=True)
            self.page.wait_for_url(
                self.settings["studio_origin"] + "/**", timeout=self.settings["login_timeout_ms"]
            )
            self.page.goto(self.url, wait_until="domcontentloaded")

    def read(self) -> StudioListPage[Row] | None:
        actual = urlsplit(self.page.url)
        expected = urlsplit(self.url)
        if (actual.scheme, actual.netloc, actual.path.rstrip("/")) != (expected.scheme, expected.netloc, expected.path):
            raise RuntimeError("입력한 재생목록을 열지 못했어요. 계정과 링크를 확인해 주세요.")

        items = self.read_items()
        for text in self.footer.all_inner_texts():
            start, end, total = page_range(text)
            if start is not None:
                if items or total == 0 or self.empty.is_visible():
                    return StudioListPage(items, start, end, total)
                return None
        if items or self.empty.is_visible():
            return StudioListPage(items)
        return None

    @abstractmethod
    def read_items(self) -> tuple[Row, ...]:
        """현재 페이지에 보이는 항목을 읽어요."""

    def wait_for_page(
        self, accept: Callable[[StudioListPage[Row]], bool], message: str, *, settle: bool = False
    ) -> StudioListPage[Row]:
        deadline = monotonic() + self.settings["ui_timeout_ms"] / 1000
        settle_seconds = self.settings["page_settle_ms"] / 1000
        candidate = None
        unchanged_since = monotonic()
        while monotonic() < deadline:
            current = self.read()
            if current is not None and accept(current):
                if not settle:
                    return current
                if self.loading.is_visible():
                    candidate = None
                elif current != candidate:
                    candidate = current
                    unchanged_since = monotonic()
                elif monotonic() - unchanged_since >= settle_seconds:
                    return current
            else:
                candidate = None
            self.page.wait_for_timeout(self.settings["poll_interval_ms"])
        raise RuntimeError(message)

    def next_button(self, current: StudioListPage[Row]) -> Locator | None:
        deadline = monotonic() + self.settings["ui_timeout_ms"] / 1000
        settle_seconds = self.settings["page_settle_ms"] / 1000
        last_since = None
        while monotonic() < deadline:
            controls = self.next_controls.count() > 0
            self.has_seen_next |= bool(controls)
            visible = self.read()
            if visible is None or self.loading.is_visible():
                last_since = None
            else:
                if visible.start is not None and current.start is not None and visible.start != current.start:
                    raise RuntimeError("다른 페이지가 열렸어요. 다시 실행해서 재생목록을 확인해 주세요.")
                more = visible.end is not None and visible.total is not None and visible.end < visible.total
                at_end = visible.end is not None and visible.end == visible.total
                if not at_end and self.enabled_next.is_visible():
                    return self.enabled_next
                if not more and (at_end or controls or not self.has_seen_next):
                    last_since = last_since if last_since is not None else monotonic()
                    if monotonic() - last_since >= settle_seconds:
                        return None
                else:
                    last_since = None
            self.page.wait_for_timeout(self.settings["poll_interval_ms"])
        raise RuntimeError("다음 페이지로 이동할 수 없어요. 재생목록 화면을 확인해 주세요.")

    def next_page(self, current: StudioListPage[Row]) -> StudioListPage[Row] | None:
        button = self.next_button(current)
        if button is None:
            return None
        button.click()

        def advanced(new: StudioListPage[Row]) -> bool:
            if current.start is not None and new.start is not None:
                return new.start > current.start
            return bool(new.items) and new.items != current.items

        return self.wait_for_page(
            advanced, "다음 페이지의 영상 목록을 확인하지 못했어요. 화면을 확인해 주세요.", settle=True
        )


class StudioPlaylist(StudioPages[Video]):
    def __init__(self, page: Page, url: str, settings: dict):
        super().__init__(page, url, settings, empty_text_key="empty_text")
        title = page.locator(self.selectors["title"])
        row = page.locator(f":is({self.selectors['row']}):visible").filter(has=title)
        self.rows = row.filter(has_not=row)

    def read_items(self) -> tuple[Video, ...]:
        rows = self.rows.evaluate_all(
            """(rows, { title, video_link, item_id_attributes }) => {
                function find(root, selector) {
                    const found = root.querySelector(selector);
                    if (found) return found;
                    const hosts = [root, ...root.querySelectorAll('*')];
                    for (const host of hosts) {
                        const match = host.shadowRoot && find(host.shadowRoot, selector);
                        if (match) return match;
                    }
                    return null;
                }
                return rows.map(row => {
                    const label = find(row, title);
                    const link = label?.closest('a[href]') || label?.querySelector('a[href]') || find(row, video_link);
                    const itemId = item_id_attributes.map(name => row.getAttribute(name) || link?.getAttribute(name))
                        .find(Boolean) || '';
                    return [label?.textContent.trim() || '', link?.getAttribute('href') || '', itemId];
                });
            }""",
            {
                "title": self.selectors["title"],
                "video_link": self.selectors["video_link"],
                "item_id_attributes": self.settings["playlist_item_id_attributes"],
            },
        )
        return tuple(Video(title, video_id(href), item_id) for title, href, item_id in rows)

    def remove(self, current: StudioListPage[Video], index: int) -> StudioListPage[Video]:
        target = current.items[index]
        notice = self.page.locator(f":is({self.selectors['removal_notice']}):visible").filter(
            has_text=self.pattern("removal_notice_text")
        ).first
        if not target.playlist_item_id and all(item == target for item in current.items[index:]) and notice.is_visible():
            try:
                notice.wait_for(state="hidden", timeout=self.settings["removal_notice_clear_ms"])
            except PlaywrightTimeoutError:
                pass

        visible = self.read()
        if visible is None or visible.items != current.items or visible.start != current.start:
            raise RuntimeError("영상 목록이 바뀌었어요. 다시 실행해서 제거할 항목을 확인해 주세요.")

        row = self.rows.nth(index)
        row.hover()
        remove_text = self.pattern("direct_remove")
        action = row.get_by_role("button", name=remove_text)
        if not action.is_visible():
            menu = row.get_by_role("button", name=self.pattern("menu_text")).or_(
                row.locator(f":is({self.selectors['menu']}):visible")
            ).first
            menu.click()
            action = self.page.locator(f":is({self.selectors['menu_item']}):visible").filter(
                has_text=remove_text
            ).or_(self.page.get_by_role("button", name=remove_text))
            action = action.filter(has_not=action)

        notice_ready = not notice.is_visible()
        fresh_notice = False

        action.click()
        dialog = self.page.locator(f":is({self.selectors['remove_dialog']}):visible").filter(
            has_text=self.pattern("remove_dialog_text")
        )
        confirm_text = self.pattern("confirm_text")
        confirm = dialog.get_by_role("button", name=remove_text).or_(
            dialog.get_by_role("button", name=confirm_text)
        ).or_(dialog.locator(f":is({self.selectors['remove_confirm_button']}):visible").filter(has_text=confirm_text))
        confirm = confirm.filter(has_not=confirm)
        expected = current.items[:index] + current.items[index + 1:]

        def removed(new: StudioListPage[Video]) -> bool:
            nonlocal notice_ready, fresh_notice
            if confirm.first.is_visible():
                confirm.click()
                confirm.wait_for(state="hidden")
                return False

            if notice.is_visible():
                fresh_notice |= notice_ready
            else:
                notice_ready = True
            if current.start is not None and new.start != current.start:
                return False
            if new.items[:len(expected)] != expected:
                return False
            if new.items != current.items:
                return True
            if new.end is not None and current.end is not None and new.end < current.end:
                return False
            return fresh_notice or (current.total is not None and new.total == current.total - 1)

        return self.wait_for_page(
            removed, f"{index + 1}번 항목 ({target.video_id})을 뺐는지 확인하지 못했어요. Studio 화면을 확인해 주세요.",
            settle=True,
        )


class StudioChannelPlaylists(StudioPages[PlaylistEntry]):
    def __init__(self, page: Page, url: str, settings: dict):
        super().__init__(page, url, settings, empty_text_key="channel_empty_text")
        self.links = page.locator(f":is({self.selectors['channel_playlist_link']}):visible")

    def read(self) -> StudioListPage[PlaylistEntry] | None:
        current = super().read()
        if current and current.start is not None and current.end is not None:
            if current.total != 0 and len(current.items) < current.end - current.start + 1:
                return None
        return current

    def read_items(self) -> tuple[PlaylistEntry, ...]:
        links = self.links.evaluate_all(
            """links => links.map(link => [link.href, link.innerText.trim() || link.getAttribute('title') || ''])"""
        )
        origin = urlsplit(self.settings["studio_origin"])
        entries = {}
        for href, title in links:
            parts = urlsplit(href)
            if (parts.scheme, parts.netloc) == (origin.scheme, origin.netloc):
                match = re.fullmatch(self.settings["channel_playlist_link_pattern"], parts.path)
                if not match:
                    continue
                playlist_id = match[1]
            elif (
                parts.scheme == "https" and parts.hostname in self.settings["public_playlist_hosts"]
                and parts.path == "/playlist"
            ):
                playlist_id = next(iter(parse_qs(parts.query).get("list", [])), "")
            else:
                continue

            path = self.settings["playlist_videos_path_template"].format(playlist_id=playlist_id)
            if re.fullmatch(self.settings["playlist_path_pattern"], path):
                url = self.settings["studio_origin"] + path
                if not entries.get(url):
                    entries[url] = title.strip()
        return tuple(PlaylistEntry(url, title) for url, title in entries.items())


def review_playlist(playlist: StudioPlaylist, *, auto_remove: bool) -> None:
    current = playlist.wait_for_page(
        lambda state: True, "영상 목록을 찾지 못했어요. 재생목록 링크와 계정 권한을 확인해 주세요.", settle=True
    )
    page_number = 1
    removed_count = 0
    while True:
        by_title = defaultdict(list)
        for index, video in enumerate(current.items):
            if video.title and video.video_id:
                by_title[video.title].append((index, video.video_id))

        duplicates = {title: items for title, items in by_title.items() if len(items) > 1}
        if duplicates:
            print(f"\n{page_number}페이지에 같은 제목이 {len(duplicates)}개 있어요.")
            targets = []
            for title, (keep, *remove) in duplicates.items():
                print(f"  {title}")
                print(f"    남길 영상  {keep[0] + 1}번 ({keep[1]})")
                for index, identifier in remove:
                    print(f"    뺄 영상    {index + 1}번 ({identifier})")
                    targets.append(index)

            choice = "y"
            if not auto_remove:
                while (choice := input("위 영상을 재생목록에서 뺄까요? [Y/N] ").strip().lower()) not in {"y", "n"}:
                    print("빼려면 Y, 다음 페이지를 보려면 N을 입력해 주세요.")
            if choice == "y":
                # 뒤에서부터 제거해야 다음 페이지에서 채워진 행이 승인한 행의 순서를 바꾸지 않아요.
                for index in sorted(targets, reverse=True):
                    current = playlist.remove(current, index)
                    removed_count += 1
                print(f"{len(targets)}개를 뺐어요. 같은 페이지를 다시 확인해요.")
                continue
        else:
            print(f"{page_number}페이지에 같은 제목이 없어요.")

        next_page = playlist.next_page(current)
        if next_page is None:
            print(f"마지막 페이지까지 확인했어요. 재생목록에서 영상 {removed_count}개를 뺐어요.")
            return
        current = next_page
        page_number += 1


def review_channel(page: Page, url: str, settings: dict, *, auto_remove: bool) -> bool:
    channel = StudioChannelPlaylists(page, url, settings)
    channel.open()
    current = channel.wait_for_page(
        lambda state: True, "채널의 재생목록을 읽지 못했어요. 링크와 계정 권한을 확인해 주세요.", settle=True
    )
    # 변경 시간순으로 정렬된 목록에서 영상 제거로 순서가 바뀌어도 대상을 빠뜨리지 않아요.
    entries = {}
    while current is not None:
        for entry in current.items:
            entries.setdefault(entry.url, entry)
        current = channel.next_page(current)

    if not entries:
        print("채널에 표시된 재생목록이 없어요.")
        return True

    failures = []
    for index, entry in enumerate(entries.values(), start=1):
        label = entry.title or entry.url
        print(f"\n[{index}/{len(entries)}] {label}", flush=True)
        playlist = StudioPlaylist(page, entry.url, settings)
        try:
            playlist.open()
            review_playlist(playlist, auto_remove=auto_remove)
        except (PlaywrightError, RuntimeError) as error:
            if page.is_closed():
                raise
            failures.append(entry)
            print(f"재생목록 확인을 마치지 못했어요. {str(error).splitlines()[0]}", file=sys.stderr)

    print(f"\n재생목록 {len(entries) - len(failures)}개를 끝까지 확인했어요.")
    if failures:
        print(f"확인을 마치지 못한 재생목록이 {len(failures)}개 있어요.", file=sys.stderr)
        for entry in failures:
            print(f"  {entry.title or '재생목록'} ({entry.url})", file=sys.stderr)
    return not failures


def main(argv: list[str] | None = None, *, account: str = "second") -> int:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")

    account_name = "첫 번째" if account == "first" else "두 번째"
    parser = argparse.ArgumentParser(description=f"{account_name} YouTube 계정의 재생목록에서 중복 제목을 정리해요.")
    parser.add_argument("--all", action="store_true", help="채널의 재생목록 탭에 표시된 재생목록을 차례로 정리해요.")
    parser.add_argument("--option", choices=["no_auto"], help="페이지마다 중복 항목을 뺄지 물어봐요.")
    args = parser.parse_args(argv)
    auto_remove = args.option is None

    try:
        settings = load_macro_settings("YOUTUBE_PLAYLIST_DEDUPE_CONFIG")
        if auto_remove:
            print("페이지마다 같은 제목의 첫 영상은 남기고, 나머지는 재생목록에서 자동으로 빼요.")
        location = "채널 콘텐츠의 재생목록 탭" if args.all else "재생목록의 동영상 탭"
        prompt = f"{account_name} 계정에서 정리할 YouTube Studio {location} 링크를 입력해 주세요.\n> "
        url = playlist_url(input(prompt), settings, all_playlists=args.all)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=account_profile(account),
                headless=False,
                no_viewport=True,
                args=YOUTUBE_BROWSER_CONFIG["launch_args"],
            )
            try:
                browser.set_default_timeout(settings["ui_timeout_ms"])
                page = browser.new_page()
                if args.all:
                    return 0 if review_channel(page, url, settings, auto_remove=auto_remove) else 1
                playlist = StudioPlaylist(page, url, settings)
                playlist.open()
                review_playlist(playlist, auto_remove=auto_remove)
            finally:
                browser.close()
    except (EOFError, KeyboardInterrupt):
        print("\n재생목록 확인을 멈췄어요.")
        return 130
    except (OSError, ValueError, RuntimeError) as error:
        print(f"재생목록 확인을 멈췄어요. {error}", file=sys.stderr)
        return 1
    except PlaywrightError as error:
        print("브라우저에서 작업을 마치지 못했어요. YouTube Studio 화면과 프로필 사용 여부를 확인해 주세요.", file=sys.stderr)
        print(str(error).splitlines()[0], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
