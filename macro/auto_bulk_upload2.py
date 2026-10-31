"""두 번째 계정으로 upload2와 input_bulk2.txt를 일괄 업로드해요."""

import sys

from auto_bulk_upload import main


if __name__ == "__main__":
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
    sys.exit(main(account="second"))
