"""기존 YouTube 브라우저 세션으로 이미지 게시글을 작성합니다."""

import re
import time
from pathlib import Path

from config import LOGIN_TIMEOUT_SECONDS, SESSION_DIR, UPLOAD_TIMEOUT_SECONDS
from image_selection import set_and_verify_images
from platforms.base import BaseUploader
from platforms.scheduling import fill_native_date_time


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
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
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

        deadline = time.monotonic() + LOGIN_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            composer = self._composer(page)
            if composer is not None:
                return composer
            page.wait_for_timeout(500)
        raise RuntimeError("YouTube 게시글 작성창이 열리지 않았어요.")

    def _attach_images(self, page, composer, images: list[Path]) -> None:
        file_input = composer.locator("input[type='file'][accept*='image']")
        if file_input.count() == 0:
            image_button = _visible(composer.locator(
                "button[aria-label*='이미지'], button[aria-label*='Image'], "
                "[role='button'][aria-label*='이미지'], [role='button'][aria-label*='Image'], "
                "button[title*='이미지'], button[title*='Image']"
            ))
            if image_button is None:
                raise RuntimeError("이미지 추가 버튼을 찾지 못했어요.")
            image_button.click()
            file_input = composer.locator("input[type='file'][accept*='image']")
            if file_input.count() == 0:
                file_input = page.locator("input[type='file'][accept*='image']")
            file_input.first.wait_for(state="attached", timeout=10000)

        target = file_input.first
        if len(images) > 1 and target.get_attribute("multiple") is None:
            raise RuntimeError("현재 YouTube 이미지 선택창이 여러 장 첨부를 지원하지 않아요.")
        set_and_verify_images(target, images)
        page.wait_for_timeout(1500)

    def _post_button(self, composer):
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

    def _schedule(self, page, composer, scheduled_at) -> None:
        post_button = self._post_button(composer)
        if post_button is None:
            raise RuntimeError("게시글 예약 메뉴를 찾지 못했어요.")

        dropdown = _visible(post_button.locator("xpath=following-sibling::button[1]"))
        if dropdown is None:
            dropdown = _visible(composer.locator(
            "button[aria-label*='게시물 예약'], button[aria-label*='Schedule post'], "
            "button[aria-label*='예약 옵션'], button[aria-label*='Schedule options'], "
            "button[aria-haspopup='menu']"
            ))
        if dropdown is None:
            dropdown = _visible(post_button.locator("xpath=../button[last()]"))
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
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and schedule_dialog is None:
            dialogs = page.locator("[role='dialog'], tp-yt-paper-dialog")
            for index in reversed(range(dialogs.count())):
                candidate = dialogs.nth(index)
                if candidate.is_visible() and fill_native_date_time(candidate, scheduled_at):
                    schedule_dialog = candidate
                    break
            if schedule_dialog is None:
                page.wait_for_timeout(500)
        if schedule_dialog is None:
            raise RuntimeError("게시글 예약 날짜와 시간을 입력하지 못했어요.")

        schedule_button = _visible(schedule_dialog.locator(
            "button:text-is('예약'), button:text-is('Schedule'), "
            "[role='button']:text-is('예약'), [role='button']:text-is('Schedule')"
        ))
        if schedule_button is None or not schedule_button.is_enabled():
            raise RuntimeError("게시글 예약 버튼을 사용할 수 없어요.")
        schedule_button.click()

    def _publish(self, page, composer) -> None:
        post_button = self._post_button(composer)
        if post_button is None:
            raise RuntimeError("게시글의 '게시' 버튼을 찾지 못했어요.")
        deadline = time.monotonic() + UPLOAD_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
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
                caption = metadata.get("full_caption", "").strip()
                editor = _visible(composer.locator("[contenteditable='true']"))
                if editor is None:
                    raise RuntimeError("게시글 입력칸을 찾지 못했어요.")
                if caption:
                    editor.fill(caption)
                self._attach_images(page, composer, images)

                scheduled_at = metadata.get("scheduled_at")
                if scheduled_at:
                    self._schedule(page, composer, scheduled_at)
                else:
                    self._publish(page, composer)

                deadline = time.monotonic() + UPLOAD_TIMEOUT_SECONDS
                while time.monotonic() < deadline:
                    if not composer.is_visible():
                        self.logger.info("YouTube 게시글 작성창이 닫혔어요.")
                        self.save_result_screenshot(page, "scheduled" if scheduled_at else "uploaded")
                        return True
                    page.wait_for_timeout(500)
                self.logger.error("게시글 완료 화면을 확인하지 못했어요. 중복 게시를 피하려면 먼저 채널에서 확인해 주세요.")
                return False
            except Exception as exc:
                self.logger.error(f"YouTube 이미지 게시글 업로드 실패: {exc}")
                return False
            finally:
                browser.close()
