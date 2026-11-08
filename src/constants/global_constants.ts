/**
 * ============================================================================
 * [GLOBAL CONSTANTS] 전역 상수 및 설정 관리 파일 (public-storage)
 * ============================================================================
 * 이 파일은 앱 내의 모든 광고 설정, 비즈니스/기능 로직 상수, 시스템 설정을 중앙 집중식으로 관리합니다.
 * 향후 추가되는 모든 상수는 본 파일에 정의하고 명확한 주석을 작성해야 합니다.
 */

// ============================================================================
// 1. 광고(Ad) 관련 상수 및 설정
// ============================================================================

/** 앱 전체에서 사용하는 식별 이름. 변경하면 광고 및 앱 설정에서 참조하는 이름이 함께 바뀌어요. */
export const CURRENT_APP_NAME = "lotto-viewer-mobile";

/** 원격 광고 데이터 JSON URL */
export const NEW_ADS_INFO_URL =
  "https://raw.githubusercontent.com/teams-jh/public-storage/refs/heads/main/json/ad_info.json";

/** 공용 에셋 및 스토리지 베이스 URL */
export const PUBLIC_STORAGE_BASE_URL =
  "https://raw.githubusercontent.com/teams-jh/public-storage/refs/heads/main";

/** 기본 더미 로고 이미지 경로 */
export const DEFAULT_DUMMY_LOGO = "/personal-ad/dummy.png";

/** 신규 광고 원격 동기화 기능 On/Off 여부 (true일 때 하루 1회 최초 접속 시 광고 갱신) */
export const NEW_AD_FEATURE_ON = true;

/** 자동 광고 롤링 시 토스 배너 광고가 선택될 확률 (0.0 ~ 1.0, 0.2 = 20%) */
export const TOSS_AD_AUTO_RANDOM_CHANCE = 0.2;

/** 스와이프 광고 전환 시 토스 배너 광고가 선택될 확률 (0.0 ~ 1.0, 0.1 = 10%) */
export const TOSS_AD_SWIPE_RANDOM_CHANCE = 0.1;

/** 토스 배너 광고 1회 노출 유지 시간 (단위: 초) */
export const TOSS_AD_DURATION_SEC = 15;

/** 자체/하우스 배너 광고 1회 노출 유지 시간 (단위: 초) */
export const PERSONAL_AD_DURATION_SEC = 10;

/** 자체 광고 노출 시 시각적 임팩트 효과 발동 확률 (0.0 ~ 1.0, 0.8 = 80%) */
export const PERSONAL_AD_EFFECT_CHANCE = 0.8;

/** 전면(Interstitial) 광고 진입 전 안내 카운트다운 시간 (단위: 초) */
export const INTERSTITIAL_AD_COUNTDOWN_SEC = 3;

/** 보상형(Reward) 광고 진입 전 카운트다운 시간 (단위: 초) */
export const REWARD_AD_COUNTDOWN_SEC = 2;

/** 광고 시청 완료 후 재노출 방지 쿨다운 시간 (단위: 밀리초, 1분 = 60,000ms) */
export const AD_COOLDOWN_MS = 60 * 1000;

// ============================================================================
// 2. 공용 스토리지 및 에셋 관리 상수
// ============================================================================

/** 단일 파일 최대 업로드 허용 용량 (단위: MB) */
export const MAX_UPLOAD_FILE_SIZE_MB = 50;

/** 원격 에셋 캐시 만료 주기 (단위: 시간) */
export const CACHE_EXPIRY_HOURS = 24;

/** 이미지 미리보기 최대 가로 해상도 (단위: px) */
export const PREVIEW_IMAGE_MAX_WIDTH = 1200;

/** 1페이지당 파일 목록 표시 개수 */
export const DEFAULT_PAGE_SIZE = 20;

// ============================================================================
// 3. UI 및 인터랙션 관련 상수
// ============================================================================

/** 기본 토스트 팝업 노출 시간 (단위: 밀리초) */
export const TOAST_DURATION_MS = 2500;

/** 모달 애니메이션 트랜지션 시간 (단위: 밀리초) */
export const MODAL_TRANSITION_MS = 200;


