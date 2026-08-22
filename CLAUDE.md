@TOSS_UX_WRITING.md
﻿# Constant Management Standard (전역 상수 관리 규칙)

- **모든 상수 중앙 집중화**: 광고 수치(시간, 횟수, 확률), 비즈니스/기능 로직 수치, 타이머, 쿨다운, 로컬 스토리지 키 등 모든 const 상수는 반드시 global_constants.ts에 정의해야 합니다.
- **주석 필수**: global_constants.ts에 새 상수를 추가할 때는 반드시 해당 상수의 의미, 단위(초, ms, 비율 0.0~1.0, 횟수 등), 조절 시 영향도를 JSDoc 주석(/** ... */)으로 상세히 작성하세요.
- **하드코딩 금지**: 컴포넌트나 훅 내부에서 매직 넘버(Magic Number)나 광고/비즈니스 설정값을 직접 하드코딩하지 말고 global_constants.ts에서 import하여 사용하세요.
