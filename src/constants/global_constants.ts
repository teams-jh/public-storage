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
