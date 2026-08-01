import { Storage } from '@apps-in-toss/web-framework';

const isBrowser = typeof window !== 'undefined';

/**
 * Storage API 및 브라우저 localStorage 호환 래퍼 함수들
 */

export const getItem = async (key: string): Promise<string | null> => {
  if (!isBrowser) return null;
  try {
    const val = await Storage.getItem(key);
    if (val !== null && val !== undefined) return val;
  } catch (e) {
    console.warn('Storage.getItem failed, fallback to localStorage', e);
  }

  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.warn('localStorage.getItem failed', e);
    return null;
  }
};

export const setItem = async (key: string, value: string): Promise<void> => {
  if (!isBrowser) return;
  try {
    await Storage.setItem(key, value);
    // web (localStorage) 호환 유지
    localStorage.setItem(key, value);
  } catch {
    try {
      localStorage.setItem(key, value);
    } catch (err) {
      console.warn('localStorage.setItem failed', err);
    }
  }
};

export const removeItem = async (key: string): Promise<void> => {
  if (!isBrowser) return;
  try {
    await Storage.removeItem(key);
    localStorage.removeItem(key);
  } catch {
    try {
      localStorage.removeItem(key);
    } catch (err) {
      console.warn('localStorage.removeItem failed', err);
    }
  }
};

export const clearItems = async (): Promise<void> => {
  if (!isBrowser) return;
  try {
    await Storage.clearItems();
    localStorage.clear();
  } catch {
    try {
      localStorage.clear();
    } catch (err) {
      console.warn('localStorage.clear failed', err);
    }
  }
};

/**
 * JSON 객체를 위한 Helper 함수
 */
export const getStorageJSON = async <T>(key: string): Promise<T | null> => {
  const value = await getItem(key);
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch (e) {
    console.warn('Failed to parse storage JSON', e);
    return null;
  }
};

export const setStorageJSON = async <T>(key: string, value: T): Promise<void> => {
  await setItem(key, JSON.stringify(value));
};

/**
 * 브라우저 웹 환경에서 동기식 처리가 필요한 경우를 위한 localStorage 헬퍼
 */
export const getLocalSync = (key: string): string | null => {
  if (!isBrowser) return null;
  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.warn('localStorage.getItem failed', e);
    return null;
  }
};

export const setLocalSync = (key: string, value: string): void => {
  if (!isBrowser) return;
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    console.warn('localStorage.setItem failed', e);
  }
};

export const removeLocalSync = (key: string): void => {
  if (!isBrowser) return;
  try {
    localStorage.removeItem(key);
  } catch (e) {
    console.warn('localStorage.removeItem failed', e);
  }
};

/**
 * 워터마크 공유/결과 횟수 관련 Storage 헬퍼
 */
const WATERMARK_SHARE_COUNT_KEY = 'ai_watermark_share_count';

export const getShareCountSync = (): number => {
  const val = getLocalSync(WATERMARK_SHARE_COUNT_KEY);
  if (!val) return 0;
  const parsed = parseInt(val, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
};

export const getShareCount = async (): Promise<number> => {
  const val = await getItem(WATERMARK_SHARE_COUNT_KEY);
  if (!val) return 0;
  const parsed = parseInt(val, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
};

export const setShareCount = async (count: number): Promise<void> => {
  setLocalSync(WATERMARK_SHARE_COUNT_KEY, String(count));
  await setItem(WATERMARK_SHARE_COUNT_KEY, String(count));
};

export const incrementShareCount = async (): Promise<number> => {
  const current = await getShareCount();
  const next = current + 1;
  await setShareCount(next);
  return next;
};
