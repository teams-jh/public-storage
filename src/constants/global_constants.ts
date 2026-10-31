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
 * macro/make_mp4의 AAC 오디오 비트레이트 (단위: kbps).
 * 값을 늘리면 음질과 출력 파일 크기가 함께 늘어나요.
 */
export const MAKE_MP4_AUDIO_BITRATE_KBPS = 192;

/**
 * 유튜브 일괄 업로드의 파일 경로·입력 형식 설정 (단위: 경로/문자열).
 * 경로는 macro 폴더 기준이며, 바꾸면 읽을 입력 파일과 영상 폴더가 바뀌어요.
 * sections는 게시물마다 필요한 태그 순서이고 separator는 게시물 구분선이에요.
 * video_suffix는 업로드 대상 확장자, time_format은 로컬 예약 시각 형식이에요.
 * retry_delay_seconds는 업로드 실패 반환 후 재시도까지 기다리는 시간(단위: 초, 기본 20초)이에요.
 * completion_wait_seconds는 브라우저 처리 완료 모달을 닫은 뒤 기다리는 시간(단위: 초, 기본 10초)이에요.
 * 두 일괄 실행 파일에서 파일 크기별 세션 유지 대기를 대체하며, 늘리면 다음 영상 시작이 늦어져요.
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
  "completion_wait_seconds": 10,
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
 * youtube_interval_seconds는 완료 후 다음 유튜브 영상까지 대기 시간(단위: 초)이에요.
 * 늘리면 다음 영상 업로드가 늦어져요. youtube_completion_wait_seconds는 업로더 내부의
 * 완료 대기(단위: 초)이며 0으로 두어 외부의 10초 대기와 중복되지 않게 해요.
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
  "youtube_interval_seconds": 10,
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
