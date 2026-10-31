# MP3와 이미지로 영상 만들기

같은 폴더의 MP3·이미지를 사용하는 두 실행 스크립트가 있어요.

- `make_mp4.py`: 기존 기능이에요. 가사 없이 곡 전체를 반복해 1시간을 초과하는 `result/이름.mp4`를 만들어요. 기존처럼 FFmpeg만 있으면 실행할 수 있어요.
- `make_k_pop.py`: 한글·영어 가사가 나오는 `result/k_pop/이름.mp4`를 만들어요. 스크립트 확장자는 `.py`이고 결과 영상은 `.mp4`예요.

기존 1시간 영상은 아래 명령으로 만들어요.

```powershell
python -m pip install imageio-ffmpeg
python macro/make_mp4/make_mp4.py
```

기존 기능의 파일 연결과 반복 횟수만 보려면 `python macro/make_mp4/make_mp4.py --dry-run`을 실행해요. 기존 영상의 FPS는 `MAKE_MP4_VIDEO_FPS`, 가사 영상의 FPS는 `MAKE_K_POP_VIDEO_FPS`로 따로 관리해요.

# 한글·영어 가사가 나오는 MP4 만들기

이 폴더에 이름이 같은 `이름.mp3`와 `이름.png` 또는 `이름.jpg`를 넣고 실행해요.
오른쪽 빈 공간에 한글 가사와 영어 번역이 함께 나오고 음원 시간에 따라 문장이 바뀌어요. 가사가 없는 구간에는 원본 이미지만 보여요. 가사는 영상에 직접 넣으므로 자막을 따로 켜지 않아도 돼요.

```powershell
python -m pip install -r macro/make_mp4/requirements.txt
python macro/make_mp4/make_k_pop.py --single-pass
```

프로젝트 루트에서 실행하는 예시예요. Python 3.11 이상과 한글 폰트가 필요해요. Windows에서는 맑은 고딕을 자동으로 찾아요. `make_k_pop.py`는 기본으로 한 곡 길이의 영상을 만들어요. `--repeat-hour`를 붙이면 가사와 곡을 1시간 넘게 반복해요. 결과는 `result/k_pop`에 저장해 기존 1시간 영상과 구분해요.

첫 실행에는 Whisper 모델을 내려받아 CPU에서 한글 가사를 인식해요. 기본 모델 `large-v3`는 용량이 크고 처리 시간이 길어요. `--model small`로 작은 모델을 선택하거나 CUDA 환경에서 `--device cuda --compute-type float16`을 사용할 수 있어요.

음성 인식용 음원은 FFmpeg로 모노 파형으로 변환해서 Whisper에 전달해요. `faster-whisper 1.2.1`과 `PyAV 19` 조합에서 생기는 `metadata_errors` 오류를 피하므로 PyAV를 내릴 필요는 없어요. 영상에 넣는 원래 음원의 채널과 음질 설정은 그대로 사용해요.

영어는 기본으로 PC에서 `Helsinki-NLP/opus-mt-ko-en` 모델로 번역해요. 첫 실행에는 번역 모델을 내려받으므로 인터넷 연결이 필요해요. 이후 번역은 로컬에서 처리하며 가사는 외부로 보내지 않아요. 완료한 문장은 저장하므로 다시 실행하면 빈 영어 문장부터 이어서 번역해요. 한글 인식 결과가 있으면 음성 인식도 다시 하지 않아요.

기존 환경에서 번역 패키지가 빠졌다면 `python -m pip install -r macro/make_mp4/requirements.txt`로 설치해 주세요. 로컬 번역 모델은 프로그램 실행 중 한 번 준비하고 곡 사이에도 재사용해요.

Google 번역을 선택하려면 `--translation-backend google`을 붙여요. 이 경우 **가사 문장을 Google 번역으로 전송해요.** 요청 제한(429), 네트워크 오류, 응답 시간 초과가 발생하면 실제 원인을 표시해요. 요청 제한 때문에 실행되지 않으면 옵션을 빼거나 `--translation-backend local`로 실행해 주세요.

