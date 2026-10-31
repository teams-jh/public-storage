"""auto_upload2.py의 로그인 세션으로 공용 유튜브 입력을 일괄 업로드해요."""

import os
from pathlib import Path
import runpy

from youtube_batch_upload import load_settings


def main():
    base_dir = Path(__file__).resolve().parent
    settings = load_settings()
    account = settings["second_account"]

    # config와 platforms를 불러오기 전에 두 번째 계정의 브라우저 설정을 적용해요.
    # 영상과 입력은 첫 번째 유튜브 일괄 업로더와 같은 파일을 사용해요.
    os.environ["MACRO_INPUT_FILE"] = str(base_dir / settings["input_file"])
    os.environ["MACRO_UPLOAD_DIR"] = str(base_dir / settings["upload_directory"])
    os.environ["MACRO_SESSION_DIR"] = str(base_dir / account["session_directory"])
    os.environ["MACRO_SCREENSHOT_DIR"] = str(base_dir / account["screenshot_directory"])
    os.environ["MACRO_FORCE_BROWSER_UPLOAD"] = account["force_browser_upload"]
    os.environ["MACRO_DISABLE_AUTO_LOGIN"] = account["disable_auto_login"]

    runpy.run_path(str(base_dir / "youtube_batch_upload.py"), run_name="__main__")


if __name__ == "__main__":
    main()
