import json
import logging
from pathlib import Path
from typing import Any, Dict, List

# ==========================================
# Directory & File Paths
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent.parent

SITE_INFO_PATH = BASE_DIR / "site_info.json"
SITE_INFO_EXAMPLE_PATH = BASE_DIR / "site_info.example.json"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SESSIONS_DIR = BASE_DIR / "sessions"

# Create required directories
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# Browser & Automation Constants
# ==========================================
DEFAULT_TIMEOUT_MS = 30000
DEFAULT_HEADLESS = False  # 기본값: 브라우저 창 화면에 표시 (Headed 모드)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_VIEWPORT = {"width": 1280, "height": 900}

# ==========================================
# Retry Policy Constants
# ==========================================
MAX_RETRY_ROUNDS = 1  # 전체 사이트 순회 후 실패한 사이트에 대해 재시도할 횟수 (1회)
RETRY_DELAY_SEC = 2   # 재시도 라운드 시작 전 대기 시간 (초)


def setup_logger(name: str = "attendance_checker", level: int = logging.INFO) -> logging.Logger:
    """
    출석체크 매크로 표준 로거를 설정하고 반환합니다.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def load_site_info(file_path: Path = SITE_INFO_PATH) -> List[Dict[str, Any]]:
    """
    site_info.json 파일에서 사이트 계정 및 URL 정보를 로드합니다.
    """
    if not file_path.exists():
        if SITE_INFO_EXAMPLE_PATH.exists():
            raise FileNotFoundError(
                f"'{file_path.name}' 파일이 존재하지 않습니다. "
                f"'{SITE_INFO_EXAMPLE_PATH.name}'을 복사하여 계정 정보를 작성해주세요."
            )
        raise FileNotFoundError(f"사이트 설정 파일이 존재하지 않습니다: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("site_info.json 파일은 사이트 객체들의 배열(JSON Array) 형태여야 합니다.")

    return data
