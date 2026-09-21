# 🎵 YouTube to MP3 Downloader

YouTube 영상 링크 또는 `link.txt` 파일에 적힌 링크들을 읽어와서 자동으로 오디오를 추출하고 고음질 **MP3** 파일로 변환 및 저장해 주는 파이썬 스크립트입니다.

---

## 📌 주요 특징

- **`link.txt` 파일 일괄 다운로드**: `link.txt` 파일에 다운로드하고 싶은 링크들을 한 줄에 하나씩 적어두고 한 번에 모두 MP3로 변환할 수 있습니다.
- **완료된 링크 자동 체크**: 다운로드가 완료된 링크 앞에는 `# [완료]` 주석이 붙어 다음 실행 시 중복 다운로드를 방지합니다.
- **무설치 ffmpeg 지원**: 별도의 복잡한 ffmpeg 환경변수 설정 없이, `imageio-ffmpeg` 패키지를 통해 Windows 환경에서도 즉시 변환이 동작합니다.
- **대화형(Interactive) 모드**: 스크립트만 실행하면 `link.txt`를 감지하여 일괄 다운로드하거나 직접 링크를 입력할 수 있습니다.
- **CLI 명령줄 모드**: 인자로 링크나 텍스트 파일을 직접 넘겨 빠르게 실행할 수 있습니다.
- **음질 선택**: 기본 192kbps부터 최대 320kbps까지 원하는 음질을 지정할 수 있습니다.
- **메타데이터 자동 삽입**: 곡 제목, 채널명(아티스트) 등의 정보가 MP3 태그에 자동으로 입력됩니다.

---

## 🚀 필수 패키지 설치

필요한 라이브러리가 아직 설치되지 않았다면 아래 명령어로 설치해 주세요:

```bash
pip install -r requirements.txt
```

---

## 💻 사용 방법

### 1. `link.txt`에 링크 적어두고 일괄 다운로드 (가장 편리함! ⭐)

1. [link.txt](file:///d:/github/public-storage/macro/youtube/link.txt) 파일을 열고 다운로드할 YouTube 링크를 한 줄에 하나씩 적어줍니다:
   ```text
   https://www.youtube.com/watch?v=xxxxxxxxxxx
   https://youtu.be/yyyyyyyyyyy
   ```
2. 스크립트를 실행합니다:
   ```bash
   python youtube2mp3.py
   # 또는
   python download_mp3.py
   ```
3. `link.txt`의 링크들이 감지되면 `Enter` 키를 눌러 바로 일괄 다운로드를 진행합니다.
4. 다운로드가 완료되면 `link.txt` 파일 내 완료된 항목 앞에 `# [완료]`가 자동으로 표시됩니다.

---

### 2. 대화형 모드에서 직접 링크 입력

`link.txt`가 비어있거나 옵션 [2]를 선택하면 콘솔에서 직접 링크를 입력하여 다운로드할 수 있습니다.

```text
👉 YouTube 링크를 입력해 주세요 (종료: q): https://www.youtube.com/watch?v=...
```

---

### 3. 명령줄(CLI) 한 줄 실행

```bash
# 특정 텍스트 파일의 링크 일괄 다운로드
python youtube2mp3.py -f link.txt

# 단일 링크 직접 전달
python youtube2mp3.py "https://www.youtube.com/watch?v=..."

# 음질을 320kbps로 지정 (-q 옵션)
python youtube2mp3.py -q 320
```

---

## 📂 파일 저장 위치

변환이 완료된 MP3 파일은 아래 폴더에 저장됩니다:
`macro/youtube/downloads/`
