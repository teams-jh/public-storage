from typing import Dict, Optional, Type

from sites.base import BaseAttendanceChecker
from sites.chilsung import ChilsungAttendanceChecker

# 사이트 식별자(site_key 및 사이트 이름) 매핑 레지스트리
SITE_REGISTRY: Dict[str, Type[BaseAttendanceChecker]] = {
    # 칠성몰
    "chilsung": ChilsungAttendanceChecker,
    "칠성몰": ChilsungAttendanceChecker,
    "lottechilsung": ChilsungAttendanceChecker,
}


def get_checker(site_key_or_name: str) -> Optional[BaseAttendanceChecker]:
    """
    사이트 키 또는 사이트 이름으로 등록된 출석체크 핸들러 인스턴스를 반환합니다.
    """
    normalized_key = site_key_or_name.strip().lower()
    checker_cls = SITE_REGISTRY.get(normalized_key) or SITE_REGISTRY.get(site_key_or_name.strip())
    if checker_cls:
        return checker_cls()
    return None


__all__ = ["BaseAttendanceChecker", "ChilsungAttendanceChecker", "get_checker", "SITE_REGISTRY"]