// ============================================================================
// 4. 로컬 스토리지(LocalStorage) 키 관리
// ============================================================================

export const STORAGE_KEYS = {
  /** 마지막 광고 시청 타임스탬프 저장 키 */
  LAST_AD_SHOWN_TIMESTAMP: "last_ad_shown_timestamp",
  /** 마지막 원격 광고 fetch 날짜 키 */
  AD_LAST_FETCH_DATE: "ait_ad_last_fetch_date",
  /** 저장된 광고 로고 키 */
  AD_SAVED_LOGO: "ait_ad_saved_logo",
  /** 저장된 신규 광고 데이터 키 */
  AD_SAVED_NEW_ADS: "ait_ad_saved_new_ads",
  /** 앱 설정 저장 키 */
  USER_SETTINGS: "public-storage_user_settings",
} as const;

// ============================================================================
// 5. 로또 당첨 번호 자동 갱신 설정
// ============================================================================

/** 동행복권 로또 6/45 회차 조회 API 주소. 변경하면 자동 갱신 데이터의 출처가 바뀌어요. */
export const LOTTO_RESULT_API_URL =
  "https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do";

/** 전체 로또 데이터 파일의 저장소 루트 기준 경로. 변경하면 갱신 대상 파일이 바뀌어요. */
export const LOTTO_NUMBER_JSON_PATH = "json/lottoNumber.json";

/** 간소화 로또 데이터 파일의 저장소 루트 기준 경로. 변경하면 앱이 읽는 갱신 대상이 바뀌어요. */
export const COMPACT_LOTTO_NUMBER_JSON_PATH = "json/compactLottoNumber.json";

/** 동행복권 API 요청 제한 시간(단위: ms). 늘리면 느린 응답을 더 오래 기다려요. */
export const LOTTO_REQUEST_TIMEOUT_MS = 15_000;

/** 동행복권 API 요청 실패 시 최대 재시도 횟수(단위: 횟수). 늘리면 일시 장애 복구 가능성과 실행 시간이 함께 늘어요. */
export const LOTTO_REQUEST_MAX_RETRIES = 3;

/** 동행복권 API 재시도 사이의 기본 대기 시간(단위: ms). 실제 대기 시간은 시도 횟수에 비례해 늘어나요. */
export const LOTTO_REQUEST_RETRY_DELAY_MS = 1_000;

/** 동행복권 API 요청에 사용하는 User-Agent 값. 변경하면 사이트에서 요청을 식별하는 방식이 달라질 수 있어요. */
export const LOTTO_REQUEST_USER_AGENT =
  "public-storage-lotto-updater/1.0 (+https://github.com/teams-jh/public-storage)";

// ============================================================================
// 6. MP3 및 이미지의 MP4 변환 설정
// ============================================================================

/**
 * make_mp4.py가 MP3와 PNG/JPG를 찾는 입력 폴더 (단위: macro/make_mp4 기준 상대 경로).
 * 값을 바꾸면 같은 이름의 음원과 이미지를 검색하는 위치가 달라져요.
 * 입력 폴더 바로 아래 파일만 처리해요.
 */
export const MAKE_MP4_INPUT_FOLDER = "merge_1hour";

/**
 * macro/make_mp4의 오디오 반복 종료 기준 (단위: 초).
 * 완성 영상은 이 길이와 같아도 부족하며 반드시 초과해야 해요.
 * 값을 늘리면 MP3 반복 횟수와 출력 MP4 크기 및 변환 시간이 함께 늘어나요.
 */
export const MAKE_MP4_MIN_DURATION_SECONDS = 3600;

/**
 * FFmpeg가 MP3 길이를 소수점 둘째 자리까지 표시할 때의 최대 반올림 오차 (단위: 초).
 * 이 값을 줄이면 한 시간 경계에 가까운 파일의 반복 횟수가 부족해질 수 있어요.
 */
export const MAKE_MP4_DURATION_ROUNDING_SECONDS = 0.005;

/**
 * macro/make_mp4의 정지 이미지 영상 프레임 빈도 (단위: 초당 프레임).
 * 값을 늘리면 MP4 인코딩 시간과 파일 크기가 늘어나요.
 */
