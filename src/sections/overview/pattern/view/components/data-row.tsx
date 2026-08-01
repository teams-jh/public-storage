import type { ThemeType } from 'src/api/lottolibrary';

import React, { memo, useState } from 'react';

import Box from '@mui/material/Box';

import { getCellColorByTheme } from 'src/api/lottolibrary';

import { LottoCell } from './lotto-cell';
import { getConsecutiveColors } from '../utils';

const LOTTO_NUMBERS = Array.from({ length: 45 }, (_, i) => i + 1);

type DataRowProps = {
  round: any;
  showBonus: boolean;
  showNumbers: boolean;
  theme: ThemeType;
  showMissing: boolean;
  missingStreakMap?: Record<number, number>;
  showConsecutive: boolean;
  consecutiveMap?: Record<number, Set<number>>;
  onPatternClick?: (drwNo: number, num: number) => void;
  highlightedMap?: Set<number>;
  latestPatternMap?: Set<number>;
  cellMinWidth?: number;
};

export const DataRow = memo(function DataRow({
  round,
  showBonus,
  showNumbers,
  theme,
  showMissing,
  missingStreakMap,
  showConsecutive,
  consecutiveMap,
  onPatternClick,
  highlightedMap,
  latestPatternMap,
  cellMinWidth = 16,
}: DataRowProps) {
  const [clicked, setClicked] = useState<number[]>([]);

  const handleClick = (num: number, isWinning: boolean) => {
    if (!isWinning) return;

    // Pattern interaction
    if (
      showConsecutive &&
      consecutiveMap?.[num] &&
      consecutiveMap[num].size > 0 &&
      onPatternClick
    ) {
      onPatternClick(round.drwNo, num);
      // Decide if we should return or allow local click.
      // User requirement: "Change color to dark gray".
      // If we also toggle local click, it might turn blue/orange (default).
      // We likely want ONLY pattern highlight if clicking a pattern.
      return;
    }

    if (clicked.includes(num)) {
      setClicked(clicked.filter((n) => n !== num));
    } else {
      setClicked([...clicked, num]);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'stretch' }}>
      <Box
        sx={{
          position: 'sticky',
          left: 0,
          zIndex: 2,
          bgcolor: 'background.paper',
          display: 'flex',
          alignItems: 'center',
          flexShrink: 0,
          alignSelf: 'stretch',
          pr: '2px',
        }}
      >
        <Box
          sx={{
            width: '40px',
            fontSize: '10px',
            textAlign: 'right',
            marginRight: '6px',
            color: '#999',
            fontFamily: 'monospace',
            flexShrink: 0,
          }}
        >
          {round.drwNo}
        </Box>
      </Box>

      <div style={{ flex: 1, display: 'flex', gap: '1px' }}>
        {LOTTO_NUMBERS.map((num) => {
          const isWinning = round.numbers.includes(num);
          const isBonus = showBonus && round.bonus === num;
          const isPatternHighlighted = highlightedMap?.has(num);
          const isLatestPattern = latestPatternMap?.has(num);
          const isClicked = clicked.includes(num);

          let bgColor = getCellColorByTheme(theme, num, isWinning, isBonus, isClicked);
          if (isLatestPattern) {
            bgColor = '#2e7d32';
          }
          if (isPatternHighlighted) {
            bgColor = '#333333';
          }
          const shouldShowNumber = showNumbers || isClicked;

          // 미출현 오버레이 계산
          const streak = showMissing && missingStreakMap ? missingStreakMap[num] || 0 : 0;
          let overlayColor = 'transparent';
          if (streak > 0 && !isWinning) {
            const alpha = Math.min(streak * 2.5, 95) / 100;
            overlayColor = `rgba(0,0,0, ${alpha})`;
          }

          return (
            <LottoCell
              key={num}
              num={num}
              bgColor={bgColor}
              textColor="#fff" // Optimized logic: Always whites if shown
              content={shouldShowNumber ? num : ''}
              overlayColor={overlayColor}
              onClick={() => handleClick(num, isWinning)}
              cursor={isWinning ? 'pointer' : 'default'}
              consecutiveColors={
                showConsecutive ? getConsecutiveColors(consecutiveMap?.[num]) : undefined
              }
              minWidth={cellMinWidth}
            />
          );
        })}
      </div>
    </div>
  );
});
