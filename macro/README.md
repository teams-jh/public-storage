# 🚀 Multi-Platform SNS Media Uploader Macro

`macro/upload/` 폴더 내의 미디어(동영상, 사진, GIF)와 `macro/input.txt`의 본문 내용을 바탕으로 **인스타그램(Instagram), 쓰레드(Threads), X(Twitter), 페이스북(Facebook), 틱톡(TikTok), 유튜브(YouTube), 네이버 클립(Naver Clip)** 에 자동으로 게시물을 업로드하는 통합 Python 매크로입니다.

---

## 유튜브 MP4 일괄 업로드

`youtube_upload/` 폴더에 MP4를 넣고 `youtube_input.txt`에 영상마다 아래 태그를 반복해서 적어 주세요.
파일명 숫자 순서(`1.mp4`, `2.mp4`, `10.mp4`)로 첫 번째 영상에 첫 번째 입력을 연결해요.
대소문자와 관계없이 `.mp4` 파일만 대상으로 하고, 하위 폴더와 다른 확장자는 제외해요.
순서를 고정하려면 `01_제목.mp4`, `02_제목.mp4`처럼 번호를 붙여 주세요.

```text
[TITLE]
첫 번째 제목

[CONTENT]
첫 번째 영상 설명
여러 줄로 적어도 돼요.

[TIME]
2026-11-01 20:30

---

[TITLE]
두 번째 제목

[CONTENT]
두 번째 영상 설명

[TIME]
2026-11-02 20:30
```

저장소 루트에서 연결 순서를 먼저 확인할 수 있어요.

```bash
python macro/youtube_batch_upload.py --dry-run
```

실제로 업로드하려면 아래 명령어를 실행해 주세요. 기존 유튜브 업로더의 계정·로그인 세션·API/브라우저 설정을 사용하고, 유튜브에만 하나씩 업로드해요.

```bash
python macro/youtube_batch_upload.py
```

두 번째 계정은 `auto_upload2.py`와 같은 `sessions2/` 로그인 세션과 `screenshot2/` 저장 경로를 사용해요.
`youtube_input.txt`와 `youtube_upload/`는 첫 번째 실행 파일과 공유해요.
브라우저 업로드로 실행하고 자동 로그인은 사용하지 않아요. 검증과 20초 뒤 재시도도 동일하게 적용해요.

```bash
python macro/youtube_batch_upload2.py --dry-run
python macro/youtube_batch_upload2.py
```

- MP4 수와 `[TITLE]`, `[CONTENT]`, `[TIME]` 수가 모두 같아야 해요. 다르면 각 개수를 알려주고 업로드 전에 중단해요.
- 모든 게시물은 `[TITLE]` → `[CONTENT]` → `[TIME]` 순서로 작성해 주세요. 게시물 사이 `---`는 생략해도 돼요.
- 제목은 비워둘 수 없고, 본문은 여러 줄 또는 빈 값으로 적을 수 있어요.
- `[TIME]` 태그는 필수예요. 값을 비우면 바로 게시하고, 미래 시각을 적으면 유튜브 자체 예약 기능으로 등록해요. 시간대는 실행 PC의 로컬 시간대예요.
- 잘못된 시각이나 지난 시각이 있으면 전체 업로드 전에 중단해요. 진행 중 예약 시각이 지나도 다음 영상 전에 멈춰요.
- 업로드 실패 시 업로더가 실패를 반환한 뒤 20초 기다리고 같은 영상을 한 번 재시도해요. 재시도도 실패하면 남은 영상은 처리하지 않아요. 재시도 전에 예약 시각이 지나도 중단해요.
- 완료 이력은 저장하지 않아요. 수동 재실행 전 YouTube Studio에서 게시 여부를 확인하고 완료된 MP4와 입력 묶음을 함께 제외해 주세요.
- 업로드 도중 ESC로 일시정지·재개할 수 있어요.
- 두 일괄 실행 파일 모두 브라우저 처리 완료 모달의 `[닫기]` 클릭 후 10초 기다리고 다음 영상으로 진행해요. 기존 파일 크기별 세션 유지 대기를 대체하므로 추가 대기는 없어요.

설정은 `src/constants/global_constants.ts`의 `YOUTUBE_BATCH_CONFIG`에서 관리해요.
검증 테스트는 `python -B -m unittest discover -s macro -p "test_youtube_batch_upload.py"`로 실행할 수 있어요.

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
│   ├── youtube.py              # 유튜브 (쇼츠/동영상 - 동영상 전용)
│   └── naver.py                # 네이버 클립 (PC 웹 - 동영상 전용)
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
`macro/input.txt` 파일에 아래와 같이 `[TITLE]`, `[CONTENT]`, `[TAGS]`, `[RATIO]`, `[TIME]` 형식으로 작성합니다:

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