export const MAKE_MP4_VIDEO_FPS = 1;

/**
 * make_k_pop.py 가사 영상의 프레임 빈도 (단위: 초당 프레임).
 * 높이면 가사 전환 시점이 정밀해지고 인코딩 시간과 파일 크기가 늘어나요.
 * 기존 1시간 영상의 MAKE_MP4_VIDEO_FPS와 독립적으로 조절해요.
 */
export const MAKE_K_POP_VIDEO_FPS = 30;

/**
 * macro/make_mp4의 AAC 오디오 비트레이트 (단위: kbps).
 * 값을 늘리면 음질과 출력 파일 크기가 함께 늘어나요.
 */
export const MAKE_MP4_AUDIO_BITRATE_KBPS = 192;

/**
 * 합치기 영상에서 하위 폴더의 곡 순서를 통째로 반복하는 기본 횟수(회).
 * 값을 늘리면 최종 영상의 재생 길이, 인코딩 시간, 파일 크기가 늘어요.
 * 실행할 때 --merge 뒤에 숫자를 넣으면 그 실행에만 다른 횟수를 적용해요.
 */
export const MAKE_POP_MERGE_REPEAT_COUNT = 5;

/**
 * 합치기 영상에 사용하는 공통 오디오 샘플링 주파수(Hz).
 * 원본 음원의 주파수가 달라도 같은 형식으로 이어 붙일 수 있어요.
 * 값을 바꾸면 출력 오디오의 주파수와 변환 중 임시 파일의 크기가 달라져요.
 */
export const MAKE_POP_MERGE_AUDIO_SAMPLE_RATE_HZ = 48000;

/**
 * 합치기 영상에 사용하는 공통 오디오 채널 수(개). 2는 스테레오예요.
 * 값을 바꾸면 출력 오디오의 채널 구성과 원본 음원의 믹싱 방식이 달라져요.
 */
export const MAKE_POP_MERGE_AUDIO_CHANNELS = 2;

