"""같은 이름의 MP3와 이미지로 한영 가사가 나오는 K-pop MP4를 만들어요."""

import sys

from lyrics_video import main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"실행할 수 없어요: {exc}", file=sys.stderr)
        raise SystemExit(1)
