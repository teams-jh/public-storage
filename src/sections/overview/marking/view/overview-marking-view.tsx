'use client';

import { useMemo, useState, useEffect } from 'react';

import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

import { DashboardContent } from 'src/layouts/dashboard';
import { getAllLottoNumbers } from 'src/api/lottolibrary';

import { Iconify } from 'src/components/iconify';
import { LottoPaper } from 'src/components/lotto/lotto-paper';

import RoundSlider from '../round-slider';

const OVERLAP_COLORS = ['#00d2ff', '#ff00ea', '#ffb700', '#00ff88', '#7d33ff'];

export type OverviewMarkingViewProps = {
  disableDashboardContent?: boolean;
};

export function OverviewMarkingView({ disableDashboardContent }: OverviewMarkingViewProps) {
  const [data, setData] = useState<any[]>([]);
  const [selectedRound, setSelectedRound] = useState<number | ''>('');
  const [showGrid, setShowGrid] = useState(false);
  const [overlapCount, setOverlapCount] = useState(0); // 0 (off), 1, 2, 3, 4, 5
  const [markingMode, setMarkingMode] = useState<'off' | 'on1' | 'on2'>('on1');

  useEffect(() => {
    const allData = getAllLottoNumbers();
    // Sort descending by round
    const sorted = [...allData].sort((a, b) => b.drwNo - a.drwNo);
    setData(sorted);
    if (sorted.length > 0) {
      setSelectedRound(sorted[0].drwNo);
    }
  }, []);

  const currentData = useMemo(() => {
    if (!selectedRound) return null;
    return data.find((d) => d.drwNo === selectedRound);
  }, [data, selectedRound]);

  const gridData = useMemo(() => {
    if (!selectedRound || data.length === 0) return [];
    const index = data.findIndex((d) => d.drwNo === selectedRound);
    if (index === -1) return [];
    return data.slice(index, index + 10);
  }, [data, selectedRound]);

  const extraLinesData = useMemo(() => {
    if (overlapCount === 0 || !selectedRound || data.length === 0) return [];
    const index = data.findIndex((d) => d.drwNo === selectedRound);
    if (index === -1) return [];

    // Get previous N rounds
    const prevRounds = data.slice(index + 1, index + 1 + overlapCount);
    return prevRounds.map((d, idx) => ({
      numbers: d.numbers,
      color: OVERLAP_COLORS[idx % OVERLAP_COLORS.length],
    }));
  }, [data, selectedRound, overlapCount]);

  const minRound = data.length > 0 ? data[data.length - 1].drwNo : 1;
  const maxRound = data.length > 0 ? data[0].drwNo : 1;

  const content = (
    <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: 1,
          mb: 1.5,
          px: { xs: 0.5, sm: 0 },
        }}
      >
        <Tooltip title="이전 회차 겹쳐보기 (1~5개)">
          <ToggleButtonGroup
            size="small"
            value={overlapCount}
            exclusive
            onChange={(e, newCount) => setOverlapCount(newCount === null ? 0 : newCount)}
            aria-label="overlap count"
            sx={{
              '& .MuiToggleButton-root': {
                border: '1px solid',
                borderColor: 'divider',
              },
            }}
          >
            {[1, 2, 3, 4, 5].map((num) => (
              <ToggleButton
                key={num}
                value={num}
                aria-label={`${num} rounds overlap`}
                sx={{
                  width: { xs: 26, sm: 32 },
                  height: { xs: 26, sm: 32 },
                  fontSize: { xs: 10, sm: 12 },
                  fontWeight: 'bold',
                  px: 0,
                }}
              >
                {num}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Tooltip>

        <ToggleButtonGroup
          size="small"
          value={markingMode}
          exclusive
          onChange={(e, newMode) => newMode !== null && setMarkingMode(newMode)}
          aria-label="marking mode"
          sx={{
            '& .MuiToggleButton-root': {
              border: '1px solid',
              borderColor: 'divider',
            },
          }}
        >
          <Tooltip title="마킹 끔">
            <ToggleButton value="off" sx={{ width: 32, height: 32, px: 0 }}>
              <Iconify icon="mdi:circle-outline" width={20} />
            </ToggleButton>
          </Tooltip>
          <Tooltip title="당첨번호만 마킹">
            <ToggleButton value="on1" sx={{ width: 32, height: 32, px: 0 }}>
              <Iconify icon="mdi:circle" width={20} />
            </ToggleButton>
          </Tooltip>
          <Tooltip title="전체 레이어 마킹">
            <ToggleButton value="on2" sx={{ width: 32, height: 32, px: 0 }}>
              <Iconify icon="mdi:circle-multiple" width={20} />
            </ToggleButton>
          </Tooltip>
        </ToggleButtonGroup>

        <Tooltip title={showGrid ? '단일 보기' : '10개 모아보기'}>
          <IconButton
            onClick={() => setShowGrid(!showGrid)}
            sx={{
              width: 40,
              height: 40,
              display: { xs: 'none', md: 'inline-flex' },
            }}
          >
            <Iconify icon={showGrid ? 'solar:list-bold' : 'solar:widget-5-bold'} width={24} />
          </IconButton>
        </Tooltip>
      </Box>

      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 0.5,
          bgcolor: '#ffffff',
          overflow: 'hidden',
          borderRadius: 1,
        }}
      >
        {showGrid ? (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'repeat(1, 1fr)',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(5, 1fr)',
              },
              gap: 1,
              p: 0,
              transform: { md: 'scale(0.75)', lg: 'scale(0.85)' },
              transformOrigin: 'center center',
            }}
          >
            {gridData.map((d) => {
              const itemIndex = data.findIndex((item) => item.drwNo === d.drwNo);
              const itemExtraLines =
                overlapCount > 0 && itemIndex !== -1
                  ? data.slice(itemIndex + 1, itemIndex + 1 + overlapCount).map((prev, idx) => ({
                      numbers: prev.numbers,
                      color: OVERLAP_COLORS[idx % OVERLAP_COLORS.length],
                    }))
                  : [];

              return (
                <LottoPaper
                  key={d.drwNo}
                  headerText={`${d.drwNo}회`}
                  selectedNumbers={d.numbers}
                  readOnly
                  color="#FF0000"
                  showLines
                  extraLines={itemExtraLines}
                  markingMode={markingMode}
                />
              );
            })}
          </Box>
        ) : (
          currentData && (
            <LottoPaper
              headerText={`${currentData.drwNo}회`}
              selectedNumbers={currentData.numbers}
              readOnly
              color="#FF0000"
              showLines
              extraLines={extraLinesData}
              markingMode={markingMode}
            />
          )
        )}
      </Box>

      {data.length > 0 && selectedRound !== '' && (
        <Box
          sx={{
            px: { xs: 1.5, md: 5 },
            py: 0.5,
            bgcolor: '#ffffff',
            borderTop: '1px solid',
            borderColor: 'divider',
            mt: 1,
            borderRadius: 1,
          }}
        >
          <Box sx={{ maxWidth: 800, mx: 'auto' }}>
            <RoundSlider
              min={minRound}
              max={maxRound}
              value={Number(selectedRound)}
              onChange={(val) => setSelectedRound(val)}
            />
          </Box>
        </Box>
      )}
    </Box>
  );

  if (disableDashboardContent) {
    return content;
  }

  return (
    <DashboardContent maxWidth="xl" sx={{ px: { xs: 0.5, sm: 2 } }}>
      {content}
    </DashboardContent>
  );
}