/**
 * 가사 영상 생성 설정. Python에서 JSON으로 읽으므로 키와 문자열은 큰따옴표를 사용해요.
 * input_folder/output_folder: make_mp4 폴더 기준 입력/결과 경로. 바꾸면 검색할 음원과 저장할 영상의 위치가 달라져요.
 * merge_input_folder/merge_output_folder: 합치기 모드의 make_mp4 기준 입력/결과 상대 경로. 바꾸면 하위 폴더 검색 위치와 합친 MP4의 저장 위치가 달라져요.
 * hour_suffix: 반복 영상 파일명에 붙일 문자열. 바꾸면 한 곡 영상과 구분하는 이름이 달라져요.
 * repeat_duration_seconds: 반복 영상이 반드시 초과해야 하는 기준 길이(초). 곡 전체 단위로 반복하며 마지막 곡을 자르지 않아요. 늘리면 반복 횟수와 파일 크기가 늘어나요.
 * repeat_gap_seconds: 반복되는 곡 사이의 무음 길이(초). 늘리면 곡 사이의 대기 시간이 길어져요. 첫 곡 앞과 마지막 곡 뒤에는 붙이지 않아요.
 * rect: 이미지 기준 x/y/너비/높이 비율(0~1). 바꾸면 한영 가사 영역이 이동해요.
 * font_candidates: 한글 폰트 경로 목록. 상대 경로는 make_mp4 폴더 기준이며 앞에서부터 존재하는 폰트를 사용해요.
 * font_ratio/min_font_ratio: 이미지 높이 대비 기본/최소 글자 크기 비율. 한글·영어 각각 명시한 줄바꿈을 유지하며 줄별 너비와 묶음 높이에 맞춰 줄여요. 최소값을 낮추면 더 긴 문장이 들어가요.
 * source_language/target_language: 인식할 원문/번역 언어 코드. source_label/target_label은 안내에 표시할 언어 이름이에요. 바꾸면 인식·번역 방향과 화면의 위아래 언어가 달라져요.
 * translation_font_scale: 원문 글자 크기 대비 번역 글자 크기 비율(0~1). 줄이면 아래쪽 번역이 더 작게 보여요.
 * context_radius: 현재 가사 앞뒤에 표시할 가사 개수(각 방향 기준 개). 1이면 이전·현재·다음 최대 3개를 표시해요.
 * context_opacity: 이전·다음 가사의 불투명도(0~1). 낮추면 흐려지고 현재 가사는 항상 불투명하게 표시해요.
 * context_slot_gap_ratio: 각 가사 영역 높이 대비 비워 둘 간격 비율(0~1). 늘리면 가사 묶음 사이 간격이 넓어져요.
 * line_gap_ratio/language_gap_ratio: 글자 크기 대비 줄/언어 사이 간격 비율. 늘리면 더 넓게 배치해요.
 * ko_color/en_color/stroke_color: RGB 색상 문자열 또는 "auto". 가사는 줄 뒤 배경에 맞춰 색을 고르고, 외곽선은 글자와 반대 밝기로 표시해요. RGB 값을 넣으면 색을 고정해요.
 * contrast_dark_color/contrast_light_color: 자동 모드에 쓰는 어두운/밝은 RGB 색상 문자열. 두 색의 밝기 차이가 크면 배경과 글자를 구분하기 쉬워요.
 * contrast_threshold: 자동 색상을 가르는 평균 회색조 밝기(0~255). 값을 높이면 밝은 글자를 더 자주 써요.
 * stroke_ratio: 글자 크기 대비 외곽선 두께 비율. 늘리면 배경과 더 뚜렷하게 구분돼요.
 * stroke_multiplier: 픽셀 단위로 계산한 외곽선 두께의 배수(양의 정수). 2이면 기본 두께의 2배로 표시해요.
 * bold_ratio: 글자 크기 대비 같은 색으로 확장할 획 두께 비율(0 이상). 늘리면 Regular 폰트도 더 굵어지고 0이면 원래 굵기로 표시해요.
 * model/device/compute_type: 로컬 음성 인식 모델·장치·연산 형식. 큰 모델은 메모리와 시간이 더 필요해요.
 * beam_size: 음성 인식 탐색 후보 수(개). 늘리면 탐색 시간이 늘어나요.
 * max_chars/max_cue_seconds: 자동 가사 한 구간의 글자 수/길이(초) 상한. 줄이면 더 자주 바뀌어요.
 * translation_timeout_seconds: 번역 요청 제한 시간(초). 늘리면 응답을 더 오래 기다려요.
 * translation_backend: 기본 번역 방식(local/google). local은 내려받은 모델로 PC에서 번역해요.
 * translation_model: 로컬 한국어→영어 모델 ID 또는 폴더 경로. 변경하면 번역 품질과 다운로드 용량이 달라져요.
 * translation_max_new_tokens: 한 문장에서 생성할 최대 토큰 수(개). 늘리면 긴 번역을 생성할 수 있어요.
 * encoder_preset/crf: H.264 속도 설정/품질 지수(0~51). 느린 preset과 낮은 crf는 변환 비용이 늘어요.
 */
export const MAKE_K_POP_LYRICS_CONFIG = {
  "source_language": "ko",
  "target_language": "en",
  "source_label": "한글",
  "target_label": "영어",
  "input_folder": "k_pop",
  "output_folder": "result/k_pop",
  "merge_input_folder": "k_pop_merge",
  "merge_output_folder": "result/k_pop_merge",
  "hour_suffix": "_1hour",
  "repeat_duration_seconds": 3600,
  "repeat_gap_seconds": 3,
  "rect": [0.54, 0.16, 0.42, 0.68],
  "font_candidates": ["Cafe24DongdongRegular.ttf", "C:/Windows/Fonts/malgun.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc"],
  "font_ratio": 0.047,
  "min_font_ratio": 0.002,
  "translation_font_scale": 0.85,
  "context_radius": 1,
  "context_opacity": 0.25,
  "context_slot_gap_ratio": 0.1,
  "line_gap_ratio": 0.3,
  "language_gap_ratio": 0.8,
  "ko_color": "auto",
  "en_color": "auto",
  "stroke_color": "auto",
  "contrast_dark_color": "#000000",
  "contrast_light_color": "#ffffff",
  "contrast_threshold": 128,
  "stroke_ratio": 0.02,
  "stroke_multiplier": 2,
  "bold_ratio": 0.04,
  "model": "large-v3",
  "device": "cpu",
  "compute_type": "int8",
  "beam_size": 5,
  "max_chars": 28,
  "max_cue_seconds": 7,
  "translation_timeout_seconds": 30,
  "translation_backend": "local",
  "translation_model": "Helsinki-NLP/opus-mt-ko-en",
  "translation_max_new_tokens": 128,
  "encoder_preset": "veryfast",
  "crf": 20
};

