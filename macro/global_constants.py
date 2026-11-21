"""TypeScript 전역 상수에서 매크로 설정을 읽어요."""

import json
from pathlib import Path
import re


def load_macro_settings(name: str) -> dict:
    path = Path(__file__).resolve().parents[1] / "src" / "constants" / "global_constants.ts"
    source = path.read_text(encoding="utf-8-sig")
    match = re.search(
        rf"export const {re.escape(name)}\s*=\s*(\{{.*?\}})\s*as const;", source, re.DOTALL
    )
    if not match:
        raise ValueError(f"global_constants.ts에서 {name} 설정을 찾지 못했어요.")
    return json.loads(match.group(1))


POST_SUBMIT_CONFIG = load_macro_settings("MACRO_POST_SUBMIT_CONFIG")
