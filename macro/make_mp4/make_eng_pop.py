"""영어 음악에 영어 가사와 더 작은 한글 번역을 넣은 MP4를 만들어요."""

import sys

from lyrics_video import main


if __name__ == "__main__":
    try:
        raise SystemExit(main("eng_pop"))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"실행할 수 없어요: {exc}", file=sys.stderr)
        raise SystemExit(1)