/**
 * make_eng_pop.py의 전용 설정. MAKE_K_POP_LYRICS_CONFIG를 공유하고 아래 속성만 덮어써요.
 * input_folder/output_folder는 make_mp4 기준 입력/결과 경로이며 바꾸면 파일 검색·저장 위치가 달라져요.
 * merge_input_folder/merge_output_folder는 make_mp4 기준 합치기 입력/결과 상대 경로이며 바꾸면 하위 폴더 검색·저장 위치가 달라져요.
 * source_language/target_language는 영어 인식·한글 번역 방향, source_label/target_label은 안내 언어 이름이에요.
 * translation_model은 로컬 영어→한국어 번역 모델 ID예요. 바꾸면 번역 품질·다운로드 용량이 달라져요.
 * translation_family는 번역 모델 종류(marian/nllb), translation_source_tag/translation_target_tag는 NLLB 원문/번역 언어 태그예요. 바꾸면 불러올 모델 구조와 번역 언어가 달라져요.
 * 나머지 글자 크기 비율·색상·투명도·무음 길이·반복 기준은 공통 설정과 같은 단위와 효과를 가져요.
 * Python에서 JSON으로 읽으므로 큰따옴표와 JSON 문법을 유지해요.
 */
export const MAKE_ENG_POP_LYRICS_CONFIG = {
  "input_folder": "eng_pop",
  "output_folder": "result/eng_pop",
  "merge_input_folder": "eng_pop_merge",
  "merge_output_folder": "result/eng_pop_merge",
  "source_language": "en",
  "target_language": "ko",
  "source_label": "영어",
  "target_label": "한글",
  "translation_model": "facebook/nllb-200-distilled-600M",
  "translation_family": "nllb",
  "translation_source_tag": "eng_Latn",
  "translation_target_tag": "kor_Hang"
};

/**
 * 유튜브 일괄 업로드의 파일 경로·입력 형식 설정 (단위: 경로/문자열).
 * 경로는 macro 폴더 기준이며, 바꾸면 읽을 입력 파일과 영상 폴더가 바뀌어요.
 * sections는 게시물마다 필요한 태그 순서이고 separator는 게시물 구분선이에요.
 * video_suffix는 업로드 대상 확장자, time_format은 로컬 예약 시각 형식이에요.
 * retry_delay_seconds는 업로드 실패 반환 후 재시도까지 기다리는 시간(단위: 초, 기본 20초)이에요.
 * post_submit_wait_seconds는 게시·예약 버튼을 누른 뒤 서버 처리를 기다리는 시간(단위: 초, 기본 10초)이에요.
 * 파일 크기별 서버 처리 대기를 대체하며, 늘리면 다음 영상 시작이 늦어져요.
 * completion_wait_seconds는 완료 모달 후 추가 대기(단위: 초)이며 0으로 두어 중복 대기를 없애요.
 * max_retries는 영상당 추가 시도 횟수(단위: 회, 기본 1회)이며, 늘리면 실패 시 시도 횟수가 늘어나요.
 * 대기 시간을 늘리면 재시도가 늦어지고, 횟수를 늘리면 중복 게시 가능성도 커질 수 있어요.
 * second_account는 두 번째 실행 파일의 세션·캡처 경로(단위: macro 기준 경로)와
 * 브라우저 업로드·자동 로그인 차단 플래그(문자열 "1": 활성화)예요.
 * auto_upload2.py와 같은 값이며, 경로를 바꾸면 사용하는 로그인 계정도 바뀔 수 있어요.
 * Python에서도 읽으므로 객체 내부는 주석과 후행 쉼표 없이 JSON 문법을 유지해요.
 */
