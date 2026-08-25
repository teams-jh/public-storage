from abc import ABC, abstractmethod
from pathlib import Path
import logging

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

    @abstractmethod
    def upload(self, media_path: Path, metadata: dict) -> bool:
        """
        미디어(동영상, 사진, GIF)와 메타데이터를 해당 플랫폼에 업로드합니다.
        
        :param media_path: 업로드할 미디어 파일 경로 (Path)
        :param metadata: {
            "title": str,
            "content": str,
            "tags": str,
            "full_caption": str
        }
        :return: 업로드 성공 여부 (bool)
        """
        pass

