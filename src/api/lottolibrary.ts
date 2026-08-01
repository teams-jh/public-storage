import compactLottoNumber from 'json/compactLottoNumber.json';

import Box from '@mui/material/Box';
import { styled } from '@mui/material/styles';

export type CompactLottoItem = {
  drwNoDate: string;
  No: number[];
  bnusNo: number;
};

export type LottoRound = {
  drwNoDate: string;
  drwNo: number;
  numbers: number[];
  bonus: number;
};

export const Ball = styled(Box)(({ theme }) => ({
  width: 80,
  height: 80,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#fff',
  fontWeight: 'bold',
  fontSize: '2rem',
  boxShadow: theme.shadows[10],
  position: 'relative',
  textShadow: '1px 1px 2px rgba(0,0,0,0.3)',
  border: '2px solid rgba(255,255,255,0.2)',
  [theme.breakpoints.down('md')]: {
    width: 60,
    height: 60,
    fontSize: '1.5rem',
  },
  [theme.breakpoints.down('sm')]: {
    width: 36,
    height: 36,
    fontSize: '0.875rem',
  },
}));

// Theme types
export type ThemeType = 'default' | 'range';

export const THEME_NAMES: Record<ThemeType, string> = {
  default: '기본',
  range: '범위별',
};

// Ball color for home display (original function)
export const getBallColor = (num: number) => {
  if (num <= 10) return '#fbc400';
  if (num <= 20) return '#69c8f2';
  if (num <= 30) return '#ff7272';
  if (num <= 40) return '#aaaaaa';
  return '#b0d840';
};

// Theme-based cell colors for pattern view
export const getCellColorByTheme = (
  theme: ThemeType,
  num: number,
  isWinning: boolean,
  isBonus: boolean,
  isClicked: boolean
): string => {
  // Bonus always has priority
  if (isBonus) return '#d54dffff';

  // Clicked state
  if (isClicked) return '#000000ff';

  // Non-winning cells
  if (!isWinning) return '#F1F3F4';

  // Winning cells - apply theme
  if (theme === 'range') {
    // Range-based colors (same as getBallColor)
    if (num <= 10) return '#fbc400';
    if (num <= 20) return '#69c8f2';
    if (num <= 30) return '#ff7272';
    if (num <= 40) return '#aaaaaa';
    return '#b0d840';
  }

  // Default theme
  return '#658effff';
};

// Get predict cell color (for user selection row)
export const getPredictCellColor = (theme: ThemeType, num: number, isSelected: boolean): string => {
  if (isSelected) return '#000000ff';

  // Non-selected cells show theme preview
  if (theme === 'range') {
    // Show range colors even when not selected
    if (num <= 10) return '#fbc400';
    if (num <= 20) return '#69c8f2';
    if (num <= 30) return '#ff7272';
    if (num <= 40) return '#aaaaaa';
    return '#b0d840';
  }

  // Default theme
  return '#E8EAED';
};

export const getLength = () => compactLottoNumber.length;

export const getLatestLottoNumber = (): LottoRound | null => {
  if (!compactLottoNumber || compactLottoNumber.length === 0) {
    return null;
  }

  const index = compactLottoNumber.length - 1;
  const latest = compactLottoNumber[index];

  return {
    drwNo: index + 1,
    drwNoDate: latest.drwNoDate,
    numbers: latest.No,
    bonus: latest.bnusNo,
  };
};

export const getLottoByIndex = (index: number): LottoRound | null => {
  if (
    !compactLottoNumber ||
    compactLottoNumber.length === 0 ||
    index < 0 ||
    index >= compactLottoNumber.length
  ) {
    return null;
  }

  const target = compactLottoNumber[index];

  return {
    drwNo: index + 1,
    drwNoDate: target.drwNoDate,
    numbers: target.No,
    bonus: target.bnusNo,
  };
};

export const getAllLottoNumbers = (): LottoRound[] =>
  compactLottoNumber.map((item, index) => ({
    drwNo: index + 1,
    drwNoDate: item.drwNoDate,
    numbers: item.No,
    bonus: item.bnusNo,
  }));