export const YOUTUBE_BATCH_CONFIG = {
  "input_file": "youtube_input.txt",
  "upload_directory": "youtube_upload",
  "video_suffix": ".mp4",
  "sections": ["[TITLE]", "[CONTENT]", "[TIME]"],
  "separator": "---",
  "time_format": "%Y-%m-%d %H:%M",
  "retry_delay_seconds": 20,
  "completion_wait_seconds": 0,
  "post_submit_wait_seconds": 10,
  "max_retries": 1,
  "second_account": {
    "session_directory": "sessions2",
    "screenshot_directory": "screenshot2",
    "force_browser_upload": "1",
    "disable_auto_login": "1"
  }
} as const;


/**
 * SNS 일괄 업로드 설정이에요. 경로는 macro 폴더 기준이며 바꾸면 입력·계정이 바뀌어요.
 * accounts의 키는 실행 계정 이름이고 값은 환경 변수별 경로·플래그(문자열)예요.
 * skip_hotkey.id는 프로세스 내 단축키 등록 ID, modifiers는 Ctrl+반복 방지 Win32 비트 플래그,
 * virtual_key는 D의 Win32 키 코드예요. 바꾸면 건너뛰기 단축키가 바뀌어요.
 * poll_seconds는 종료 요청 검사 간격(단위: 초)이며 줄이면 반응 속도와 검사 빈도가 늘어요.
 * minimum_media_count는 실행에 필요한 최소 미디어 수(단위: 개)이며 줄이면 단일 파일도 실행해요.
 * separator는 한 줄 전체가 일치할 때 게시물을 나누는 구분 문자열이에요.
 * sections는 허용하는 입력 태그와 메타데이터 필드 이름이며 바꾸면 입력 해석이 바뀌어요.
 * platforms는 기본 업로드 순서예요. disabled_platforms는 선택해도 건너뛰는 플랫폼이에요.
 * video_only_platforms는 사진을 건너뛰는 플랫폼이에요. 바꾸면 미디어 전송 대상이 바뀌어요.
 * youtube_post_submit_wait_seconds는 게시·예약 버튼 클릭 후 서버 처리 대기(단위: 초)예요.
 * 10초 뒤 완료 화면을 확인하고 다음 작업으로 넘어가며, 미확인 항목은 실패 목록에 남겨요.
 * 늘리면 서버 처리 확인 시간과 다음 작업까지의 시간이 함께 늘어요.
 * youtube_interval_seconds는 파일 사이 추가 대기, youtube_completion_wait_seconds는
 * 완료 모달 후 추가 대기(단위: 초)예요. 둘 다 0으로 두어 10초 이후 추가 대기를 없애요.
 * Python에서도 읽으므로 객체 내부는 주석과 후행 쉼표 없이 JSON 문법을 유지해요.
 */
export const AUTO_BULK_UPLOAD_CONFIG = {
  "minimum_media_count": 2,
  "skip_hotkey": {"id": 2, "modifiers": 16386, "virtual_key": 68, "poll_seconds": 0.1},
  "separator": "---",
  "sections": {"[TITLE]": "title", "[CONTENT]": "content", "[TAGS]": "tags", "[RATIO]": "ratio", "[TIME]": "time"},
  "platforms": ["naver", "instagram", "threads", "tiktok", "youtube"],
  "disabled_platforms": ["facebook"],
  "video_only_platforms": ["youtube", "naver"],
  "youtube_post_submit_wait_seconds": 10,
  "youtube_interval_seconds": 0,
  "youtube_completion_wait_seconds": 0,
  "accounts": {
    "first": {"MACRO_INPUT_FILE": "input_bulk1.txt", "MACRO_UPLOAD_DIR": "upload"},
    "second": {
      "MACRO_INPUT_FILE": "input_bulk2.txt",
      "MACRO_UPLOAD_DIR": "upload2",
      "MACRO_SESSION_DIR": "sessions2",
      "MACRO_SCREENSHOT_DIR": "screenshot2",
      "MACRO_FORCE_BROWSER_UPLOAD": "1",
      "MACRO_DISABLE_AUTO_LOGIN": "1"
    }
  }
} as const;
