import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 기본 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent


def resolve_macro_path(environment_name: str, default_name: str) -> Path:
    """환경 변수의 절대/상대 경로를 macro 폴더 기준 경로로 변환합니다."""
    configured_path = Path(os.getenv(environment_name, default_name))
    return configured_path if configured_path.is_absolute() else BASE_DIR / configured_path


UPLOAD_DIR = resolve_macro_path("MACRO_UPLOAD_DIR", "upload")
INPUT_FILE = resolve_macro_path("MACRO_INPUT_FILE", "input.txt")
SESSION_DIR = resolve_macro_path("MACRO_SESSION_DIR", "sessions")
SCREENSHOT_DIR = resolve_macro_path("MACRO_SCREENSHOT_DIR", "screenshot")
SESSION_DIR.mkdir(exist_ok=True)

# 두 번째 계정처럼 브라우저 프로필 로그인이 필요한 실행에서는 API와 자동 로그인을 사용하지 않습니다.
FORCE_BROWSER_UPLOAD = os.getenv("MACRO_FORCE_BROWSER_UPLOAD", "0") == "1"
DISABLE_AUTO_LOGIN = os.getenv("MACRO_DISABLE_AUTO_LOGIN", "0") == "1"

# .env 로드
load_dotenv(BASE_DIR / ".env")

# ==========================================
# Global Timeout Constants & Dynamic Helpers
# ==========================================
# 기본 업로드 제한시간 (초 단위: 180초 = 3분)
UPLOAD_TIMEOUT_SECONDS = 180

# 로그인 및 2단계 인증 대기 최대 시간 (초 단위: 180초 = 3분)
LOGIN_TIMEOUT_SECONDS = 180

# input.txt의 [TIME] 예약 시각 형식입니다. 연-월-일 시:분 단위이며 로컬 시간대를 사용합니다.
SCHEDULE_TIME_FORMAT = "%Y-%m-%d %H:%M"

# Instagram 자체 예약 기능이 허용하는 최대 예약 범위입니다. 단위는 일이며,
# 값을 늘려도 Instagram 계정/서비스 제한을 넘으면 예약 등록이 거절됩니다.
INSTAGRAM_SCHEDULE_MAX_DAYS = 75

# TikTok 웹 예약 기능이 허용하는 최소 예약 간격입니다. 단위는 분이며,
# 이 값보다 가까운 시각은 TikTok에서 예약할 수 없어 즉시 게시 방지를 위해 실패 처리합니다.
TIKTOK_SCHEDULE_MIN_MINUTES = 15

# TikTok 웹 예약 기능이 허용하는 최대 예약 범위입니다. 단위는 일이며,
# 이 값보다 먼 시각은 TikTok에서 예약할 수 없어 즉시 게시 방지를 위해 실패 처리합니다.
TIKTOK_SCHEDULE_MAX_DAYS = 10

# Instagram 게시물 작성 시 AI 생성 콘텐츠 레이블을 항상 활성화합니다.
# 웹 작성 화면에서만 토글 상태를 검증할 수 있으므로 True이면 브라우저 업로드를 사용합니다.
INSTAGRAM_AI_LABEL_ENABLED = True


def parse_scheduled_time(value: str) -> datetime | None:
    """[TIME] 값을 로컬 datetime으로 변환합니다. 빈 값은 None을 반환합니다."""
    value = value.strip()
    if not value:
        return None
    return datetime.strptime(value, SCHEDULE_TIME_FORMAT)

def get_media_size_mb(filepath: Path) -> float:
    """미디어 파일 크기를 MB 단위(실수)로 반환합니다."""
    if not filepath.exists():
        return 0.0
    return filepath.stat().st_size / (1024 * 1024)

def get_dynamic_upload_timeout(filepath: Path) -> int:
    """
    미디어 파일 크기 및 종류에 따른 동적 업로드 제한시간을 계산합니다 (초 단위).
    - 사진/이미지: 기본 180초 (3분)
    - 동영상: 용량(MB)에 비례하여 동적 확장 (기본 180초 + 1MB당 5초, 최대 1800초 = 30분)
      예: 10MB -> 230초, 50MB -> 430초, 100MB -> 680초
    """
    if not is_video(filepath):
        return UPLOAD_TIMEOUT_SECONDS
    
    size_mb = get_media_size_mb(filepath)
    dynamic_timeout = max(UPLOAD_TIMEOUT_SECONDS, int(size_mb * 5) + 180)
    return min(1800, dynamic_timeout)

def get_dynamic_sync_buffer(filepath: Path) -> int:
    """
    업로드 및 게시 완료 후 백그라운드 패킷 유실을 방지하기 위한 세션 유지 대기시간을 계산합니다 (초 단위).
    - 사진/이미지: 20초 넉넉 대기
    - 동영상: 용량(MB)에 비례하여 30초 ~ 180초(3분)까지 넉넉하게 세션 유지
      예: 10MB -> 40초, 50MB -> 80초, 100MB -> 130초
    """
    if not is_video(filepath):
        return 20
    
    size_mb = get_media_size_mb(filepath)
    dynamic_buffer = max(30, int(size_mb * 1) + 30)
    return min(180, dynamic_buffer)


# 자격 증명 설정

