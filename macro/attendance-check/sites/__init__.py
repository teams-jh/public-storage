from typing import Dict, Optional, Type

from sites.base import BaseAttendanceChecker
from sites.chilsung import ChilsungAttendanceChecker
from sites.kdisk import KdiskAttendanceChecker
from sites.ondisk import OndiskAttendanceChecker
from sites.filejo import FilejoAttendanceChecker
from sites.filecity import FilecityAttendanceChecker
from sites.sharebox import ShareboxAttendanceChecker

# 사이트 식별자(site_key 및 사이트 이름) 매핑 레지스트리
SITE_REGISTRY: Dict[str, Type[BaseAttendanceChecker]] = {
    # 칠성몰
    "chilsung": ChilsungAttendanceChecker,
    "칠성몰": ChilsungAttendanceChecker,
    "lottechilsung": ChilsungAttendanceChecker,
    # 케이디스크 (KDISK)
    "kdisk": KdiskAttendanceChecker,
    "k-disk": KdiskAttendanceChecker,
    "케이디스크": KdiskAttendanceChecker,
    # 온디스크 (OnDisk)
    "ondisk": OndiskAttendanceChecker,
    "on-disk": OndiskAttendanceChecker,
    "온디스크": OndiskAttendanceChecker,
    # 파일조 (FileJo)
    "filejo": FilejoAttendanceChecker,
    "file-jo": FilejoAttendanceChecker,
    "파일조": FilejoAttendanceChecker,
    # 파일시티 (FileCity)
    "filecity": FilecityAttendanceChecker,
    "file-city": FilecityAttendanceChecker,
    "파일시티": FilecityAttendanceChecker,
    # 쉐어박스 (ShareBox)
    "sharebox": ShareboxAttendanceChecker,
    "share-box": ShareboxAttendanceChecker,
    "쉐어박스": ShareboxAttendanceChecker,
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


__all__ = [
    "BaseAttendanceChecker",
    "ChilsungAttendanceChecker",
    "KdiskAttendanceChecker",
    "OndiskAttendanceChecker",
    "FilejoAttendanceChecker",
    "FilecityAttendanceChecker",
    "ShareboxAttendanceChecker",
    "get_checker",
    "SITE_REGISTRY",
]
