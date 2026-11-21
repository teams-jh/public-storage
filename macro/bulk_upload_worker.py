"""일괄 업로드의 한 파일을 독립 프로세스에서 실행해요."""

import json
import sys
from pathlib import Path


def main():
    from auto_upload import PLATFORM_MAP, TwitterXUploader
    from config import parse_scheduled_time
    from upload_pause import pause_on_escape

    platform, media, completion_wait, post_submit_wait, payload = sys.argv[1:]
    metadata = json.loads(payload)
    metadata["scheduled_at"] = parse_scheduled_time(metadata["time"])
    uploaders = dict(PLATFORM_MAP, x=TwitterXUploader)
    uploader = (uploaders[platform](completion_wait_seconds=float(completion_wait),
                                    post_submit_wait_seconds=float(post_submit_wait))
                if platform == "youtube" else uploaders[platform]())
    return 0 if pause_on_escape(uploader.upload)(Path(media), metadata) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
