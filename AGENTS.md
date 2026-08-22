# Constant Management Standard (전역 상수 관리 규칙)

- **모든 상수 중앙 집중화**: 광고 수치(시간, 횟수, 확률), 비즈니스/기능 로직 수치, 타이머, 쿨다운, 로컬 스토리지 키 등 모든 const 상수는 반드시 global_constants.ts에 정의해야 합니다.
- **주석 필수**: global_constants.ts에 새 상수를 추가할 때는 반드시 해당 상수의 의미, 단위(초, ms, 비율 0.0~1.0, 횟수 등), 조절 시 영향도를 JSDoc 주석(/** ... */)으로 상세히 작성하세요.
- **하드코딩 금지**: 컴포넌트나 훅 내부에서 매직 넘버(Magic Number)나 광고/비즈니스 설정값을 직접 하드코딩하지 말고 global_constants.ts에서 import하여 사용하세요.
# Toss UX Writing Standard (토스 UX 라이팅 표준)

- **토스 8대 라이팅 원칙 준수**: 모든 UI 문구는 [TOSS_UX_WRITING.md](file:///./TOSS_UX_WRITING.md)에 정의된 5대 Core Value와 8대 Writing Principle을 엄격히 준수합니다.
- **문어체 금지 (~해요체 필수)**: `~합니다 / ~되었습니다 / ~바랍니다` 등의 문어체를 지양하고, 친근하고 명확한 `~해요 / ~했어요 / ~해주세요` 구어체를 사용합니다.
- **모호한 버튼명 금지 (Predictable Hint)**: 단순 `확인`, `다음`, `완료`, `취소`, `이동` 대신 사용자가 다음 결과를 예측할 수 있는 구체적인 동사형 버튼명(`결과 확인하기`, `다음 문제 풀기`, `계속 풀기`, `저장하기` 등)을 작성합니다.
- **잡초 단어(Weed) 제거**: `정상적으로`, `성공적으로`, `해당` 등 불필요한 단어를 제거하고 핵심 메시지만 간결하게 전달합니다.
- **기계적 에러/조롱 문구 금지**: 오류 시 `문제가 생겼어요. 다시 시도해 주세요`와 같이 친절한 해결책을 제시하고, 사용자를 존중하는(Respect) 어조를 유지합니다.
# UI Layout Standard: Icon & Text Vertical Center Alignment (아이콘-텍스트 수직 중앙 정렬)

- **수직 중앙 정렬 필수 (`items-center`)**: 아이콘이 텍스트보다 상대적으로 클 때 텍스트가 아이콘 상단에 붙지 않도록, 반드시 부모 컨테이너에 `flex items-center` (`align-items: center`)를 적용하여 아이콘의 세로 중심 높이에 텍스트가 위치하도록 합니다.
- **다중 라인 텍스트 처리**: 아이콘 옆에 제목+설명 등 다중 라인이 올 경우, 텍스트 래퍼에 `flex flex-col justify-center`를 적용하고 전체 컨테이너에 `items-center`를 적용합니다.
- **MUI 규칙 준수**: MUI 환경에서는 `<Stack>` 대신 `<Box sx={{ display: 'flex', alignItems: 'center', gap: ... }}>`를 사용합니다.
