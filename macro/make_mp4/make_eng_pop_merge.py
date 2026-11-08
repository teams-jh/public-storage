"""영어 원문과 한글 번역을 보여주는 여러 곡의 합치기 영상을 만들어요."""

import sys

from lyrics_merge import main


if __name__ == "__main__":
    try:
        raise SystemExit(main("eng_pop"))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"실행할 수 없어요. {exc}", file=sys.stderr)
        raise SystemExit(1)