[TIME]
2026-09-12 19:30
```
> **💡 비율(RATIO) 설정:**
> - `9:16`: 인스타그램 릴스/세로 화면 기본 비율 (기본값)
> - `1:1`: 정사각형 피드 비율
> - `16:9`: 가로 비율
> - `원본`: 미디어 원본 비율 유지

> **💡 예약 시간(TIME) 설정:**
> - `YYYY-MM-DD HH:MM` 형식으로 입력하면 파일을 지금 업로드하고, 각 SNS의 자체 예약 기능에 공개 시각을 등록해요.
> - 프로그램이 예약 시각까지 실행되거나 기다리지 않아도 돼요.
> - `[TIME]`을 생략하거나 이미 지난 시각을 입력하면 예약 설정 없이 바로 게시해요.
> - 예약 UI를 찾지 못하거나 플랫폼의 예약 가능 범위를 벗어나면 즉시 게시하지 않고 해당 플랫폼 업로드를 실패 처리해요.
> - Instagram은 프로페셔널 계정에서 최대 75일 뒤까지 예약할 수 있어요.
> - TikTok 웹 예약은 지원 계정의 동영상에 한해 15분~10일 뒤로 설정할 수 있어요.
> - 네이버 클립 PC 웹 등록 예약은 최대 30일 뒤까지 설정할 수 있어요.

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

# Naver Clip (기본 1차·2차 카테고리: 유머 > 유머)
NAVER_CLIP_CATEGORY=유머>유머
```

> **💡 브라우저 세션 보존 기능:**
> 2단계 인증(2FA/SMS)이 필요한 플랫폼의 경우 최초 실행 시 열리는 브라우저 화면에서 한 번만 로그인하시면 `sessions/` 폴더에 세션 쿠키가 저장되어 이후에는 로그인 없이 바로 자동 업로드됩니다.

---

## 🏃 4. 실행 방법

### 1) 전체 SNS 일괄 업로드
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

# 네이버 클립만 업로드 (동영상 전용)
python auto_upload.py -p naver
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

### 4) 업로드 일시정지 및 재개 (Windows)

`auto_upload.py`, `auto_upload2.py`, `auto_image_upload.py`, `auto_image_upload2.py`를 실행하는 동안 ESC를 누르면 자동화가 잠시 멈춰요. 다시 ESC를 누르면 이어서 진행해요. 브라우저에 초점이 있어도 사용할 수 있어요. 이미 시작한 브라우저 동작이나 서버 전송은 끝난 뒤 멈추며, 일시정지한 시간은 업로드 대기 제한에서 제외해요.

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
| **Naver Clip** | 동영상 전용 | Playwright (클립 크리에이터 PC 웹) | 첫 번째 영상 커버를 선택하고 AI 활용 설정을 켜요. `[TIME]` 등록 예약은 목표 월로 이동해 날짜를 선택하고 저장한 뒤 시·분을 설정해요. 주요 조작마다 3초씩 멈추고, 등록 완료 화면에서는 10초 뒤 확인을 눌러 브라우저를 닫아요. |


## 여러 SNS에 파일을 하나씩 일괄 업로드하기

```bash
python auto_bulk_upload.py --dry-run
python auto_bulk_upload2.py --dry-run
python auto_bulk_upload.py
python auto_bulk_upload2.py --platform youtube
```

- 첫 번째 스크립트는 `upload/`와 `input_bulk1.txt`를 사용해요.
- 두 번째 스크립트는 `upload2/`와 `input_bulk2.txt`, `sessions2/`의 로그인 계정을 사용해요.
- 지원하는 동영상·사진이 2개 이상이어야 실행해요. 파일은 이름의 숫자 순서(1, 2, 10)로 연결해요.
- 입력은 기존 `[TITLE]`, `[CONTENT]`, `[TAGS]`, `[RATIO]`, `[TIME]` 형식을 사용하고 게시물 사이에 `---`만 있는 줄을 넣어요. 파일 수와 게시물 수를 맞춰 주세요.
- 예약 시각이 비어 있으면 바로 게시해요. 잘못된 시각이나 지난 시각은 업로드 전에 확인하고 멈춰요.
- 플랫폼별로 파일을 순차 업로드해요. 유튜브는 영상 완료 후 10초 뒤 다음 영상을 올려요. 유튜브와 네이버 클립은 사진을 건너뛰고, 페이스북은 기존처럼 비활성화되어 있어요.
- 업로드에 실패하거나 오류가 생겨도 다음 파일·플랫폼을 계속 처리해요. 마지막에 실패한 플랫폼·파일명·제목·이유를 모아서 보여줘요. Ctrl+D로 건너뛴 항목은 따로 보여줘요. 실패가 있으면 모든 항목을 처리한 뒤 종료 코드 1을 반환해요. 다시 실행하기 전에 실패한 항목의 게시 여부를 확인해 주세요.
- `--dry-run`은 파일과 게시물 연결만 확인해요. 브라우저를 열거나 게시하지 않아요.

입력 예시예요.

```text
[TITLE]
첫 번째 제목
[CONTENT]
첫 번째 본문
[TAGS]
#첫번째
[RATIO]
9:16
[TIME]

---

[TITLE]
두 번째 제목
[CONTENT]
두 번째 본문
[TAGS]
#두번째
[RATIO]
9:16
[TIME]
```

일괄 업로드 중 **Ctrl+D**를 누르면 현재 파일의 업로드 프로세스와 브라우저를 종료하고 같은 플랫폼의 다음 파일로 넘어가요. 마지막 파일이면 다음 플랫폼으로 넘어가요. 이미 게시된 내용은 유지돼요. **ESC** 일시정지 중에도 Ctrl+D로 건너뛸 수 있어요. 파일 사이 대기 중에 누른 Ctrl+D는 다음 파일을 건너뛰지 않아요.
