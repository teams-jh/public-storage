"""두 번째 SNS 계정용 독립 실행 진입점입니다."""

import os
import runpy
import sys
from pathlib import Path


def main():
    base_dir = Path(__file__).resolve().parent

    # config와 platforms를 불러오기 전에 두 번째 계정 전용 경로를 지정합니다.
    os.environ["MACRO_INPUT_FILE"] = str(base_dir / "input2.txt")
    os.environ["MACRO_UPLOAD_DIR"] = str(base_dir / "upload2")
    os.environ["MACRO_SESSION_DIR"] = str(base_dir / "sessions2")
    os.environ["MACRO_SCREENSHOT_DIR"] = str(base_dir / "screenshot2")
    os.environ["MACRO_FORCE_BROWSER_UPLOAD"] = "1"
    os.environ["MACRO_DISABLE_AUTO_LOGIN"] = "1"

    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    runpy.run_path(str(base_dir / "auto_upload.py"), run_name="__main__")


if __name__ == "__main__":
    main()
