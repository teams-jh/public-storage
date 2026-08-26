# 🚀 Multi-Platform SNS Media Uploader Macro

`macro/upload/` 폴더 내의 미디어(동영상, 사진, GIF)와 `macro/input.txt`의 본문 내용을 바탕으로 **인스타그램(Instagram), 쓰레드(Threads), X(Twitter), 페이스북(Facebook), 틱톡(TikTok), 유튜브(YouTube)** 에 자동으로 게시물을 업로드하는 통합 Python 매크로입니다.

---

## 📁 폴더 및 파일 구조

```
macro/
├── upload/                     # 🎬 업로드할 미디어 파일(동영상 .mp4/.mov, 사진 .jpg/.png/.webp, GIF .gif)을 넣는 폴더
├── input.txt                   # 📝 업로드할 제목, 본문, 태그를 입력하는 텍스트 파일
├── auto_upload.py              # 🚀 메인 실행 스크립트
├── config.py                   # ⚙️ 설정 로더 및 파일 탐색/파싱 함수
├── requirements.txt            # 📦 필요한 Python 라이브러리 목록
├── .env.example                # 🔑 환경 변수/계정 설정 템플릿
├── platforms/                  # 🌐 플랫폼별 업로더 모듈
│   ├── base.py                 # 업로더 추상 기본 클래스
│   ├── instagram.py            # 인스타그램 (사진/릴스/피드)
│   ├── threads.py              # 쓰레드 (Threads)
│   ├── x_twitter.py            # X (Twitter)
│   ├── facebook.py             # 페이스북 (사진/피드/페이지/릴스)
│   ├── tiktok.py               # 틱톡 (TikTok Studio)
│   └── youtube.py              # 유튜브 (쇼츠/동영상 - 동영상 전용)
└── sessions/                   # 💾 브라우저 쿠키 및 로그인 세션 저장소 (자동 생성)
```

---

## 🎨 지원하는 미디어 포맷

- **동영상 (Video)**: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- **사진 (Image)**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`
- **GIF 애니메이션**: `.gif`

---

## 🛠️ 1. 사전 준비 및 패키지 설치

### 1) Python 라이브러리 설치
터미널에서 아래 명령어를 실행하여 필수 의존성을 설치합니다:

```bash
cd macro
pip install -r requirements.txt
```

### 2) Playwright 브라우저 바이너리 설치
웹 브라우저 자동화를 위한 Chromium 브라우저를 설치합니다:

```bash
playwright install chromium
```

---

## 📝 2. 입력 데이터 설정

### `input.txt` 작성법
`macro/input.txt` 파일에 아래와 같이 `[TITLE]`, `[CONTENT]`, `[TAGS]`, `[RATIO]` 형식으로 작성합니다:

```txt
[TITLE]
오늘의 게시물 업로드 예시

[CONTENT]
안녕하세요! 오늘 소개해드릴 소식/영상입니다.
재미있게 보셨다면 좋아요와 팔로우 부탁드려요!

[TAGS]
#일상 #피드 #소통 #릴스 #쇼츠 #틱톡 #shorts #reels #tiktok

[RATIO]
9:16
```
> **💡 비율(RATIO) 설정:**
> - `9:16`: 인스타그램 릴스/세로 화면 기본 비율 (기본값)
> - `1:1`: 정사각형 피드 비율
> - `16:9`: 가로 비율
> - `원본`: 미디어 원본 비율 유지

### 미디어 파일 배치
업로드할 파일(`sample.mp4`, `image.jpg`, `animation.gif` 등)을 `macro/upload/` 폴더에 넣어둡니다.
지정하지 않을 경우 폴더 내 첫 번째 미디어가 자동으로 선택됩니다.

---

## 🔑 3. 계정 및 환경 변수 설정 (`.env`)

`macro/.env.example` 파일을 복사하여 `macro/.env`를 생성하고 계정 정보 또는 API 토큰을 입력합니다:

```bash
cp .env.example .env
```

```ini
# Instagram & Threads
INSTAGRAM_USERNAME=your_id
INSTAGRAM_PASSWORD=your_pw

# X (Twitter)
TWITTER_USERNAME=your_x_id
TWITTER_PASSWORD=your_x_pw

# Facebook
FACEBOOK_EMAIL=your_email
FACEBOOK_PASSWORD=your_pw

# TikTok
TIKTOK_USERNAME=your_tiktok_id
TIKTOK_PASSWORD=your_tiktok_pw

# YouTube
# Google Cloud Console에서 다운로드한 OAuth 2.0 클라이언트 JSON 파일명
YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json
```

> **💡 브라우저 세션 보존 기능:**
> 2단계 인증(2FA/SMS)이 필요한 플랫폼의 경우 최초 실행 시 열리는 브라우저 화면에서 한 번만 로그인하시면 `sessions/` 폴더에 세션 쿠키가 저장되어 이후에는 로그인 없이 바로 자동 업로드됩니다.

---

## 🏃 4. 실행 방법

### 1) 6대 SNS 전체 일괄 업로드
```bash
python auto_upload.py
```

### 2) 특정 플랫폼만 선택하여 업로드
`--platform` (`-p`) 옵션을 사용하여 원하는 플랫폼만 업로드할 수 있습니다:

```bash
# 인스타그램만 업로드
python auto_upload.py -p instagram

# 쓰레드만 업로드
python auto_upload.py -p threads

# X(Twitter)만 업로드
python auto_upload.py -p x

# 페이스북만 업로드
python auto_upload.py -p facebook

# 틱톡만 업로드
python auto_upload.py -p tiktok

# 유튜브만 업로드
python auto_upload.py -p youtube
```

### 3) 특정 미디어 파일(사진/GIF/동영상) 직접 지정
`-f`, `-m`, `-v` (`--file`, `--media`, `--video`) 옵션으로 원하는 파일을 직접 지정할 수 있습니다:
```bash
# 사진 파일 지정 업로드
python auto_upload.py -f upload/my_photo.png

# GIF 파일 지정 업로드
python auto_upload.py -m upload/my_animation.gif

# 동영상 파일 지정 업로드
python auto_upload.py -v upload/my_special_video.mp4
```

---

## ⚡ 플랫폼별 작동 방식 요약

| 플랫폼 | 지원 미디어 | 기본 동작 방식 | 설명 |
| :--- | :--- | :--- | :--- |
| **Instagram** | 동영상, 사진, GIF | `instagrapi` / Playwright | 릴스(`clip_upload`), 사진(`photo_upload`) 또는 웹 자동화 게시 |
| **Threads** | 동영상, 사진, GIF | Playwright / Threads API | 본문 및 미디어(영상/사진/GIF) 첨부 후 즉시 게시 |
| **X (Twitter)** | 동영상, 사진, GIF | `tweepy` / Playwright | 미디어 카테고리(`tweet_image`, `tweet_gif`, `tweet_video`) 자동 분류 업로드 및 트윗 |
| **Facebook** | 동영상, 사진, GIF | Graph API / Playwright | 사진(`/photos`), 비디오(`/videos`) API 엔드포인트 분기 및 피드 자동 게시 |
| **TikTok** | 동영상, 사진 | Playwright (TikTok Studio) | 틱톡 스튜디오를 통한 비디오 및 사진 모드 자동 게시 |
| **YouTube** | 동영상 전용 | YouTube Data API v3 / Playwright | 쇼츠/동영상 업로드 (사진/GIF 감지 시 자동 스킵 안내) |

