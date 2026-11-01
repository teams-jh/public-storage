# MP3와 이미지로 영상 만들기

용도와 입력 폴더가 다른 세 실행 스크립트가 있어요.

- `make_mp4.py`: `merge_1hour` 폴더의 MP3·이미지를 사용해요. 가사 없이 곡 전체를 반복해 1시간을 초과하는 `result/이름.mp4`를 만들어요. 기존처럼 FFmpeg만 있으면 실행할 수 있어요.
- `make_k_pop.py`: `k_pop` 폴더의 MP3·이미지로 한영 가사 영상과 1시간 반복 영상을 만들어요. 결과는 `result/k_pop`에 저장해요.
- `make_eng_pop.py`: `eng_pop` 폴더의 MP3·이미지로 영어 가사 아래에 더 작은 한글 번역을 넣어요. 결과는 `result/eng_pop`에 저장해요.

## 영어 음악 만들기

`macro/make_mp4/eng_pop`에 이름이 같은 MP3와 PNG/JPG를 넣어요. `make_mp4` 폴더에서 아래처럼 실행해요.

```powershell
python .\make_eng_pop.py      # 한 곡 + 1시간을 넘기는 반복 영상
python .\make_eng_pop.py 1    # 한 곡 영상만
python .\make_eng_pop.py 2    # 반복 영상만
python .\make_eng_pop.py 3    # 없는 가사 JSON만
```

영어 음성을 인식하고 한글로 번역해요. 영어를 위에, 한글을 영어 크기의 85%로 아래에 표시해요. 이전·현재·다음 최대 3개 가사, 주변 가사 불투명도 0.25, 줄바꿈 없이 글자 축소, 다음 발화 시작 시 전환, 곡 사이 3초 무음, 동동체 굵은 글자와 흰 테두리는 한국어 음악과 같아요. 미리보기 PNG는 만들지 않아요.

기본 실행은 `result/eng_pop/곡이름.mp4`와 `result/eng_pop/곡이름_1hour.mp4`를 만들어요. 가사 JSON은 음원 옆의 `eng_pop/곡이름.lyrics.json`에 `en`(원문), `ko`(번역), `start`, `end`로 저장해요. `--offline`, `--force`, `--prepare-only`, `--dry-run`, `--folder`, `--font`, `--rect`, `--translation-backend` 등 나머지 옵션도 같아요.

음성 인식 모델은 기존 캐시를 재사용해요. 영어→한글 번역에는 [facebook/nllb-200-distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M)을 사용하며 첫 실행에는 별도로 내려받아 캐시에 보관해요. `MAKE_ENG_POP_LYRICS_CONFIG`에서 입력·출력 폴더와 언어·번역 모델을 관리하고 나머지 모양과 반복 설정은 `MAKE_K_POP_LYRICS_CONFIG`를 공유해요.

`macro/make_mp4/merge_1hour` 폴더를 만들고 이름이 같은 MP3와 PNG/JPG를 넣어요. 폴더 바로 아래 파일만 처리하고, 결과는 `macro/make_mp4/result/이름.mp4`에 저장해요. 입력 폴더는 `src/constants/global_constants.ts`의 `MAKE_MP4_INPUT_FOLDER`에서 조절해요.

기존 1시간 영상은 아래 명령으로 만들어요.

```powershell
python -m pip install imageio-ffmpeg
python macro/make_mp4/make_mp4.py
```

기존 기능의 파일 연결과 반복 횟수만 보려면 `python macro/make_mp4/make_mp4.py --dry-run`을 실행해요. 기존 영상의 FPS는 `MAKE_MP4_VIDEO_FPS`, 가사 영상의 FPS는 `MAKE_K_POP_VIDEO_FPS`로 따로 관리해요.

# 한글·영어 가사가 나오는 MP4 만들기

`macro/make_mp4/k_pop` 폴더에 이름이 같은 `이름.mp3`와 `이름.png` 또는 `이름.jpg`를 넣고 실행해요. `make_k_pop.py`와 폰트 파일은 `make_mp4` 폴더에 그대로 둬요.
오른쪽 빈 공간에 한글 가사와 영어 번역이 함께 나오고 음원 시간에 따라 문장이 바뀌어요. 첫 가사의 음성이 시작되기 전에는 원본 이미지만 보여요. 가사는 발화가 끝나도 유지하고 다음 가사의 음성이 시작될 때 교체해요. 마지막 가사는 곡이 끝날 때까지 유지해요. 가사는 영상에 직접 넣으므로 자막을 따로 켜지 않아도 돼요.

```powershell
python -m pip install -r macro/make_mp4/requirements.txt
python macro/make_mp4/make_k_pop.py
```

