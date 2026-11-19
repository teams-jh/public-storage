"""한국어·영어·일본어 곡을 한 영상으로 이어 붙여요."""

import sys

from lyrics_merge import main


if __name__ == "__main__":
    try:
        raise SystemExit(main("total_merge"))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"실행할 수 없어요. {exc}", file=sys.stderr)
        raise SystemExit(1)