노래는 반주·발음·코러스 때문에 가사와 시간이 틀릴 수 있어요. 게시 전 가사 JSON과 실제 재생을 확인해 주세요. 단어마다 색이 채워지는 효과가 아니라 구간별 한영 가사 교체 방식이에요.

## 가사 확인과 수정

먼저 가사와 첫 구간 미리보기만 만들 수 있어요.

```powershell
python macro/make_mp4/make_k_pop.py --prepare-only
```

- `이름.lyrics.json`: 음원 옆에 저장하는 한영 가사와 시작·종료 시각이에요.
- `result/k_pop/이름.preview.png`: 첫 가사 구간의 배치 미리보기예요.
- `result/k_pop/이름.mp4`: 완성 영상이에요.

JSON을 수정하고 다시 실행하면 수정한 가사를 사용해요. `start`, `end`는 **곡 시작 기준 초**이고 오름차순으로 겹치지 않아야 해요. 빈 시간에는 가사가 나오지 않아요. 긴 가사는 자동으로 줄바꿈하고 글자를 줄여요. 최소 크기로도 들어가지 않으면 구간을 나눠 달라는 메시지가 나와요.

직접 아래 형식의 `이름.lyrics.json`을 만들 수도 있어요. 예시는 실제 곡 가사가 아니에요.

```json
{
  "cues": [
    {"start": 3.2, "end": 6.5, "ko": "오늘도 함께 걸어요", "en": "Let's walk together today"},
    {"start": 8.0, "end": 11.4, "ko": "햇살을 따라가요", "en": "Follow the sunlight"}
  ]
}
```

한영 가사가 모두 있는 JSON에 `--offline`을 사용하면 모델 다운로드·인식·외부 번역 없이 만들어요. 자동 생성 JSON에는 원본 음원 SHA-256이 있어 음원을 교체하면 알려줘요. 새로 인식하려면 기존 JSON을 다른 이름으로 보관해 주세요. `--force`는 MP4만 다시 만들고 가사 JSON은 유지해요.

```powershell
python macro/make_mp4/make_k_pop.py --single-pass --offline --force
```

## 가사 위치와 글꼴

`--rect`는 이미지 전체를 0~1로 봤을 때 `왼쪽,위쪽,너비,높이`예요. 기본값은 이 폴더 이미지의 오른쪽 빈 공간에 맞췄어요. 빈 공간을 자동 감지하지는 않아요.

```powershell
python macro/make_mp4/make_k_pop.py --single-pass --rect 0.54,0.16,0.42,0.68 --font C:/Windows/Fonts/malgun.ttf
```

`--folder`로 다른 입력 폴더를 지정할 수 있어요. 하위 폴더는 검색하지 않아요.

파일 연결과 예상 반복 횟수만 확인하려면 다음처럼 실행해요. 다운로드·번역·파일 저장은 하지 않아요.

```powershell
python macro/make_mp4/make_k_pop.py --dry-run
```

이름이 맞지 않는 파일은 건너뛰어요. 대소문자는 구분하지 않고 같은 이름의 PNG와 JPG가 모두 있으면 PNG를 사용해요. 기존 MP4는 `--force`가 없으면 건너뛰어요. 만들던 중 오류가 나도 기존 완성 MP4는 유지하고 다음 곡을 처리해요.

영상 길이와 인코딩 설정, 가사 위치·색상·크기·모델 기본값은 `src/constants/global_constants.ts`의 `MAKE_K_POP_` 상수 (반복 길이·음질은 공용 `MAKE_MP4_` 상수)에서 조절해요. 가사 설정 객체는 Python이 JSON으로 읽으므로 큰따옴표와 JSON 문법을 유지해 주세요.

구현 참고: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [deep-translator](https://github.com/nidhaloff/deep-translator), [FFmpeg](https://ffmpeg.org/ffmpeg.html).
