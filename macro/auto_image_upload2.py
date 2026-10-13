"""두 번째 SNS 계정에 upload_image2의 이미지를 한 게시물로 올립니다."""

import os
import sys
from pathlib import Path


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    os.environ["MACRO_INPUT_FILE"] = str(base_dir / "input_image2.txt")
    os.environ["MACRO_UPLOAD_DIR"] = str(base_dir / "upload_image2")
    os.environ["MACRO_SESSION_DIR"] = str(base_dir / "sessions2")
    os.environ["MACRO_SCREENSHOT_DIR"] = str(base_dir / "screenshot2")
    os.environ["MACRO_FORCE_BROWSER_UPLOAD"] = "1"
    os.environ["MACRO_DISABLE_AUTO_LOGIN"] = "1"

    from image_upload_core import run

    return run(base_dir / "input_image2.txt", base_dir / "upload_image2")


if __name__ == "__main__":
    sys.exit(main())
