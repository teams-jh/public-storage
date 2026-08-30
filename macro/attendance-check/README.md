# 출석체크 자동화 매크로 (`attendance-check`)

`site_info.json`에 정의된 사이트별 계정 정보를 읽어와 자동으로 로그인하고 일일 출석체크를 수행하는 매크로 프로그램입니다.

---

## 📁 디렉토리 구조

```
macro/attendance-check/
├── site_info.json              # 실제 사이트 계정 정보 (Git 커밋 제외)
├── site_info.example.json      # 설정 파일 템플릿
├── config.py                   # 경로, 타임아웃, 로깅 등 공통 설정
├── run.py                      # 매크로 실행 메인 엔트리포인트 (CLI)
├── screenshots/                # 화면 캡처 디렉토리
│   ├── success/                # 출석체크 성공/이미완료 스크린샷
│   └── fail/                   # 로그인 실패, 출석 실패, 오류 스크린샷
└── sites/
    ├── __init__.py             # 사이트 핸들러 매핑 레지스트리
    ├── base.py                 # BaseAttendanceChecker 기본 추상 클래스
    └── ...                     # 사이트별 전용 핸들러들
```

---

## ⚙️ 설정 (`site_info.json`)

`site_info.json` 파일에 출석체크 대상 사이트들의 계정 및 URL 정보를 정의합니다.

```json
[
  {
    "name": "칠성몰",
    "site_key": "chilsung",
    "url": "https://mall.lottechilsung.co.kr/daily-check",
    "login_url": "https://mall.lottechilsung.co.kr/sign-in",
    "id": "아이디",
    "password": "비밀번호",
    "enabled": true
  }
]
```

- `name`: 사이트 표시 이름
- `site_key`: 사이트 고유 식별자 (`sites/`에 매핑)
- `url`: 출석체크 페이지 주소
- `login_url`: 로그인 페이지 주소 (생략 시 기본값 사용)
- `id`: 계정 아이디
- `password`: 계정 비밀번호
- `enabled`: 실행 활성화 여부 (`true` / `false`)

> [!IMPORTANT]
> `site_info.json`은 개인 로그인 정보가 포함되므로 `.gitignore`에 등록되어 Git 저장소에 커밋되지 않습니다.

---

## 🚀 실행 방법

### 1. 전체 사이트 출석체크 실행 (기본 모드: 크롬 브라우저 화면 표시)
별도 옵션 없이 실행하면 크롬 브라우저가 화면에 열리며 로그인 및 출석체크 과정을 눈으로 확인할 수 있습니다.
```bash
python run.py
```
또는 폴더 내 **`run_headed.bat`** 파일을 더블 클릭해도 동일하게 실행됩니다.

### 2. 백그라운드 무인 실행 (`--headless`)
브라우저 창을 띄우지 않고 조용히 백그라운드에서 실행하고 싶을 때 사용합니다.
```bash
python run.py --headless
```

### 3. 특정 사이트만 지정하여 실행 (`--site`)
```bash
python run.py --site 칠성몰
# 또는 키로 실행
python run.py --site chilsung
```

### 4. 지원하는 사이트 핸들러 목록 확인 (`--list`)
```bash
python run.py --list
```

---

## 🧩 신규 사이트 추가 방법 (확장 가이드)

사이트마다 로그인 입력 폼, 다이얼로그 방식, 출석 버튼 UI가 다르므로 모듈화되어 있습니다. 새 사이트를 추가하려면 아래 2단계를 진행합니다:

### 1단계: `sites/<새사이트>.py` 핸들러 생성
`BaseAttendanceChecker`를 상속받아 `login()` 및 `check_attendance()`를 구현합니다.

```python
# sites/example_site.py
from typing import Any, Dict
from playwright.sync_api import Page
from sites.base import BaseAttendanceChecker

class ExampleSiteAttendanceChecker(BaseAttendanceChecker):
    def __init__(self):
        super().__init__(site_key="example", display_name="예시사이트")

    def login(self, page: Page, site_info: Dict[str, Any]) -> tuple[bool, str]:
        page.goto(site_info["login_url"])
        page.locator("input[name='id']").fill(site_info["id"])
        page.locator("input[name='pw']").fill(site_info["password"])
        page.locator("button.login-btn").click()
        page.wait_for_timeout(2000)
        return True, "로그인 완료"

    def check_attendance(self, page: Page, site_info: Dict[str, Any]) -> Dict[str, Any]:
        page.goto(site_info["url"])
        page.locator("button.attend-btn").click()
        return {"success": True, "status": "SUCCESS", "message": "출석체크 완료"}
```

### 2단계: `sites/__init__.py`에 핸들러 등록
`SITE_REGISTRY` 딕셔너리에 사이트명과 클래스를 등록합니다.

```python
from sites.example_site import ExampleSiteAttendanceChecker

SITE_REGISTRY = {
    "chilsung": ChilsungAttendanceChecker,
    "칠성몰": ChilsungAttendanceChecker,
    "example": ExampleSiteAttendanceChecker,
    "예시사이트": ExampleSiteAttendanceChecker,
}
```
