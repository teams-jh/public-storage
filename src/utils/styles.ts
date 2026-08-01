import type { CSSProperties } from 'react';

/**
 * 최소 border-radius 수치 (픽셀 단위: 5px)
 * 프로젝트 내 모든 버튼, 박스, 모달, 태그 등 뾰족한 모서리를 금지하고 최소 5px 이상 라운드를 적용합니다.
 */
export const MIN_BORDER_RADIUS_NUM = 5;
export const COMMON_BORDER_RADIUS = `${MIN_BORDER_RADIUS_NUM}px`;

/**
 * 프로젝트 전체 공통 border-radius 스타일 객체 (최소 5px)
 */
export const BORDER_RADIUS_STYLE: CSSProperties = {
  borderRadius: COMMON_BORDER_RADIUS,
};
