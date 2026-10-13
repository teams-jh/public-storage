"""첫 번째 SNS 계정에 upload_image의 이미지를 한 게시물로 올립니다."""

import os
import sys
from pathlib import Path


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    os.environ["MACRO_INPUT_FILE"] = str(base_dir / "input_image.txt")
    os.environ["MACRO_UPLOAD_DIR"] = str(base_dir / "upload_image")
    os.environ["MACRO_SESSION_DIR"] = str(base_dir / "sessions")
    os.environ["MACRO_SCREENSHOT_DIR"] = str(base_dir / "screenshot")
    os.environ["MACRO_FORCE_BROWSER_UPLOAD"] = "1"
    os.environ["MACRO_DISABLE_AUTO_LOGIN"] = "0"

    from image_upload_core import run

    return run(base_dir / "input_image.txt", base_dir / "upload_image")


if __name__ == "__main__":
    sys.exit(main())
