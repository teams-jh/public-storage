'use client';

import { useMemo, useState, useCallback } from 'react';

import Tab from '@mui/material/Tab';
import Card from '@mui/material/Card';
import Tabs from '@mui/material/Tabs';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import ToggleButton from '@mui/material/ToggleButton';
import InputAdornment from '@mui/material/InputAdornment';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

import { varAlpha } from 'minimal-shared/utils';

import { DashboardContent } from 'src/layouts/dashboard';
import { getAllLottoNumbers } from 'src/api/lottolibrary';

import { Iconify } from 'src/components/iconify';

import { AnalyticsMissing } from '../analytics-missing';
import { AnalyticsChemistry } from '../analytics-chemistry';
import { AnalyticsCarryOver } from '../analytics-carry-over';
import { AnalyticsAppearance } from '../analytics-appearance';

// ----------------------------------------------------------------------

type PeriodType = '5weeks' | '10weeks' | '6months' | '1year' | 'all';

export function OverviewAnalyticsView() {
  const allLotto = useMemo(() => getAllLottoNumbers(), []);
  const latestRound = allLotto.length > 0 ? allLotto[allLotto.length - 1].drwNo : 0;
  const latestDate =
    allLotto.length > 0 ? new Date(allLotto[allLotto.length - 1].drwNoDate) : new Date();

  const [startRound, setStartRound] = useState(1);
  const [endRound, setEndRound] = useState(latestRound);
  const [includeBonus, setIncludeBonus] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('all');

  // 기간에 따른 시작 회차 계산
  const getStartRoundByPeriod = useCallback(
    (period: PeriodType): number => {
      if (period === 'all') return 1;

      const targetDate = new Date(latestDate);

      switch (period) {
        case '5weeks':
          targetDate.setDate(targetDate.getDate() - 4 * 7);
          break;
        case '10weeks':
          targetDate.setDate(targetDate.getDate() - 9 * 7);
          break;
        case '6months':
          targetDate.setMonth(targetDate.getMonth() - 6);
          break;
        case '1year':
          targetDate.setFullYear(targetDate.getFullYear() - 1);
          break;
        default:
          return 1;
      }

      // targetDate 이후의 첫 번째 회차 찾기
      const foundRound = allLotto.find((r) => new Date(r.drwNoDate) >= targetDate);
      return foundRound ? foundRound.drwNo : 1;
    },
    [allLotto, latestDate]
  );

  // 기간 버튼 클릭 핸들러
  const handlePeriodChange = useCallback(
    (_event: React.MouseEvent<HTMLElement>, newPeriod: PeriodType | null) => {
      if (newPeriod !== null) {
        setSelectedPeriod(newPeriod);
        const newStartRound = getStartRoundByPeriod(newPeriod);
        setStartRound(newStartRound);
        setEndRound(latestRound);
      }
    },
    [getStartRoundByPeriod, latestRound]
  );

  // 수동으로 회차 입력 시 기간 선택 해제
  const handleStartRoundChange = useCallback((value: number) => {
    setStartRound(Math.max(1, value));
    setSelectedPeriod('all'); // 수동 입력 시 전체로 변경 (또는 선택 해제)
  }, []);

  const handleEndRoundChange = useCallback(
    (value: number) => {
      setEndRound(Math.min(latestRound, value));
    },
    [latestRound]
  );

  const filteredRounds = useMemo(
    () => allLotto.filter((r) => r.drwNo >= startRound && r.drwNo <= endRound),
    [allLotto, startRound, endRound]
  );

  return (
    <DashboardContent maxWidth="xl" sx={{ px: { xs: 0.5, sm: 2 } }}>
      <Card sx={{ mb: 2, p: { xs: 1.25, sm: 2 }, borderRadius: 2 }}>
        <Stack
          direction="row"
          flexWrap="wrap"
          spacing={{ xs: 1, sm: 1.5 }}
          alignItems="center"
          justifyContent="center"
          useFlexGap
        >
          <Stack
            direction="row"
            spacing={0.75}
            alignItems="center"
            sx={{
              bgcolor: (theme) => varAlpha(theme.palette.grey['500Channel'], 0.08),
              p: 0.5,
              px: 1,
              borderRadius: 1.5,
              border: (theme) => `1px solid ${varAlpha(theme.palette.grey['500Channel'], 0.12)}`,
            }}
          >
            <TextField
              type="number"
              size="small"
              value={startRound}
              onChange={(e) => handleStartRoundChange(Number(e.target.value))}
              placeholder="시작"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end" sx={{ ml: -0.5, mr: -0.5 }}>
                    <Typography
                      sx={{ fontSize: '0.75rem', fontWeight: 600, color: 'text.secondary' }}
                    >
                      회
                    </Typography>
                  </InputAdornment>
                ),
              }}
              inputProps={{
                min: 1,
                max: endRound,
                style: {
                  textAlign: 'center',
                  padding: '4px 2px',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                },
              }}
              sx={{
                width: { xs: 72, sm: 85 },
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'background.paper',
                  borderRadius: 1,
                  height: 32,
                  boxShadow: (theme) => theme.customShadows.z1,
                  '& fieldset': { borderColor: 'transparent' },
                  '&:hover fieldset': { borderColor: 'primary.main' },
                  '&.Mui-focused fieldset': { borderColor: 'primary.main' },
                },
              }}
            />

            <Typography sx={{ color: 'text.secondary', fontWeight: 'bold', fontSize: '0.85rem' }}>
              ~
            </Typography>

            <TextField
              type="number"
              size="small"
              value={endRound}
              onChange={(e) => handleEndRoundChange(Number(e.target.value))}
              placeholder="최신"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end" sx={{ ml: -0.5, mr: -0.5 }}>
                    <Typography
                      sx={{ fontSize: '0.75rem', fontWeight: 600, color: 'text.secondary' }}
                    >
                      회
                    </Typography>
                  </InputAdornment>
                ),
              }}
              inputProps={{
                min: startRound,
                max: latestRound,
                style: {
                  textAlign: 'center',
                  padding: '4px 2px',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                },
              }}
              sx={{
                width: { xs: 72, sm: 85 },
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'background.paper',
                  borderRadius: 1,
                  height: 32,
                  boxShadow: (theme) => theme.customShadows.z1,
                  '& fieldset': { borderColor: 'transparent' },
                  '&:hover fieldset': { borderColor: 'primary.main' },
                  '&.Mui-focused fieldset': { borderColor: 'primary.main' },
                },
              }}
            />
          </Stack>

          <ToggleButtonGroup
            value={selectedPeriod}
            exclusive
            onChange={handlePeriodChange}
            size="small"
            sx={{
              '& .MuiToggleButton-root': {
                px: { xs: 1, sm: 1.5 },
                py: 0.5,
                height: 32,
                fontSize: { xs: '0.75rem', sm: '0.85rem' },
                fontWeight: 600,
                whiteSpace: 'nowrap',
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                },
              },
            }}
          >
            <ToggleButton value="5weeks">5주</ToggleButton>
            <ToggleButton value="10weeks">10주</ToggleButton>
            <ToggleButton value="6months">6개월</ToggleButton>
            <ToggleButton value="1year">1년</ToggleButton>
            <ToggleButton value="all">전체</ToggleButton>
          </ToggleButtonGroup>

          <ToggleButtonGroup
            size="small"
            value={includeBonus ? ['showBonus'] : []}
            onChange={(event, newValues) => {
              setIncludeBonus(newValues.includes('showBonus'));
            }}
            aria-label="bonus settings"
          >
            <Tooltip title="보너스 번호 포함">
              <ToggleButton
                value="showBonus"
                aria-label="show bonus"
                sx={{
                  width: 32,
                  height: 32,
                  p: 0,
                  '&.Mui-selected': {
                    backgroundColor: 'primary.main',
                    color: 'primary.contrastText',
                    '&:hover': {
                      backgroundColor: 'primary.dark',
                    },
                  },
                }}
              >
                <Iconify icon="mdi:star-circle-outline" width={18} />
              </ToggleButton>
            </Tooltip>
          </ToggleButtonGroup>
        </Stack>
      </Card>

      <Tabs
        value={currentTab}
        onChange={(e, newValue) => setCurrentTab(newValue)}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        sx={{
          mb: 2,
          minHeight: 38,
          borderBottom: 1,
          borderColor: 'divider',
          '& .MuiTab-root': {
            fontSize: { xs: '0.85rem', sm: '0.95rem' },
            fontWeight: 700,
            px: { xs: 1.5, sm: 2.5 },
            minWidth: 'auto',
            minHeight: 38,
            py: 0.5,
          },
        }}
      >
        <Tab label="출현 순위" />
        <Tab label="미출현 번호" />
        <Tab label="이월 순위" />
        <Tab label="궁합수 순위" />
      </Tabs>

      {currentTab === 0 && (
        <AnalyticsAppearance rounds={filteredRounds} includeBonus={includeBonus} />
      )}

      {currentTab === 1 && (
        <AnalyticsMissing allLotto={allLotto} endRound={endRound} includeBonus={includeBonus} />
      )}

      {currentTab === 2 && (
        <AnalyticsCarryOver
          allLotto={allLotto}
          startRound={startRound}
          endRound={endRound}
          includeBonus={includeBonus}
        />
      )}

      {currentTab === 3 && (
        <AnalyticsChemistry rounds={filteredRounds} includeBonus={includeBonus} />
      )}
    </DashboardContent>
  );
}
