'use client';

import { useState } from 'react';

import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { alpha, useTheme } from '@mui/material/styles';

// ----------------------------------------------------------------------

const COLUMNS = ['A', 'B', 'C', 'D', 'E'];
const NUMBERS = Array.from({ length: 45 }, (_, i) => i + 1);

export function LottoPickerPaper() {
  const theme = useTheme();

  // State to track selected numbers for each column (A-E)
  // { A: [1, 2, ...], B: [], ... }
  const [selections, setSelections] = useState<Record<string, number[]>>({
    A: [],
    B: [],
    C: [],
    D: [],
    E: [],
  });

  const [autoSelections, setAutoSelections] = useState<Record<string, boolean>>({
    A: false,
    B: false,
    C: false,
    D: false,
    E: false,
  });

  const handleToggleNumber = (column: string, number: number) => {
    setSelections((prev) => {
      const currentColumn = prev[column];
      const isSelected = currentColumn.includes(number);

      if (isSelected) {
        return {
          ...prev,
          [column]: currentColumn.filter((n) => n !== number),
        };
      }

      if (currentColumn.length >= 6) {
        return prev; // Max 6 numbers
      }

      return {
        ...prev,
        [column]: [...currentColumn, number],
      };
    });
  };

  const handleToggleAuto = (column: string) => {
    setAutoSelections((prev) => ({
      ...prev,
      [column]: !prev[column],
    }));
  };

  const handleClearColumn = (column: string) => {
    setSelections((prev) => ({
      ...prev,
      [column]: [],
    }));
    setAutoSelections((prev) => ({
      ...prev,
      [column]: false,
    }));
  };

  return (
    <Box
      sx={{
        p: 3,
        overflowX: 'auto',
        bgcolor: '#fdfdfd', // Paper-ish off-white
        border: '1px solid #e0e0e0',
        borderRadius: 1,
      }}
    >
      <Stack direction="row" spacing={3} sx={{ minWidth: 800 }}>
        {/* Left Info Panel */}
        <Stack
          spacing={2}
          sx={{ width: 180, flexShrink: 0, borderRight: '2px dashed #e0e0e0', pr: 3 }}
        >
          <Typography
            variant="h4"
            sx={{
              color: '#ff6b6b',
              fontWeight: 'bold',
              transform: 'rotate(-90deg)',
              whiteSpace: 'nowrap',
              mt: 10,
              mb: 10,
              textAlign: 'center',
            }}
          >
            Lotto 6/45
          </Typography>
          <Typography variant="caption" color="text.secondary">
            ※ 본 용지는 로또 번호선택용입니다.
          </Typography>
          <Box sx={{ mt: 'auto !important' }}>
            <Typography variant="caption" display="block" color="text.secondary">
              발행 기관: 복권위원회
            </Typography>
            <Typography variant="caption" display="block" color="text.secondary">
              수탁사업자: (주)동행복권
            </Typography>
          </Box>
        </Stack>

        {/* Columns A-E */}
        <Stack direction="row" spacing={2} sx={{ flexGrow: 1 }}>
          {COLUMNS.map((col) => (
            <LottoColumn
              key={col}
              columnId={col}
              selectedNumbers={selections[col]}
              isAuto={autoSelections[col]}
              onToggleNumber={(num) => handleToggleNumber(col, num)}
              onToggleAuto={() => handleToggleAuto(col)}
              onClear={() => handleClearColumn(col)}
            />
          ))}
        </Stack>
      </Stack>
    </Box>
  );
}

// ----------------------------------------------------------------------

type LottoColumnProps = {
  columnId: string;
  selectedNumbers: number[];
  isAuto: boolean;
  onToggleNumber: (num: number) => void;
  onToggleAuto: () => void;
  onClear: () => void;
};

function LottoColumn({
  columnId,
  selectedNumbers,
  isAuto,
  onToggleNumber,
  onToggleAuto,
  onClear,
}: LottoColumnProps) {
  return (
    <Stack
      sx={{
        width: 200,
        border: '1px solid #ff6b6b',
        flexShrink: 0,
      }}
    >
      {/* Header */}
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          bgcolor: '#ff6b6b',
          color: 'white',
          px: 1,
          py: 0.5,
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
          {columnId}
        </Typography>
        <Typography variant="subtitle2">1,000원</Typography>
      </Stack>

      {/* Number Grid */}
      <Box sx={{ p: 1, flexGrow: 1 }}>
        <Grid container spacing={0.5}>
          {NUMBERS.map((num) => {
            const isSelected = selectedNumbers.includes(num);
            return (
              <Grid size={12 / 7} key={num} sx={{ display: 'flex', justifyContent: 'center' }}>
                <Box
                  onClick={() => onToggleNumber(num)}
                  sx={{
                    width: 24,
                    height: 28,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '13px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    userSelect: 'none',

                    ...(isSelected
                      ? {
                          bgcolor: '#333',
                          color: 'white',
                          border: '1px solid #333',
                        }
                      : {
                          color: '#ff6b6b',
                          bgcolor: 'transparent',
                          borderLeft: '1px solid #ff6b6b',
                          borderRight: '1px solid #ff6b6b',
                          backgroundImage: `
                            linear-gradient(to right, #ff6b6b 5px, transparent 5px, transparent calc(100% - 5px), #ff6b6b calc(100% - 5px)),
                            linear-gradient(to right, #ff6b6b 5px, transparent 5px, transparent calc(100% - 5px), #ff6b6b calc(100% - 5px))
                        `,
                          backgroundPosition: 'top, bottom',
                          backgroundSize: '100% 1px',
                          backgroundRepeat: 'no-repeat',
                        }),

                    '&:hover': {
                      bgcolor: isSelected ? '#333' : alpha('#ff6b6b', 0.1),
                    },
                  }}
                >
                  {num}
                </Box>
              </Grid>
            );
          })}
        </Grid>
      </Box>

      {/* Footer Actions */}
      <Stack spacing={1} sx={{ p: 1, borderTop: '1px solid #eee' }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="caption" sx={{ fontSize: '10px' }}>
            자동 선택
          </Typography>
          <Box
            onClick={onToggleAuto}
            sx={{
              width: 12,
              height: 12,
              border: '1px solid #ccc',
              bgcolor: isAuto ? 'black' : 'transparent',
            }}
          />
        </Stack>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="caption" sx={{ fontSize: '10px' }}>
            취소
          </Typography>
          <Box
            onClick={onClear}
            sx={{
              width: 12,
              height: 12,
              border: '1px solid #ccc',
              cursor: 'pointer',
              '&:active': { bgcolor: 'black' },
            }}
          />
        </Stack>
      </Stack>
    </Stack>
  );
}