프로젝트 루트에서 실행하는 예시예요. Python 3.11 이상과 한글 폰트가 필요해요. 기본 폰트는 같은 폴더의 `Cafe24DongdongRegular.ttf`이며 한글·영어 모두 획을 확장해 굵게 표시해요. 이 파일이 없으면 Windows에서는 맑은 고딕을 찾아요. `make_k_pop.py`는 옵션이 없으면 한 곡 영상과 그 결과를 1시간 반복한 영상을 모두 만들어요. 결과는 `make_mp4/result/k_pop`에 저장해요.

첫 실행에는 Whisper 모델을 내려받아 CPU에서 한글 가사를 인식해요. 기본 모델 `large-v3`는 용량이 크고 처리 시간이 길어요. `--model small`로 작은 모델을 선택하거나 CUDA 환경에서 `--device cuda --compute-type float16`을 사용할 수 있어요.

음성 인식·번역 모델은 한 번 내려받으면 Hugging Face의 디스크 캐시에 계속 남아요. Windows 기본 위치는 `%USERPROFILE%/.cache/huggingface/hub`이며 `HF_HOME` 등의 환경 설정에 따라 달라질 수 있어요. 캐시가 있으면 인터넷에 접속하지 않고 먼저 불러오며, 파일이 없을 때만 다운로드를 안내해요. 모델을 메모리에 불러오는 시간은 실행할 때마다 필요해요. 한 번 실행하는 동안에는 곡 사이에도 모델을 재사용해요. 캐시를 지우거나 다른 모델을 선택하면 필요한 파일을 다시 내려받아요.

음성 인식용 음원은 FFmpeg로 모노 파형으로 변환해서 Whisper에 전달해요. `faster-whisper 1.2.1`과 `PyAV 19` 조합에서 생기는 `metadata_errors` 오류를 피하므로 PyAV를 내릴 필요는 없어요. 영상에 넣는 원래 음원의 채널과 음질 설정은 그대로 사용해요.

영어는 기본으로 PC에서 `Helsinki-NLP/opus-mt-ko-en` 모델로 번역해요. 첫 실행에는 번역 모델을 내려받으므로 인터넷 연결이 필요해요. 이후 번역은 로컬에서 처리하며 가사는 외부로 보내지 않아요. 완료한 문장은 저장하므로 다시 실행하면 빈 영어 문장부터 이어서 번역해요. 한글 인식 결과가 있으면 음성 인식도 다시 하지 않아요.

기존 환경에서 번역 패키지가 빠졌다면 `python -m pip install -r macro/make_mp4/requirements.txt`로 설치해 주세요. 로컬 번역 모델은 프로그램 실행 중 한 번 준비하고 곡 사이에도 재사용해요.

Google 번역을 선택하려면 `--translation-backend google`을 붙여요. 이 경우 **가사 문장을 Google 번역으로 전송해요.** 요청 제한(429), 네트워크 오류, 응답 시간 초과가 발생하면 실제 원인을 표시해요. 요청 제한 때문에 실행되지 않으면 옵션을 빼거나 `--translation-backend local`로 실행해 주세요.

노래는 반주·발음·코러스 때문에 가사와 시간이 틀릴 수 있어요. 게시 전 가사 JSON과 실제 재생을 확인해 주세요. 단어마다 색이 채워지는 효과가 아니라 구간별 한영 가사 교체 방식이에요.

## 생성 옵션

`make_mp4` 폴더에서 아래처럼 실행해요.

```powershell
python .\make_k_pop.py      # 한 곡 + 1시간 반복 모두 만들어요
python .\make_k_pop.py 1    # 한 곡 영상만 만들어요
python .\make_k_pop.py 2    # 1시간 반복 영상만 만들어요
python .\make_k_pop.py 3    # 없는 가사 JSON만 만들어요
```

`--option 1`, `--option 2`, `--option 3`도 같은 동작이에요. 기존 `--single-pass`는 옵션 1, `--repeat-hour`는 옵션 2와 같아요. 숫자와 이름 옵션을 함께 넣으면 한 가지만 선택해 달라는 메시지가 나와요.

옵션 3은 MP3 옆에 `곡이름.lyrics.json`만 만들어요. 원문·번역·시각을 함께 저장하며 이미지나 폰트는 필요하지 않아요. MP4와 미리보기, 결과 폴더는 만들지 않아요. **이미 JSON이 있으면 내용을 읽거나 수정하지 않고 건너뛰며 `--force`를 붙여도 그대로 둬요.** 미완성 JSON도 건너뛰어요. 기존 JSON의 빈 번역을 이어 채우려면 `--prepare-only`를 사용해 주세요.

한 곡과 반복 영상은 파일별로 존재 여부를 확인해요. 한 곡 영상만 있으면 기본 실행에서 반복 영상만 추가로 만들어요. 옵션 2는 한 곡 영상이 없으면 임시로 생성해 반복 영상만 남겨요. `--force`는 선택한 결과물을 다시 만들어요. 반복 영상은 무음을 붙인 한 곡 구간을 한 번 인코딩한 뒤 이어 붙여요. 가사 인식·번역은 다시 하지 않아요.

