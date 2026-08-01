import type { ThemeType } from 'src/api/lottolibrary';

import React, { memo } from 'react';

import Box from '@mui/material/Box';

import { getPredictCellColor } from 'src/api/lottolibrary';

import { LottoCell } from './lotto-cell';
import { getConsecutiveColors } from '../utils';

const LOTTO_NUMBERS = Array.from({ length: 45 }, (_, i) => i + 1);

type PredictRowProps = {
  selectedNumbers: number[];
  excludedNumbers: number[];
  handleNumberClick: (num: number) => void;
  handleNumberRightClick?: (num: number) => void;
  showNumbers: boolean;
  theme: ThemeType;
  showConsecutive: boolean;
  consecutiveCandidates: Record<number, Set<number>>;
  cellMinWidth?: number;
};

export const PredictRow = memo(function PredictRow({
  selectedNumbers,
  excludedNumbers,
  handleNumberClick,
  handleNumberRightClick,
  showNumbers,
  theme,
  showConsecutive,
  consecutiveCandidates,
  cellMinWidth = 16,
}: PredictRowProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'stretch', marginBottom: '2px' }}>
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
            flexShrink: 0,
            fontSize: '10px',
            textAlign: 'right',
            marginRight: '6px',
            color: '#999',
            fontFamily: 'monospace',
          }}
        >
          예측
        </Box>
      </Box>

      <div style={{ flex: 1, display: 'flex', gap: '1px' }}>
        {LOTTO_NUMBERS.map((num) => {
          const isSelected = selectedNumbers.includes(num);
          const isExcluded = excludedNumbers?.includes(num) || false;
          const shouldShowNumber = showNumbers || isSelected || isExcluded; // Simplified logic
          const bgColor = getPredictCellColor(theme, num, isSelected);
          const textColor = isSelected || theme !== 'default' ? '#fff' : '#555';

          let consecutiveColors;
          if (showConsecutive) {
            consecutiveColors = getConsecutiveColors(consecutiveCandidates[num]);
          }

          return (
            <LottoCell
              key={num}
              num={num}
              bgColor={bgColor}
              textColor={shouldShowNumber ? textColor : 'transparent'}
              content={shouldShowNumber ? num : ''}
              onClick={() => handleNumberClick(num)}
              onContextMenu={(e) => {
                if (handleNumberRightClick) {
                  e.preventDefault();
                  handleNumberRightClick(num);
                }
              }}
              isExcluded={isExcluded}
              cursor="pointer"
              consecutiveColors={consecutiveColors}
              minWidth={cellMinWidth}
            />
          );
        })}
      </div>
    </div>
  );
});
