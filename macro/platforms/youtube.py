import os
import re
import time
from datetime import timezone
from pathlib import Path
from platforms.base import BaseUploader
from platforms.scheduling import (
    choose_calendar_date,
    get_scheduled_at,
)
from config import (
    CONFIG, SESSION_DIR, get_media_type, UPLOAD_TIMEOUT_SECONDS, LOGIN_TIMEOUT_SECONDS,
    get_dynamic_upload_timeout, get_dynamic_sync_buffer, get_media_size_mb
)

class YouTubeUploader(BaseUploader):
    def __init__(self):
        super().__init__("YouTube")
        self.client_secrets_file = CONFIG.get("YOUTUBE_CLIENT_SECRETS_FILE")

    def _configure_native_schedule(self, page, scheduled_at) -> bool:
        """YouTube Studio 공개 상태 화면에서 예약 날짜와 시간을 설정합니다."""
        public_radio = page.locator(
            "tp-yt-paper-radio-button[name='PUBLIC']:visible"
        )
        if public_radio.count() > 0:
            try:
                if public_radio.last.get_attribute("aria-checked") != "true":
                    public_radio.last.click(force=True)
                    page.wait_for_timeout(500)
            except Exception as error:
                self.logger.error(f"YouTube 공개 상태 선택에 실패했어요: {error}")
                return False

        visibility_select = page.locator("ytcp-video-visibility-select:visible").last
        if visibility_select.count() == 0:
            self.logger.error("YouTube 공개 상태 설정 영역을 찾지 못했어요.")
            return False

        schedule_picker = visibility_select.locator(
            "#second-container ytcp-datetime-picker:visible"
        )
        if schedule_picker.count() == 0:
            schedule_section = visibility_select.locator(
                "#second-container-expand-button:not([hidden]), "
                "#second-container .early-access-header, "
                "#second-container"
            )
            clicked = False
            for index in range(schedule_section.count()):
                target = schedule_section.nth(index)
                try:
                    if target.is_visible():
                        target.scroll_into_view_if_needed()
                        target.click(force=True)
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                self.logger.error("YouTube [예약] 영역을 펼치지 못했어요.")
                return False

            try:
                schedule_picker.wait_for(state="visible", timeout=10000)
            except Exception:
                self.logger.error("YouTube 예약 날짜·시간 입력 영역이 열리지 않았어요.")
                return False

        date_trigger = schedule_picker.locator(
            "#datepicker-trigger ytcp-dropdown-trigger[role='button'], "
            "#datepicker-trigger"
        )
        date_trigger_clicked = False
        for index in range(date_trigger.count()):
            target = date_trigger.nth(index)
            try:
                if target.is_visible():
                    target.scroll_into_view_if_needed()
                    target.click(force=True)
                    date_trigger_clicked = True
                    break
            except Exception:
                continue
        if not date_trigger_clicked:
            self.logger.error("YouTube 예약 날짜 드롭다운을 열지 못했어요.")
            return False

        page.wait_for_timeout(500)
        if not choose_calendar_date(page, scheduled_at, picker_already_open=True):
            self.logger.error("YouTube 예약 날짜를 선택하지 못했어요.")
            return False
        page.wait_for_timeout(500)
        try:
            selected_date_text = " ".join(date_trigger.last.inner_text().split())
            selected_date_numbers = [int(value) for value in re.findall(r"\d+", selected_date_text)]
            if selected_date_numbers[:3] != [
                scheduled_at.year,
                scheduled_at.month,
                scheduled_at.day,
            ]:
                self.logger.error(
                    f"YouTube 예약 날짜 확인에 실패했어요: {selected_date_text or '문구 없음'}"
                )
                return False
        except Exception as error:
            self.logger.error(f"YouTube 예약 날짜 확인에 실패했어요: {error}")
            return False

        time_input = schedule_picker.locator(
            "#time-of-day-container input:visible, tp-yt-paper-input#textbox input:visible"
        )
        if time_input.count() == 0:
            self.logger.error("YouTube 예약 시간 입력칸을 찾지 못했어요.")
            return False

        target_time = time_input.last
        try:
            current_value = target_time.input_value().strip()
            hour_12 = scheduled_at.hour % 12 or 12
            if "오전" in current_value or "오후" in current_value:
                meridiem = "오전" if scheduled_at.hour < 12 else "오후"
                time_value = f"{meridiem} {hour_12}:{scheduled_at.minute:02d}"
            elif "AM" in current_value.upper() or "PM" in current_value.upper():
                meridiem = "AM" if scheduled_at.hour < 12 else "PM"
                time_value = f"{hour_12}:{scheduled_at.minute:02d} {meridiem}"
            else:
                time_value = scheduled_at.strftime("%H:%M")

            target_time.click(force=True)
            target_time.fill(time_value)
            target_time.dispatch_event("input")
            target_time.dispatch_event("change")
            target_time.press("Tab")
            page.wait_for_timeout(700)
            selected_time_text = target_time.input_value().strip()
            time_match = re.search(r"(\d{1,2}):(\d{2})", selected_time_text)
            if not time_match:
                self.logger.error(f"YouTube 예약 시간이 입력되지 않았어요: {selected_time_text}")
                return False
            selected_hour = int(time_match.group(1))
            selected_minute = int(time_match.group(2))
            upper_time_text = selected_time_text.upper()
            if "오후" in selected_time_text or "PM" in upper_time_text:
                selected_hour = selected_hour % 12 + 12
            elif "오전" in selected_time_text or "AM" in upper_time_text:
                selected_hour %= 12
            if (selected_hour, selected_minute) != (
                scheduled_at.hour,
                scheduled_at.minute,
            ):
                self.logger.error(
                    f"YouTube 예약 시간 확인에 실패했어요: {selected_time_text}"
                )
                return False
        except Exception as error:
            self.logger.error(f"YouTube 예약 시간 입력에 실패했어요: {error}")
            return False

        self.logger.info(f"YouTube 자체 예약 공개 설정 완료: {scheduled_at:%Y-%m-%d %H:%M}")
        return True

    def _click_final_schedule_button(self, page) -> bool:
        """업로드 모달 하단의 aria-label='예약'인 실제 버튼을 클릭합니다."""
        selector = "button[aria-label='예약'][aria-disabled='false']:visible"
        buttons = page.locator(selector)
        try:
            buttons.last.wait_for(state="visible", timeout=30000)
        except Exception:
            self.logger.error("YouTube aria-label='예약' 버튼이 나타나지 않았어요.")
            return False

        candidates = []
        for index in range(buttons.count()):
            candidate = buttons.nth(index)
            try:
                box = candidate.bounding_box()
                if candidate.is_visible() and box:
                    candidates.append((box["y"], candidate))
            except Exception:
                continue
        if not candidates:
            self.logger.error("YouTube 화면에 보이는 aria-label='예약' 버튼을 찾지 못했어요.")
            return False

        # 모달 하단 버튼은 같은 이름의 다른 컨트롤보다 화면 아래에 있어요.
        target = max(candidates, key=lambda item: item[0])[1]
        target.scroll_into_view_if_needed()
        self.logger.info("YouTube aria-label='예약'인 모달 하단 버튼을 찾았어요.")

        def click_was_accepted():
            try:
                return (
                    not target.is_visible()
                    or not target.is_enabled()
                    or target.get_attribute("aria-disabled") == "true"
                )
            except Exception:
                return True

        try:
            target.click(timeout=5000)
            self.logger.info("YouTube aria-label='예약' 버튼 클릭 완료")
            page.wait_for_timeout(2500)
            if click_was_accepted():
                return True
        except Exception as error:
            self.logger.warning(f"YouTube 예약 버튼 기본 클릭 재시도 중: {error}")

        try:
            box = target.bounding_box()
            if box:
                page.mouse.click(
                    box["x"] + box["width"] / 2,
                    box["y"] + box["height"] / 2,
                )
                self.logger.info("YouTube aria-label='예약' 버튼 중앙 좌표 클릭 완료")
                page.wait_for_timeout(2500)
                if click_was_accepted():
                    return True
        except Exception as error:
            self.logger.warning(f"YouTube 예약 버튼 좌표 클릭 재시도 중: {error}")

        try:
            target.focus()
            target.press("Enter")
            self.logger.info("YouTube aria-label='예약' 버튼 Enter 입력 완료")
            page.wait_for_timeout(2500)
            if click_was_accepted():
                return True
        except Exception as error:
            self.logger.warning(f"YouTube 예약 버튼 Enter 입력 실패: {error}")

        self.logger.error("YouTube 예약 버튼을 눌렀지만 화면이 전환되지 않았어요.")
        return False

    def _close_completion_dialog(self, page) -> bool:
        """예약 등록 후 표시되는 처리 중/완료 모달의 닫기 버튼을 누릅니다."""
        close_buttons = page.get_by_role("button", name="닫기", exact=True)
        try:
            close_buttons.last.wait_for(state="visible", timeout=30000)
        except Exception:
            close_buttons = page.get_by_role("button", name="Close", exact=True)
            try:
                close_buttons.last.wait_for(state="visible", timeout=5000)
            except Exception:
                close_buttons = page.locator(
                    "#close-button button:visible, #close-button:visible, "
                    "button[aria-label='닫기']:visible, button[aria-label='Close']:visible"
                )
                try:
                    close_buttons.last.wait_for(state="visible", timeout=5000)
                except Exception:
                    self.logger.error("YouTube 처리 완료 모달의 [닫기] 버튼을 찾지 못했어요.")
                    return False

        visible_buttons = []
        for index in range(close_buttons.count()):
            candidate = close_buttons.nth(index)
            try:
                box = candidate.bounding_box()
                if candidate.is_visible() and box:
                    visible_buttons.append((box["y"], candidate))
            except Exception:
                continue
        if not visible_buttons:
            self.logger.error("YouTube 화면에 보이는 [닫기] 버튼을 찾지 못했어요.")
            return False

        target = max(visible_buttons, key=lambda item: item[0])[1]
        try:
            target.scroll_into_view_if_needed()
            target.click(timeout=5000)
        except Exception:
            try:
                target.click(force=True, timeout=3000)
            except Exception:
                try:
                    target.evaluate("element => element.click()")
                except Exception as error:
                    self.logger.error(f"YouTube [닫기] 버튼 클릭에 실패했어요: {error}")
                    return False

        try:
            target.wait_for(state="hidden", timeout=10000)
        except Exception:
            self.logger.error("YouTube [닫기] 클릭 후 처리 완료 모달이 닫히지 않았어요.")
            return False

        self.logger.info("YouTube 처리 완료 모달 [닫기] 버튼 클릭 완료")
        return True

    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        YouTube 동영상 / 쇼츠 업로드
        (YouTube는 동영상 파일만 지원하므로 사진/GIF의 경우 건너뜁니다)
        1. Google YouTube Data API v3 (가장 안정적 & OAuth 토큰 저장)
        2. Playwright YouTube Studio 웹 자동화
        """
        media_type = get_media_type(media_path)
        if media_type != "video":
            self.logger.warning(
                f"YouTube는 동영상(.mp4, .mov 등) 파일만 지원하므로 "
                f"이미지/GIF 파일({media_path.name})은 업로드를 건너뜁니다."
            )
            return True

        title = metadata.get("title", media_path.stem)
        content = metadata.get("content", "")
        tags_raw = metadata.get("tags", "")
        # 해시태그 목록 추출
        tags = [t.strip("# ").strip() for t in tags_raw.split() if t.strip()]

        # 유튜브 설명(Description)에는 [TITLE]을 제외하고 [CONTENT]와 [TAGS]만 포함
        desc_parts = []
        if content:
            desc_parts.append(content)
        if tags_raw:
            desc_parts.append(tags_raw)
        description = "\n\n".join(desc_parts).strip()
        scheduled_at = get_scheduled_at(metadata)

        self.logger.info(f"YouTube 업로드 시작: {media_path.name}")
        self.logger.info(f"제목: {title}")
        self.logger.info(f"설명 내용 요약:\n{description[:100]}...")

        # 방법 1: YouTube Data API v3
        secrets_path = Path(self.client_secrets_file)
        if secrets_path.exists():
            try:
                self.logger.info("YouTube Data API v3를 통해 업로드를 시작합니다...")
                return self._upload_via_api(media_path, title, description, tags, scheduled_at)
            except Exception as e:
                self.logger.error(f"YouTube API 업로드 중 오류: {e}. Playwright 모드로 전환합니다.")

        # 방법 2: Playwright 웹 브라우저 자동화
        return self._upload_via_playwright(media_path, title, description, scheduled_at)

    def _upload_via_api(self, video_path: Path, title: str, description: str, tags: list, scheduled_at=None) -> bool:
        import pickle
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        token_file = SESSION_DIR / "youtube_token.pickle"
        creds = None

        if token_file.exists():
            with open(token_file, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_file), SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],  # 유튜브 제목 100자 제한
                "description": description,
                "tags": tags,
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": "private" if scheduled_at else "public",
                "selfDeclaredMadeForKids": False
            }
        }
        if scheduled_at:
            publish_at = scheduled_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            body["status"]["publishAt"] = publish_at
            self.logger.info(f"YouTube 자체 예약 공개 시각 설정: {scheduled_at:%Y-%m-%d %H:%M}")

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        self.logger.info("동영상 업로드 진행 중...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                self.logger.info(f"업로드 진행률: {progress}%")

        result_name = "예약 업로드" if scheduled_at else "업로드"
        self.logger.info(f"YouTube {result_name} 완료! Video ID: {response.get('id')}")
        self.logger.info(f"URL: https://youtu.be/{response.get('id')}")
        return True

    def _upload_via_playwright(self, video_path: Path, title: str, description: str, scheduled_at=None) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            user_data_dir = SESSION_DIR / "browser_youtube"
            user_data_dir.mkdir(exist_ok=True)

            size_mb = get_media_size_mb(video_path)
            upload_timeout = get_dynamic_upload_timeout(video_path)
            sync_buffer = get_dynamic_sync_buffer(video_path)

            self.logger.info(f"YouTube Studio 브라우저를 실행합니다... (파일 크기: {size_mb:.2f}MB, 동적 대기: {upload_timeout}초, 완료 후 세션유지: {sync_buffer}초)")
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.new_page()
                page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)


                # 로그인 확인 (최대 180초 대기)
                if "accounts.google.com" in page.url:
                    self.logger.info(f"Google 로그인이 필요합니다. 브라우저에서 로그인해 주세요 (최대 {LOGIN_TIMEOUT_SECONDS}초 대기)...")
                    try:
                        page.wait_for_url("https://studio.youtube.com/**", timeout=LOGIN_TIMEOUT_SECONDS * 1000)
                    except Exception:
                        self.logger.error("YouTube 로그인 대기 시간이 초과되었습니다.")
                        browser.close()
                        return False

                self.logger.info("만들기 버튼 클릭 및 파일 업로드...")
                page.wait_for_timeout(3000)

                # 만들기 버튼
                create_btn = page.locator("#create-icon, button:has-text('만들기'), button:has-text('CREATE')")
                if create_btn.count() > 0:
                    create_btn.first.click()
                    page.wait_for_timeout(1000)
                    upload_menu = page.locator("tp-yt-paper-item:has-text('동영상 업로드'), tp-yt-paper-item:has-text('Upload videos')")
                    if upload_menu.count() > 0:
                        upload_menu.first.click()
                        page.wait_for_timeout(2000)

                # 파일 선택 input
                file_input = page.locator("input[type='file']")
                if file_input.count() > 0:
                    file_input.first.set_input_files(str(video_path.resolve()))
                    self.logger.info(f"동영상 파일 첨부 완료! 서버 업로드 및 인코딩 진행 대기 중 (최대 {upload_timeout}초)...")
                    page.wait_for_timeout(5000)

                    # 제목 입력
                    title_input = page.locator("#title-textarea #textbox")
                    if title_input.count() > 0:
                        title_input.first.fill(title)
                        self.logger.info("동영상 제목 입력 완료")

                    # 설명 입력
                    desc_input = page.locator("#description-textarea #textbox")
                    if desc_input.count() > 0:
                        desc_input.first.fill(description)
                        self.logger.info("동영상 설명 입력 완료")

                    # '아동용이 아닙니다' 라디오 버튼 클릭
                    not_for_kids = page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']")
                    if not_for_kids.count() > 0:
                        not_for_kids.first.click()

                    # 유튜브 하단 서버 업로드 완료율 대기 (0% -> 100% / 업로드 완료 / 처리 중)
                    self.logger.info("YouTube 서버로 동영상 파일 전송 완료 대기 중...")
                    for _ in range(upload_timeout // 3):
                        page.wait_for_timeout(3000)
                        upload_status = page.locator("span.progress-label, div.progress-label, span:has-text('업로드 완료'), span:has-text('처리 완료'), span:has-text('검사 완료')")
                        if upload_status.count() > 0:
                            status_text = upload_status.first.inner_text()
                            if any(k in status_text for k in ["업로드 완료", "처리", "검사", "완료", "100%"]):
                                self.logger.info(f"동영상 업로드 상태 확인: {status_text}")
                                break

                    # 다음 버튼 3회 클릭 (세부정보 -> 동영상 요소 -> 검사 -> 공개 상태)
                    for step in range(3):
                        next_btn = page.locator("#next-button")
                        if next_btn.count() > 0:
                            next_btn.first.click()
                            page.wait_for_timeout(2000)

                    if scheduled_at:
                        if not self._configure_native_schedule(page, scheduled_at):
                            browser.close()
                            return False
                    else:
                        # 공개(Public) 라디오 버튼 클릭
                        public_radio = page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
                        if public_radio.count() > 0:
                            public_radio.first.click()
                            page.wait_for_timeout(1000)

                    # 모달 하단의 게시/예약 버튼 클릭
                    if scheduled_at:
                        action_name = "예약"
                        if not self._click_final_schedule_button(page):
                            browser.close()
                            return False
                    else:
                        action_name = "게시"
                        done_btn = page.locator("#done-button button:visible, #done-button:visible")
                        try:
                            done_btn.last.wait_for(state="visible", timeout=30000)
                        except Exception:
                            pass
                        if done_btn.count() == 0:
                            self.logger.error("YouTube 모달 하단의 게시 버튼을 찾지 못했어요.")
                            browser.close()
                            return False
                        done_host = done_btn.last
                        inner_done_button = done_host.locator("button:visible")
                        click_target = (
                            inner_done_button.last
                            if inner_done_button.count() > 0
                            else done_host
                        )
                        button_ready = False
                        for _ in range(30):
                            try:
                                if (
                                    click_target.is_enabled()
                                    and click_target.get_attribute("aria-disabled") != "true"
                                    and done_host.get_attribute("aria-disabled") != "true"
                                ):
                                    button_ready = True
                                    break
                            except Exception:
                                pass
                            page.wait_for_timeout(1000)
                        if not button_ready:
                            self.logger.error(f"YouTube [{action_name}] 버튼이 활성화되지 않았어요.")
                            browser.close()
                            return False

                        click_target.scroll_into_view_if_needed()
                        clicked = False
                        try:
                            button_box = click_target.bounding_box()
                            if button_box:
                                page.mouse.click(
                                    button_box["x"] + button_box["width"] / 2,
                                    button_box["y"] + button_box["height"] / 2,
                                )
                                clicked = True
                                self.logger.info(f"YouTube 모달 하단 [{action_name}] 버튼 중앙 좌표 클릭 완료")
                        except Exception:
                            pass
                        if not clicked:
                            try:
                                click_target.click(force=True)
                                clicked = True
                            except Exception:
                                try:
                                    click_target.evaluate("element => element.click()")
                                    clicked = True
                                except Exception:
                                    pass
                        if not clicked:
                            self.logger.error(f"YouTube [{action_name}] 버튼 클릭에 실패했어요.")
                            browser.close()
                            return False

                    self.logger.info(f"{action_name} 버튼 클릭 완료! 서버 처리 및 링크 생성 대기 중 (최대 {upload_timeout}초)...")

                    # 업로드 완료 및 링크 생성 확인 대기 (최대 upload_timeout초)
                    yt_done = False
                    for _ in range(upload_timeout):
                        page.wait_for_timeout(1000)
                        # 완료 다이얼로그에 유튜브 링크 또는 닫기 버튼이 생성된 경우
                        yt_link = page.locator("a[href*='youtu.be'], a.ytcp-video-info")
                        close_btn = page.locator("#close-button, button:has-text('닫기'), button:has-text('Close')")

                        if yt_link.count() > 0:
                            href = yt_link.first.get_attribute("href") or ""
                            self.logger.info(f"🎉 YouTube 동영상 게시 완료! 링크: {href}")
                            yt_done = True
                            break
                        elif close_btn.count() > 0 and close_btn.first.is_visible():
                            yt_done = True
                            self.logger.info("🎉 YouTube 동영상 게시 완료 확인 (완료 창 노출)!")
                            break

                    if yt_done:
                        if not self._close_completion_dialog(page):
                            browser.close()
                            return False
                        # 백그라운드 전송 유실 방지를 위한 파일 크기 비례 안전 대기
                        self.logger.info(f"업로드 세션 안전 동기화 중 ({sync_buffer}초간 넉넉하게 대기)...")
                        page.wait_for_timeout(sync_buffer * 1000)
                        result_name = "예약 업로드" if scheduled_at else "업로드"
                        self.logger.info(f"🎉 YouTube 최종 {result_name} 완료!")
                        browser.close()
                        return True
                    else:
                        self.logger.warning("YouTube 서버 처리 완료 확인을 받지 못했습니다.")
                        page.wait_for_timeout(5000)
                        browser.close()
                        return False

                self.logger.error("YouTube 업로드 input을 찾지 못했습니다.")
                page.wait_for_timeout(5000)
                browser.close()
                return False



        except Exception as e:
            self.logger.error(f"Playwright YouTube 업로드 실패: {e}")
            return False