## 가사 확인과 수정

먼저 가사 JSON만 준비할 수 있어요.

```powershell
python macro/make_mp4/make_k_pop.py --prepare-only
```

- `k_pop/이름.lyrics.json`: 음원 옆에 저장하는 한영 가사와 시작·종료 시각이에요.
- `result/k_pop/이름.mp4`: 한 곡 길이의 가사 영상이에요.
- `result/k_pop/이름_1hour.mp4`: 곡 전체를 반복해 **1시간을 초과**하는 영상이에요. 곡 사이에는 **3초 무음**을 넣고 마지막 화면을 유지해요. 첫 곡 앞과 마지막 곡 뒤에는 무음을 붙이지 않아요. 한 곡 영상에는 무음을 넣지 않아요. 무음을 포함해 반복 횟수를 계산하며 마지막 곡을 중간에 자르지 않아요. 예를 들어 3분 곡은 20회와 무음 19개를 이어 약 60분 57초가 돼요. 한 곡이 정확히 1시간이어도 2회 반복해요.

이전에 만든 1시간 영상도 새 방식으로 다시 만들려면 `python .\make_k_pop.py 2 --force`를 실행해 주세요.

JSON을 수정하고 다시 실행하면 수정한 가사를 사용해요. `start`, `end`는 **곡 시작 기준 초**이고 오름차순으로 겹치지 않아야 해요. `start`는 가사가 표시되는 시각이에요. `end`는 발화 종료 시각으로 보관하고, 화면에서는 다음 가사의 `start`까지 이전 가사를 유지해요. 전환이 빠르거나 늦으면 다음 가사의 `start`를 음성이 시작되는 시각으로 수정해 주세요. 한글·영어 모두 줄바꿈하지 않고 한 줄에 들어갈 때까지 글자를 줄여요. 원문에 있는 줄바꿈도 공백으로 합쳐요. 최소 크기로도 들어가지 않으면 구간을 나눠 달라는 메시지가 나와요.

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

긴 문장의 글자 크기는 가사와 언어별로 따로 줄여요. A·B·C 중 B만 길다면 B의 긴 줄만 작아지고 A·C와 B의 다른 언어는 원래 크기를 유지해요. 원문과 번역의 기본 크기 비율은 유지하되, 너비를 넘는 줄에만 축소를 적용해요.

현재 가사는 가운데에 선명하게 표시하고, 위에는 이전 가사, 아래에는 다음 가사를 함께 보여요. 한글·영어 한 쌍을 한 가사로 봤을 때 최대 3개이며 이전·다음 가사의 불투명도는 0.25로 흐리게 표시해요. 첫 가사에서는 현재·다음, 마지막에서는 이전·현재만 보여요. 영어 크기는 한글의 85%로 줄였어요. 긴 문장이 있으면 세 묶음이 영역 안에 들어가도록 글자 크기를 줄여 한글·영어 각각 한 줄로 표시해요. 다음 발화가 시작되면 표시하는 가사 묶음도 한 칸씩 바뀌어요.

`--rect`는 이미지 전체를 0~1로 봤을 때 `왼쪽,위쪽,너비,높이`예요. 기본값은 이 폴더 이미지의 오른쪽 빈 공간에 맞췄어요. 빈 공간을 자동 감지하지는 않아요.

```powershell
python macro/make_mp4/make_k_pop.py --single-pass --rect 0.54,0.16,0.42,0.68 --font C:/Windows/Fonts/malgun.ttf
```

`--folder`로 다른 입력 폴더를 지정할 수 있어요. 결과 폴더는 `make_mp4/result/k_pop`을 사용해요. 입력 폴더의 바로 아래 파일만 처리하고 하위 폴더는 검색하지 않아요.

파일 연결과 만들 결과물만 확인하려면 다음처럼 실행해요. 다운로드·번역·파일 저장은 하지 않아요.

```powershell
python macro/make_mp4/make_k_pop.py --dry-run
```

이름이 맞지 않는 파일은 건너뛰어요. 대소문자는 구분하지 않고 같은 이름의 PNG와 JPG가 모두 있으면 PNG를 사용해요. 기존 MP4는 `--force`가 없으면 건너뛰어요. 만들던 중 오류가 나도 기존 완성 MP4는 유지하고 다음 곡을 처리해요.

영상 길이와 인코딩 설정, 가사 위치·색상·크기·모델 기본값은 `src/constants/global_constants.ts`의 `MAKE_K_POP_` 상수 (음질은 공용 `MAKE_MP4_` 상수)에서 조절해요. 가사 설정 객체는 Python이 JSON으로 읽으므로 큰따옴표와 JSON 문법을 유지해 주세요.

구현 참고: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [deep-translator](https://github.com/nidhaloff/deep-translator), [FFmpeg](https://ffmpeg.org/ffmpeg.html).
