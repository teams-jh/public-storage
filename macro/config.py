import os
from pathlib import Path
from dotenv import load_dotenv

# 기본 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "upload"
INPUT_FILE = BASE_DIR / "input.txt"
SESSION_DIR = BASE_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

# .env 로드
load_dotenv(BASE_DIR / ".env")

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
    input.txt 파일을 파싱하여 title, content, tags 및 통합 caption을 반환합니다.
    """
    if not filepath.exists():
        return {
            "title": "",
            "content": "",
            "tags": "",
            "full_caption": ""
        }
    
    raw_text = filepath.read_text(encoding="utf-8").strip()
    
    title = ""
    content = ""
    tags = ""
    
    # 섹션 태그([TITLE], [CONTENT], [TAGS])가 있는 경우 분리 파싱
    if "[TITLE]" in raw_text or "[CONTENT]" in raw_text or "[TAGS]" in raw_text:
        current_section = None
        sections = {"[TITLE]": [], "[CONTENT]": [], "[TAGS]": []}
        
        for line in raw_text.splitlines():
            line_strip = line.strip()
            if line_strip in sections:
                current_section = line_strip
            elif current_section:
                sections[current_section].append(line)
                
        title = "\n".join(sections["[TITLE]"]).strip()
        content = "\n".join(sections["[CONTENT]"]).strip()
        tags = "\n".join(sections["[TAGS]"]).strip()
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