CONFIG = {
    # Instagram & Threads
    "INSTAGRAM_USERNAME": os.getenv("INSTAGRAM_USERNAME", ""),
    "INSTAGRAM_PASSWORD": os.getenv("INSTAGRAM_PASSWORD", ""),
    "META_ACCESS_TOKEN": os.getenv("META_ACCESS_TOKEN", ""),
    "INSTAGRAM_ACCOUNT_ID": os.getenv("INSTAGRAM_ACCOUNT_ID", ""),
    "FACEBOOK_PAGE_ID": os.getenv("FACEBOOK_PAGE_ID", ""),
    "THREADS_USER_ID": os.getenv("THREADS_USER_ID", ""),
    
    # X (Twitter)
    "TWITTER_USERNAME": os.getenv("TWITTER_USERNAME", ""),
    "TWITTER_PASSWORD": os.getenv("TWITTER_PASSWORD", ""),
    "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY", ""),
    "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET", ""),
    "TWITTER_ACCESS_TOKEN": os.getenv("TWITTER_ACCESS_TOKEN", ""),
    "TWITTER_ACCESS_TOKEN_SECRET": os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""),
    
    # Facebook
    "FACEBOOK_EMAIL": os.getenv("FACEBOOK_EMAIL", ""),
    "FACEBOOK_PASSWORD": os.getenv("FACEBOOK_PASSWORD", ""),
    
    # TikTok
    "TIKTOK_USERNAME": os.getenv("TIKTOK_USERNAME", ""),
    "TIKTOK_PASSWORD": os.getenv("TIKTOK_PASSWORD", ""),
    "TIKTOK_ACCESS_TOKEN": os.getenv("TIKTOK_ACCESS_TOKEN", ""),
    
    # YouTube
    "YOUTUBE_CLIENT_SECRETS_FILE": str(BASE_DIR / os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")),
}

def parse_input_file(filepath: Path = INPUT_FILE) -> dict:
    """
    input.txt 파일을 파싱하여 title, content, tags, ratio, time 및 통합 caption을 반환합니다.
    """
    if not filepath.exists():
        return {
            "title": "",
            "content": "",
            "tags": "",
            "ratio": "9:16",
            "time": "",
            "full_caption": ""
        }
    
    raw_text = filepath.read_text(encoding="utf-8").strip()
    
    title = ""
    content = ""
    tags = ""
    ratio = ""
    scheduled_time = ""
    
    # 섹션 태그([TITLE], [CONTENT], [TAGS], [RATIO], [TIME])가 있는 경우 분리 파싱
    if any(section in raw_text for section in ("[TITLE]", "[CONTENT]", "[TAGS]", "[RATIO]", "[TIME]")):
        current_section = None
        sections = {
            "[TITLE]": [],
            "[CONTENT]": [],
            "[TAGS]": [],
            "[RATIO]": [],
            "[TIME]": [],
        }
        
        for line in raw_text.splitlines():
            line_strip = line.strip()
            if line_strip in sections:
                current_section = line_strip
            elif current_section:
                sections[current_section].append(line)
                
        title = "\n".join(sections["[TITLE]"]).strip()
        content = "\n".join(sections["[CONTENT]"]).strip()
        tags = "\n".join(sections["[TAGS]"]).strip()
        ratio = "\n".join(sections["[RATIO]"]).strip()
        scheduled_time = "\n".join(sections["[TIME]"]).strip()
    else:
        # 섹션 태그가 없는 경우 첫 줄을 제목, 나머지를 본문으로 처리
        lines = raw_text.splitlines()
        if lines:
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            
    full_caption_parts = []
    if title:
        full_caption_parts.append(title)
    if content:
        full_caption_parts.append(content)
    if tags:
        full_caption_parts.append(tags)
        
    full_caption = "\n\n".join(full_caption_parts).strip()
    
    return {
        "title": title or "업로드 영상",
        "content": content or raw_text,
        "tags": tags,
        "ratio": ratio or "9:16",
        "time": scheduled_time,
        "full_caption": full_caption or raw_text
    }

# 지원하는 미디어 파일 확장자
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".jfif", ".tiff"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS

def is_video(filepath: Path) -> bool:
    """파일이 동영상인지 여부를 확인합니다."""
    return filepath.suffix.lower() in VIDEO_EXTENSIONS

def get_media_type(filepath: Path) -> str:
    """
    파일 확장자를 기반으로 미디어 타입을 반환합니다.
    동영상 파일이 아니면 모두 'image'(사진)으로 판단합니다.
    """
    if is_video(filepath):
        return "video"
    return "image"

def get_target_media(upload_dir: Path = UPLOAD_DIR) -> list[Path]:
    """
    upload 디렉토리에서 업로드 대상 미디어 파일 목록(동영상 또는 사진)을 가져옵니다.
    """
    if not upload_dir.exists():
        return []
    
    media_files = [
        f for f in upload_dir.iterdir()
        if f.is_file() and (f.suffix.lower() in SUPPORTED_EXTENSIONS or not is_video(f))
    ]
    return sorted(media_files)

def get_target_videos(upload_dir: Path = UPLOAD_DIR) -> list[Path]:
    """
    (하위 호환성 유지) upload 디렉토리에서 업로드 대상 파일 목록을 가져옵니다.
    """
    return get_target_media(upload_dir)
