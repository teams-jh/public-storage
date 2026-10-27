# MP3와 이미지로 MP4 만들기

이 폴더에 이름이 같은 `이름.mp3`와 `이름.png` 또는 `이름.jpg`를 넣고 실행해요.
각 MP3를 **곡 전체 단위로 반복**해서 1시간을 초과하는 `이름.mp4`를 만들어요. 예를 들어 14분짜리 MP3는 5번 반복해요.

```powershell
python -m pip install imageio-ffmpeg
python macro/make_mp4/make_mp4.py
```

프로젝트 루트에서 실행하는 예시예요. FFmpeg가 이미 설치되어 있다면 패키지 설치는 생략해도 돼요.

반복 횟수만 확인하려면 다음처럼 실행해요.

```powershell
python macro/make_mp4/make_mp4.py --dry-run
```

이름이 맞지 않는 파일은 건너뛰어요. 같은 이름의 PNG와 JPG가 모두 있으면 PNG를 사용해요. 이미 MP4가 있으면 덮어쓰지 않아요. 영상 길이와 인코딩 설정은 `src/constants/global_constants.ts`의 `MAKE_MP4_` 상수에서 조절할 수 있어요.
