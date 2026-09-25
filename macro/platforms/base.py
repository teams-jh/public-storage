from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import logging

from config import SCREENSHOT_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class BaseUploader(ABC):
    """
    모든 SNS 플랫폼 업로더의 기본 클래스
    """
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = logging.getLogger(platform_name)

    def maximize_browser(self, page) -> None:
        """Chromium 브라우저 창을 최대화(전체 화면)합니다."""
        session = None
        try:
            session = page.context.new_cdp_session(page)
            window = session.send("Browser.getWindowForTarget")
            session.send(
                "Browser.setWindowBounds",
                {
                    "windowId": window["windowId"],
                    "bounds": {"windowState": "maximized"},
                },
            )
            self.logger.info(f"{self.platform_name} 브라우저 창을 최대화(전체 화면)했어요.")
        except Exception as error:
            self.logger.warning(f"{self.platform_name} 브라우저 창 최대화에 실패했어요: {error}")
            try:
                screen_size = page.evaluate("""() => ({
                    width: window.screen.availWidth || 1920,
                    height: window.screen.availHeight || 1080
                })""")
                if screen_size and screen_size.get("width") and screen_size.get("height"):
                    page.set_viewport_size({
                        "width": screen_size["width"],
                        "height": screen_size["height"]
                    })
                    self.logger.info(f"{self.platform_name} 뷰포트를 화면 전체 크기({screen_size['width']}x{screen_size['height']})로 설정했어요.")
            except Exception:
                pass
        finally:
            if session is not None:
                try:
                    session.detach()
                except Exception:
                    pass

    def save_result_screenshot(self, page, result: str = "success") -> Path | None:
        """브라우저 업로드 결과 화면을 macro/screenshot 폴더에 저장합니다."""
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            safe_platform = "".join(
                character.lower() if character.isalnum() else "_"
                for character in self.platform_name
            ).strip("_")
            safe_result = "".join(
                character.lower() if character.isalnum() else "_"
                for character in result
            ).strip("_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            screenshot_path = SCREENSHOT_DIR / (
                f"{safe_platform}_{safe_result}_{timestamp}.png"
            )
            page.wait_for_timeout(500)
            page.screenshot(path=str(screenshot_path), full_page=False)
            self.logger.info(f"결과 화면 저장 완료: {screenshot_path}")
            return screenshot_path
        except Exception as error:
            self.logger.error(f"결과 화면 저장에 실패했어요: {error}")
            return None

    def log_wait_progress(
        self,
        stage: str,
        elapsed_seconds: int,
        total_seconds: int,
        interval_seconds: int = 10,
    ):
        """긴 폴링 작업의 경과 시간과 남은 최대 시간을 주기적으로 기록합니다."""
        elapsed_seconds = max(0, min(elapsed_seconds, total_seconds))
        remaining_seconds = max(0, total_seconds - elapsed_seconds)
        if (
            elapsed_seconds == 0
            or elapsed_seconds == total_seconds
            or elapsed_seconds % interval_seconds == 0
        ):
            self.logger.info(
                f"{stage}: 최대 {total_seconds}초 중 {elapsed_seconds}초 경과, "
                f"최대 {remaining_seconds}초 남았어요."
            )

    def wait_with_countdown(self, page, total_seconds: int, stage: str):
        """고정 대기 시간 동안 10초 간격으로 남은 시간을 기록합니다."""
        total_seconds = max(0, int(total_seconds))
        self.log_wait_progress(stage, 0, total_seconds)
        for elapsed_seconds in range(1, total_seconds + 1):
            page.wait_for_timeout(1000)
            self.log_wait_progress(stage, elapsed_seconds, total_seconds)

    @abstractmethod
    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        미디어(동영상, 사진, GIF)와 메타데이터를 해당 플랫폼에 업로드합니다.
        
        :param media_path: 업로드할 미디어 파일 경로 (Path)
        :param metadata: {
            "title": str,
            "content": str,
            "tags": str,
            "full_caption": str,
            "time": str,
            "scheduled_at": datetime | None
        }
        :return: 업로드 성공 여부 (bool)
        """
        pass
