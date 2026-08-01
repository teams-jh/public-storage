'use client';

import { varAlpha } from 'minimal-shared/utils';
import { useMemo, useState, useEffect, useCallback } from 'react';

import Box from '@mui/material/Box';
import Tab from '@mui/material/Tab';
import Card from '@mui/material/Card';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Tabs from '@mui/material/Tabs';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import Switch from '@mui/material/Switch';
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import DialogTitle from '@mui/material/DialogTitle';
import ToggleButton from '@mui/material/ToggleButton';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import LinearProgress from '@mui/material/LinearProgress';
import TableContainer from '@mui/material/TableContainer';
import FormControlLabel from '@mui/material/FormControlLabel';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

import { DashboardContent } from 'src/layouts/dashboard';
import { getBallColor, getAllLottoNumbers } from 'src/api/lottolibrary';

import { Iconify } from 'src/components/iconify';

// ----------------------------------------------------------------------

const LOTTO_NUMBERS = Array.from({ length: 45 }, (_, i) => i + 1);

// Responsive Lotto Ball Component
type LottoBallProps = {
  number: number;
  size?: number;
  highlighted?: boolean;
};

function LottoBall({ number, size = 36, highlighted = true }: LottoBallProps) {
  const color = getBallColor(number);
  return (
    <Box
      sx={{
        width: size,
        height: size,
        aspectRatio: '1 / 1',
        flexShrink: 0,
        borderRadius: '50%',
        bgcolor: highlighted ? color : 'grey.300',
        color: highlighted ? '#fff' : 'text.disabled',
        fontWeight: 'bold',
        fontSize: size * 0.45,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: highlighted
          ? 'inset -2px -2px 4px rgba(0,0,0,0.2), 2px 2px 4px rgba(0,0,0,0.1)'
          : 'none',
        border: highlighted ? '1px solid rgba(255,255,255,0.2)' : '1px dashed rgba(0,0,0,0.1)',
        opacity: highlighted ? 1 : 0.25,
        transition: 'all 0.2s ease',
      }}
    >
      {number}
    </Box>
  );
}

// Generate combinations of size k from an array of numbers
function getCombinations(arr: number[], k: number): number[][] {
  const result: number[][] = [];
  function backtrack(start: number, current: number[]) {
    if (current.length === k) {
      result.push([...current]);
      return;
    }
    for (let i = start; i < arr.length; i += 1) {
      current.push(arr[i]);
      backtrack(i + 1, current);
      current.pop();
    }
  }
  backtrack(0, []);
  return result;
}

// Section title helper
function SectionLabel({ icon, label }: { icon: string; label: string }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
      <Iconify icon={icon} width={18} sx={{ color: 'text.secondary' }} />
      <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
        {label}
      </Typography>
    </Stack>
  );
}

// Table header cell helper
const headerCellSx = {
  fontWeight: 'bold',
  bgcolor: (theme: any) => varAlpha(theme.vars.palette.grey['500Channel'], 0.08),
  borderBottom: '2px solid',
  borderBottomColor: 'divider',
  py: 1,
  px: { xs: 1, sm: 1.5 },
  fontSize: { xs: '0.75rem', sm: '0.8125rem' },
  whiteSpace: 'nowrap',
};

export function OverviewRoundView() {
  const allLotto = useMemo(() => getAllLottoNumbers(), []);
  const latestRound = useMemo(
    () => (allLotto.length > 0 ? allLotto[allLotto.length - 1].drwNo : 0),
    [allLotto]
  );

  // Mode Selection State
  const [analysisMode, setAnalysisMode] = useState<'round' | 'custom'>('round');
  const [customNumbers, setCustomNumbers] = useState<number[]>([]);

  const [X, setX] = useState<number>(0);
  const [A, setA] = useState<number>(1);
  const [B, setB] = useState<number>(1);
  const [includeBonus, setIncludeBonus] = useState<boolean>(false);
  const [currentTab, setCurrentTab] = useState<number>(0);
  const [comboSize, setComboSize] = useState<number>(2);

  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [modalTitle, setModalTitle] = useState<string>('');
  const [modalRounds, setModalRounds] = useState<any[]>([]);
  const [highlightNumbers, setHighlightNumbers] = useState<number[]>([]);
  const [modalSortOrder, setModalSortOrder] = useState<'desc' | 'asc'>('desc');
  const [companionSortOrder, setCompanionSortOrder] = useState<'desc' | 'asc'>('desc');

  const sortedModalRounds = useMemo(
    () =>
      [...modalRounds].sort((a, b) => {
        if (modalSortOrder === 'desc') {
          return b.drwNo - a.drwNo;
        }
        return a.drwNo - b.drwNo;
      }),
    [modalRounds, modalSortOrder]
  );

  const lastMatchedRound = useMemo(() => {
    if (modalRounds.length === 0) return 0;
    return Math.max(...modalRounds.map((r) => r.drwNo));
  }, [modalRounds]);

  const unappearedRounds = latestRound - lastMatchedRound;

  // Initialize values when component mounts and data is loaded
  useEffect(() => {
    if (latestRound > 0) {
      setX(latestRound);
      setB(latestRound - 1);
    }
  }, [latestRound]);

  // Target draw numbers based on mode
  const targetDraw = useMemo(() => allLotto.find((item) => item.drwNo === X), [allLotto, X]);
  const targetNumbers = useMemo(() => {
    if (analysisMode === 'round') {
      return targetDraw ? targetDraw.numbers : [];
    }
    return [...customNumbers].sort((a, b) => a - b);
  }, [analysisMode, targetDraw, customNumbers]);
  const targetBonus = useMemo(() => (targetDraw ? targetDraw.bonus : 0), [targetDraw]);

  // Check if analysis is ready
  const isAnalysisReady = useMemo(() => {
    if (analysisMode === 'round') {
      return targetNumbers.length === 6;
    }
    return targetNumbers.length >= 1;
  }, [analysisMode, targetNumbers]);

  // Adjust combo size if selected numbers decrease below current combo size
  useEffect(() => {
    if (
      analysisMode === 'custom' &&
      targetNumbers.length >= 2 &&
      comboSize > targetNumbers.length
    ) {
      setComboSize(targetNumbers.length);
    }
  }, [targetNumbers.length, comboSize, analysisMode]);

  // Switch to Companion numbers tab if only 1 number is selected
  useEffect(() => {
    if (analysisMode === 'custom' && targetNumbers.length === 1 && currentTab !== 3) {
      setCurrentTab(3);
    }
  }, [targetNumbers.length, currentTab, analysisMode]);

  const safeTabValue = useMemo(() => {
    if (analysisMode === 'custom' && targetNumbers.length === 1) {
      return 3;
    }
    return currentTab;
  }, [analysisMode, targetNumbers.length, currentTab]);

  // Mode change handler
  const handleModeChange = (newMode: 'round' | 'custom') => {
    setAnalysisMode(newMode);
    if (newMode === 'round') {
      const maxB = X - 1;
      setB((prevB) => Math.min(prevB, maxB));
      setA((prevA) => Math.min(prevA, maxB));
    } else {
      // In custom mode, max B can go up to latestRound
      setB(latestRound);
    }
  };

  // Safe handlers that enforce constraints
  const handleXChange = (val: number) => {
    const nextX = Math.min(latestRound, Math.max(2, val));
    setX(nextX);
    if (analysisMode === 'round') {
      setB((prevB) => Math.min(prevB, nextX - 1));
      setA((prevA) => Math.min(prevA, nextX - 1));
    }
  };

  const handleAChange = (val: number) => {
    const nextA = Math.min(B, Math.max(1, val));
    setA(nextA);
  };

  const handleBChange = (val: number) => {
    const maxB = analysisMode === 'round' ? X - 1 : latestRound;
    const nextB = Math.min(maxB, Math.max(A, val));
    setB(nextB);
  };

  const applyPreset = (presetType: 'all' | '100' | '200' | '500') => {
    const reference = analysisMode === 'round' ? X : latestRound + 1;
    if (reference < 2) return;
    const maxB = reference - 1;
    let nextA = 1;

    if (presetType === '100') nextA = Math.max(1, reference - 100);
    else if (presetType === '200') nextA = Math.max(1, reference - 200);
    else if (presetType === '500') nextA = Math.max(1, reference - 500);

    setA(nextA);
    setB(maxB);
  };

  // Custom Selection Actions
  const handleToggleCustomNumber = (num: number) => {
    setCustomNumbers((prev) => {
      if (prev.includes(num)) {
        return prev.filter((n) => n !== num);
      }
      if (prev.length >= 6) {
        return prev;
      }
      return [...prev, num];
    });
  };

  const handleRandomSelect = () => {
    const numbers: number[] = [];
    while (numbers.length < 6) {
      const rand = Math.floor(Math.random() * 45) + 1;
      if (!numbers.includes(rand)) {
        numbers.push(rand);
      }
    }
    setCustomNumbers(numbers.sort((a, b) => a - b));
  };

  const handleFillLatest = () => {
    const latest = allLotto.length > 0 ? allLotto[allLotto.length - 1] : null;
    if (latest) {
      setCustomNumbers([...latest.numbers].sort((a, b) => a - b));
    }
  };

  const handleClearCustom = () => {
    setCustomNumbers([]);
  };

  // 1. Calculate Match Count Statistics
  const matchCountStats = useMemo(() => {
    if (!isAnalysisReady || A > B) {
      return { 2: [], 3: [], 4: [], 5: [] };
    }

    const historicalRounds = allLotto.filter((r) => r.drwNo >= A && r.drwNo <= B);
    const m2: any[] = [];
    const m3: any[] = [];
    const m4: any[] = [];
    const m5: any[] = [];

    historicalRounds.forEach((r) => {
      const pool = includeBonus ? [...r.numbers, r.bonus] : r.numbers;
      const matched = pool.filter((n) => targetNumbers.includes(n));
      const matchCount = matched.length;

      const roundData = {
        drwNo: r.drwNo,
        numbers: r.numbers,
        bonus: r.bonus,
        drwNoDate: r.drwNoDate,
        matchedNumbers: matched,
      };

      if (matchCount === 2) m2.push(roundData);
      else if (matchCount === 3) m3.push(roundData);
      else if (matchCount === 4) m4.push(roundData);
      else if (matchCount === 5) m5.push(roundData);
    });

    return { 2: m2, 3: m3, 4: m4, 5: m5 };
  }, [isAnalysisReady, targetNumbers, A, B, includeBonus, allLotto]);

  // 2. Calculate Combination Occurrence Statistics
  const combinationStats = useMemo(() => {
    if (!isAnalysisReady || A > B) return [];

    const combos =
      analysisMode === 'custom'
        ? LOTTO_NUMBERS.filter((num) => !targetNumbers.includes(num)).map((num) =>
            [...targetNumbers, num].sort((a, b) => a - b)
          )
        : getCombinations(targetNumbers, comboSize);
    const historicalRounds = allLotto.filter((r) => r.drwNo >= A && r.drwNo <= B);

    const stats = combos.map((combo) => {
      const matchedRounds = historicalRounds.filter((r) => {
        const pool = includeBonus ? [...r.numbers, r.bonus] : r.numbers;
        return combo.every((num) => pool.includes(num));
      });

      return {
        combo: [...combo].sort((a, b) => a - b),
        count: matchedRounds.length,
        matchedRounds,
      };
    });

    return stats.sort((a, b) => b.count - a.count);
  }, [isAnalysisReady, targetNumbers, A, B, comboSize, includeBonus, allLotto, analysisMode]);

  // 3. Calculate Single Number Statistics
  const singleNumberStats = useMemo(() => {
    if (!isAnalysisReady || A > B) return [];

    const historicalRounds = allLotto.filter((r) => r.drwNo >= A && r.drwNo <= B);

    const stats = targetNumbers.map((num) => {
      const matchedRounds = historicalRounds.filter((r) => {
        const pool = includeBonus ? [...r.numbers, r.bonus] : r.numbers;
        return pool.includes(num);
      });

      return {
        number: num,
        count: matchedRounds.length,
        matchedRounds,
      };
    });

    return stats.sort((a, b) => b.count - a.count);
  }, [isAnalysisReady, targetNumbers, A, B, includeBonus, allLotto]);

  // 4. Calculate Unappeared Companion Number Statistics
  const companionNumberStats = useMemo(() => {
    if (!isAnalysisReady) return [];

    const remainingNumbers = LOTTO_NUMBERS.filter((num) => !targetNumbers.includes(num));

    const stats = remainingNumbers.map((x) => {
      const combo = [...targetNumbers, x];
      const matchedRounds = allLotto.filter((r) => {
        const pool = includeBonus ? [...r.numbers, r.bonus] : r.numbers;
        return combo.every((num) => pool.includes(num));
      });

      const lastDrwNo =
        matchedRounds.length > 0 ? Math.max(...matchedRounds.map((r) => r.drwNo)) : 0;
      const gap = lastDrwNo > 0 ? latestRound - lastDrwNo : latestRound;

      return {
        number: x,
        lastDrwNo,
        gap,
        matchedRounds,
      };
    });

    return stats.sort((a, b) => {
      if (companionSortOrder === 'desc') {
        return b.gap - a.gap;
      }
      return a.gap - b.gap;
    });
  }, [isAnalysisReady, targetNumbers, includeBonus, allLotto, latestRound, companionSortOrder]);

  const totalRounds = B - A + 1;

  // Max count for progress bar scaling
  const maxComboCount = useMemo(
    () => Math.max(1, ...combinationStats.map((s) => s.count)),
    [combinationStats]
  );
  const maxSingleCount = useMemo(
    () => Math.max(1, ...singleNumberStats.map((s) => s.count)),
    [singleNumberStats]
  );
  const maxCompanionGap = useMemo(
    () => Math.max(1, ...companionNumberStats.map((s) => s.gap)),
    [companionNumberStats]
  );

  const handleOpenMatchModal = (k: number) => {
    const rounds = matchCountStats[k as 2 | 3 | 4 | 5] || [];
    setModalTitle(`${k}개 번호 일치 회차 목록 (총 ${rounds.length}회)`);
    setModalRounds(rounds);
    setHighlightNumbers(targetNumbers);
    setModalOpen(true);
  };

  const handleOpenComboModal = (combo: number[], count: number, matchedRounds: any[]) => {
    const comboText = combo.length === 1 ? `번호 ${combo[0]}` : `조합 [${combo.join(', ')}]`;
    setModalTitle(`${comboText} 출현 회차 목록 (총 ${count}회)`);
    setModalRounds(matchedRounds);
    setHighlightNumbers(combo);
    setModalOpen(true);
  };

  const getRoundGapInfo = useCallback(
    (currentRoundNo: number, highlightNums: number[]) => {
      if (highlightNums.length === 0) return { gap: 0, isFirst: false };

      for (let i = currentRoundNo - 2; i >= 0; i -= 1) {
        const r = allLotto[i];
        const pool = includeBonus ? [...r.numbers, r.bonus] : r.numbers;
        const isMatch = highlightNums.every((num) => pool.includes(num));
        if (isMatch) {
          return { gap: currentRoundNo - r.drwNo, isFirst: false };
        }
      }
      return { gap: 0, isFirst: true };
    },
    [allLotto, includeBonus]
  );

  const handleSelectRoundFromModal = (roundNo: number) => {
    if (analysisMode === 'round') {
      handleXChange(roundNo);
    } else {
      const target = allLotto.find((item) => item.drwNo === roundNo);
      if (target) {
        setCustomNumbers([...target.numbers].sort((a, b) => a - b));
      }
    }
    setModalOpen(false);
  };

  return (
    <DashboardContent maxWidth="xl" sx={{ px: { xs: 0.5, sm: 2 } }}>
      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 0.5 }}>
        <Iconify icon="solar:chart-2-bold-duotone" width={28} sx={{ color: 'primary.main' }} />
        <Typography variant="h4">회차분석</Typography>
      </Stack>
      <Typography variant="body2" sx={{ mb: 2.5, color: 'text.secondary' }}>
        분석할 당첨 번호(특정 회차 혹은 사용자 직접 선택)가 지정한 분석 범위(A ~ B회차) 내에서 동반
        출현한 통계를 분석합니다.
      </Typography>

      <Grid container spacing={3}>
        {/* Left Settings Panel & Target Input/Selection */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Stack spacing={3}>
            {/* Settings Card */}
            <Card sx={{ p: { xs: 1.5, sm: 3 } }}>
              <SectionLabel icon="solar:settings-bold-duotone" label="분석 모드" />

              <ToggleButtonGroup
                value={analysisMode}
                exclusive
                onChange={(e, val) => val !== null && handleModeChange(val)}
                fullWidth
                color="primary"
                sx={{ mb: 2 }}
                size="small"
              >
                <ToggleButton
                  value="round"
                  sx={{ fontWeight: 'bold', fontSize: { xs: '0.75rem', sm: '0.875rem' } }}
                >
                  <Iconify icon="solar:calendar-date-bold" width={16} sx={{ mr: 0.5 }} />
                  회차별 당첨번호
                </ToggleButton>
                <ToggleButton
                  value="custom"
                  sx={{ fontWeight: 'bold', fontSize: { xs: '0.75rem', sm: '0.875rem' } }}
                >
                  <Iconify icon="solar:hand-stars-bold" width={16} sx={{ mr: 0.5 }} />
                  사용자 직접선택
                </ToggleButton>
              </ToggleButtonGroup>

              <Divider sx={{ mb: 2 }} />

              <Stack spacing={2}>
                {analysisMode === 'round' && (
                  <>
                    <SectionLabel icon="solar:target-bold-duotone" label="대상 회차" />
                    <Stack
                      direction="row"
                      alignItems="center"
                      sx={{
                        bgcolor: (theme) => varAlpha(theme.palette.grey['500Channel'], 0.08),
                        p: 0.5,
                        px: 1,
                        borderRadius: 1.5,
                        border: (theme) =>
                          `1px solid ${varAlpha(theme.palette.grey['500Channel'], 0.12)}`,
                      }}
                    >
                      <TextField
                        type="number"
                        size="small"
                        value={X || ''}
                        onChange={(e) => handleXChange(Number(e.target.value))}
                        placeholder="대상 회차"
                        InputProps={{
                          endAdornment: (
                            <InputAdornment position="end" sx={{ ml: -0.5, mr: -0.5 }}>
                              <Typography
                                sx={{
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                  color: 'text.secondary',
                                }}
                              >
                                회
                              </Typography>
                            </InputAdornment>
                          ),
                        }}
                        inputProps={{
                          min: 2,
                          max: latestRound,
                          style: {
                            textAlign: 'center',
                            padding: '4px 2px',
                            fontSize: '0.85rem',
                            fontWeight: 700,
                          },
                        }}
                        sx={{
                          width: '100%',
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
                  </>
                )}

                <SectionLabel icon="solar:sort-horizontal-bold-duotone" label="분석 범위" />
                <Stack
                  direction="row"
                  spacing={0.75}
                  alignItems="center"
                  sx={{
                    bgcolor: (theme) => varAlpha(theme.palette.grey['500Channel'], 0.08),
                    p: 0.5,
                    px: 1,
                    borderRadius: 1.5,
                    border: (theme) =>
                      `1px solid ${varAlpha(theme.palette.grey['500Channel'], 0.12)}`,
                  }}
                >
                  <TextField
                    type="number"
                    size="small"
                    value={A || ''}
                    onChange={(e) => handleAChange(Number(e.target.value))}
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
                      max: B,
                      style: {
                        textAlign: 'center',
                        padding: '4px 2px',
                        fontSize: '0.85rem',
                        fontWeight: 700,
                      },
                    }}
                    sx={{
                      flex: 1,
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

                  <Typography
                    sx={{ color: 'text.secondary', fontWeight: 'bold', fontSize: '0.85rem' }}
                  >
                    ~
                  </Typography>

                  <TextField
                    type="number"
                    size="small"
                    value={B || ''}
                    onChange={(e) => handleBChange(Number(e.target.value))}
                    placeholder="종료"
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
                      min: A,
                      max: analysisMode === 'round' ? X - 1 : latestRound,
                      style: {
                        textAlign: 'center',
                        padding: '4px 2px',
                        fontSize: '0.85rem',
                        fontWeight: 700,
                      },
                    }}
                    sx={{
                      flex: 1,
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

                {/* Preset Ranges */}
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {[
                    { key: 'all' as const, label: '전체' },
                    { key: '100' as const, label: '최근 100회' },
                    { key: '200' as const, label: '최근 200회' },
                    { key: '500' as const, label: '최근 500회' },
                  ].map((preset) => (
                    <Chip
                      key={preset.key}
                      label={preset.label}
                      size="small"
                      variant="outlined"
                      onClick={() => applyPreset(preset.key)}
                      sx={{
                        cursor: 'pointer',
                        '&:hover': {
                          bgcolor: (theme) =>
                            varAlpha(theme.vars.palette.primary.mainChannel, 0.08),
                        },
                      }}
                    />
                  ))}
                </Stack>

                <Divider />

                <FormControlLabel
                  control={
                    <Switch
                      checked={includeBonus}
                      onChange={(e) => setIncludeBonus(e.target.checked)}
                    />
                  }
                  label={<Typography variant="body2">과거 회차 보너스 번호 포함</Typography>}
                />
              </Stack>

              {/* Summary info */}
              {isAnalysisReady && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Chip
                      icon={<Iconify icon="solar:database-bold" width={16} />}
                      label={`분석 대상: ${totalRounds.toLocaleString()}회`}
                      size="small"
                      color="primary"
                      variant="soft"
                    />
                    <Chip
                      icon={<Iconify icon="solar:calendar-date-bold" width={16} />}
                      label={`${A}회 ~ ${B}회`}
                      size="small"
                      color="info"
                      variant="soft"
                    />
                  </Stack>
                </>
              )}
            </Card>

            {/* Target Display/Selector Card */}
            {analysisMode === 'round' ? (
              <Card sx={{ p: { xs: 1.5, sm: 3 } }}>
                <SectionLabel icon="solar:ticket-bold-duotone" label={`${X}회차 당첨 정보`} />
                {targetDraw ? (
                  <>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      추첨일: {targetDraw.drwNoDate}
                    </Typography>

                    <Stack
                      direction="row"
                      alignItems="center"
                      spacing={{ xs: 0.5, sm: 1 }}
                      flexWrap="wrap"
                      useFlexGap
                    >
                      {targetNumbers.map((num) => (
                        <LottoBall key={num} number={num} size={30} />
                      ))}
                      <Typography variant="h6" sx={{ mx: 0.25, color: 'text.secondary' }}>
                        +
                      </Typography>
                      <Stack alignItems="center">
                        <LottoBall number={targetBonus} size={30} />
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ mt: 0.25, fontSize: '0.7rem' }}
                        >
                          보너스
                        </Typography>
                      </Stack>
                    </Stack>
                  </>
                ) : (
                  <Typography variant="body2" color="text.disabled">
                    회차 정보를 찾을 수 없습니다.
                  </Typography>
                )}
              </Card>
            ) : (
              <Card sx={{ p: { xs: 1.5, sm: 3 } }}>
                <SectionLabel icon="solar:hand-stars-bold-duotone" label="직접 번호 선택" />
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  분석에 사용할 번호(1~6개)를 아래 숫자 판에서 선택하세요.
                </Typography>

                <Stack
                  direction="row"
                  spacing={1}
                  sx={{
                    minHeight: 48,
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px dashed',
                    borderColor: customNumbers.length >= 1 ? 'primary.main' : 'divider',
                    borderRadius: 1,
                    mb: 2,
                    p: 1,
                    bgcolor: 'background.neutral',
                    transition: 'border-color 0.2s ease',
                  }}
                >
                  {customNumbers.length === 0 ? (
                    <Typography variant="body2" color="text.disabled">
                      번호를 선택해 주세요 (최소 1개)
                    </Typography>
                  ) : (
                    <Stack direction="row" spacing={0.8}>
                      {customNumbers.map((num) => (
                        <LottoBall key={num} number={num} size={30} />
                      ))}
                      {customNumbers.length < 6 && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ alignSelf: 'center', ml: 1 }}
                        >
                          ({customNumbers.length}/6)
                        </Typography>
                      )}
                    </Stack>
                  )}
                </Stack>

                {/* 1-45 Grid */}
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(7, 1fr)',
                    gap: 0.8,
                    p: 1.5,
                    borderRadius: 1,
                    bgcolor: 'background.neutral',
                  }}
                >
                  {LOTTO_NUMBERS.map((num) => {
                    const isSelected = customNumbers.includes(num);
                    const ballColor = getBallColor(num);
                    return (
                      <Box
                        key={num}
                        onClick={() => handleToggleCustomNumber(num)}
                        sx={{
                          aspectRatio: '1/1',
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                          fontWeight: 'bold',
                          fontSize: '0.8rem',
                          bgcolor: isSelected ? ballColor : 'background.paper',
                          color: isSelected ? '#fff' : 'text.primary',
                          border: (theme) =>
                            `1px solid ${isSelected ? 'transparent' : theme.vars.palette.divider}`,
                          boxShadow: isSelected ? '1px 1px 3px rgba(0,0,0,0.15)' : 'none',
                          transition: 'all 0.15s ease',
                          '&:hover': {
                            bgcolor: isSelected ? ballColor : 'grey.200',
                            transform: 'scale(1.1)',
                          },
                        }}
                      >
                        {num}
                      </Box>
                    );
                  })}
                </Box>

                {/* Action Buttons */}
                <Stack direction="row" spacing={1} sx={{ mt: 2 }} justifyContent="space-between">
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleClearCustom}
                    sx={{ flex: 1 }}
                    startIcon={<Iconify icon="solar:restart-bold" width={16} />}
                  >
                    초기화
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleRandomSelect}
                    sx={{ flex: 1 }}
                    startIcon={<Iconify icon="solar:shuffle-bold" width={16} />}
                  >
                    무작위
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleFillLatest}
                    sx={{ flex: 1 }}
                    startIcon={<Iconify icon="solar:star-bold" width={16} />}
                  >
                    최근당첨
                  </Button>
                </Stack>
              </Card>
            )}
          </Stack>
        </Grid>

        {/* Right Analysis Tabs */}
        <Grid size={{ xs: 12, md: 8 }}>
          {!isAnalysisReady ? (
            <Card
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 480,
                textAlign: 'center',
                p: 4,
              }}
            >
              <Iconify
                icon="solar:info-circle-bold-duotone"
                width={64}
                height={64}
                sx={{ color: 'text.secondary', mb: 2 }}
              />
              <Typography variant="h6" color="text.secondary">
                분석할 번호를 선택해 주세요
              </Typography>
              <Typography variant="body2" color="text.disabled" sx={{ mt: 1, maxWidth: 320 }}>
                왼쪽 &apos;직접 번호 선택&apos; 영역에서 번호를 최소 1개 이상 선택하면 분석 결과가
                나타납니다. (최대 6개)
              </Typography>
            </Card>
          ) : (
            <Card>
              {/* Tab Headers - Using MUI Tabs for cleaner look */}
              <Box
                sx={{
                  borderBottom: 1,
                  borderColor: 'divider',
                  bgcolor: (theme) => varAlpha(theme.vars.palette.grey['500Channel'], 0.04),
                }}
              >
                <Tabs
                  value={safeTabValue}
                  onChange={(e, val) => setCurrentTab(val)}
                  variant="scrollable"
                  scrollButtons="auto"
                  allowScrollButtonsMobile
                  sx={{
                    px: { xs: 1, sm: 2 },
                    minHeight: 40,
                    '& .MuiTab-root': {
                      fontWeight: 'bold',
                      minHeight: 40,
                      py: 0.5,
                      px: { xs: 1.5, sm: 2 },
                      fontSize: { xs: '0.8rem', sm: '0.875rem' },
                      whiteSpace: 'nowrap',
                    },
                  }}
                >
                  {targetNumbers.length >= 2 && (
                    <Tab
                      value={0}
                      label="번호 조합별 분석"
                      icon={<Iconify icon="solar:layers-bold" width={20} />}
                      iconPosition="start"
                    />
                  )}
                  {targetNumbers.length >= 2 && (
                    <Tab
                      value={1}
                      label="일치 개수별 통계"
                      icon={<Iconify icon="solar:chart-2-bold" width={20} />}
                      iconPosition="start"
                    />
                  )}
                  {targetNumbers.length >= 2 && (
                    <Tab
                      value={2}
                      label="개별 번호 통계"
                      icon={<Iconify icon="solar:hashtag-bold" width={20} />}
                      iconPosition="start"
                    />
                  )}
                  <Tab
                    value={3}
                    label="미출현 짝번호"
                    icon={<Iconify icon="solar:link-broken-bold" width={20} />}
                    iconPosition="start"
                  />
                </Tabs>
              </Box>

              {/* Tab 0: Combinations Analysis */}
              {currentTab === 0 && (
                <Box sx={{ p: { xs: 1.5, sm: 3 } }}>
                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ mb: 3 }}
                  >
                    <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '55%' }}>
                      {analysisMode === 'round' ? (
                        <>
                          <strong>{X}회차</strong>의 6개 번호 중 {comboSize}개씩 조합하여{' '}
                          <strong>
                            {A} ~ {B}회차
                          </strong>
                          에서의 동반 출현 횟수입니다.
                        </>
                      ) : (
                        <>
                          선택한 <strong>{targetNumbers.length}개 번호</strong>에 나머지 번호 1개를
                          추가하여{' '}
                          <strong>
                            {A} ~ {B}회차
                          </strong>
                          에서의 동반 출현 횟수입니다.
                        </>
                      )}
                    </Typography>

                    {analysisMode === 'round' && (
                      <ToggleButtonGroup
                        value={comboSize}
                        exclusive
                        onChange={(e, val) => val !== null && setComboSize(val)}
                        size="small"
                        color="primary"
                      >
                        {[2, 3, 4, 5]
                          .filter((size) => size <= targetNumbers.length)
                          .map((size) => (
                            <ToggleButton key={size} value={size} sx={{ px: 1.5 }}>
                              {size}개
                            </ToggleButton>
                          ))}
                      </ToggleButtonGroup>
                    )}
                  </Stack>

                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={headerCellSx}>조합 번호</TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            출현 횟수
                          </TableCell>
                          <TableCell align="center" sx={{ ...headerCellSx, minWidth: 160 }}>
                            출현 비율
                          </TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            조회
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {combinationStats.map((stat, idx) => {
                          const percentage =
                            totalRounds > 0
                              ? ((stat.count / totalRounds) * 100).toFixed(2)
                              : '0.00';
                          const progressValue = (stat.count / maxComboCount) * 100;
                          const extraNumber =
                            analysisMode === 'custom'
                              ? stat.combo.find((num) => !targetNumbers.includes(num))
                              : undefined;
                          return (
                            <TableRow
                              key={idx}
                              hover
                              sx={{
                                '&:nth-of-type(even)': {
                                  bgcolor: (theme) =>
                                    varAlpha(theme.vars.palette.grey['500Channel'], 0.03),
                                },
                              }}
                            >
                              <TableCell>
                                {analysisMode === 'custom' ? (
                                  <Stack direction="row" spacing={0.8} alignItems="center">
                                    {targetNumbers.map((num) => (
                                      <LottoBall key={num} number={num} size={28} />
                                    ))}
                                    <Typography
                                      variant="body2"
                                      sx={{ mx: 0.5, color: 'text.secondary', fontWeight: 'bold' }}
                                    >
                                      +
                                    </Typography>
                                    {extraNumber !== undefined && (
                                      <LottoBall number={extraNumber} size={28} />
                                    )}
                                  </Stack>
                                ) : (
                                  <Stack direction="row" spacing={0.8}>
                                    {stat.combo.map((num) => (
                                      <LottoBall key={num} number={num} size={28} />
                                    ))}
                                  </Stack>
                                )}
                              </TableCell>
                              <TableCell align="center">
                                <Typography
                                  variant="body2"
                                  sx={{ fontWeight: 'bold', color: 'primary.main' }}
                                >
                                  {stat.count}회
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Stack spacing={0.5} alignItems="center">
                                  <Typography variant="caption">{percentage}%</Typography>
                                  <LinearProgress
                                    variant="determinate"
                                    value={progressValue}
                                    sx={{
                                      width: '100%',
                                      height: 6,
                                      borderRadius: 3,
                                      bgcolor: (theme) =>
                                        varAlpha(theme.vars.palette.primary.mainChannel, 0.08),
                                      '& .MuiLinearProgress-bar': { borderRadius: 3 },
                                    }}
                                  />
                                </Stack>
                              </TableCell>
                              <TableCell align="center">
                                <Tooltip title="출현 회차 목록 보기">
                                  <span>
                                    <Button
                                      size="small"
                                      variant="soft"
                                      onClick={() =>
                                        handleOpenComboModal(
                                          stat.combo,
                                          stat.count,
                                          stat.matchedRounds
                                        )
                                      }
                                      disabled={stat.count === 0}
                                      startIcon={<Iconify icon="solar:eye-bold" />}
                                    >
                                      보기
                                    </Button>
                                  </span>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}

              {/* Tab 1: Match Count Summary */}
              {currentTab === 1 && (
                <Box sx={{ p: 3 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    {analysisMode === 'round' ? (
                      <>
                        <strong>{X}회차</strong> 당첨 번호 6개와{' '}
                        <strong>
                          {A} ~ {B}회차
                        </strong>
                        의 과거 당첨 번호가 몇 개 일치하는지 분석한 결과입니다.
                      </>
                    ) : (
                      <>
                        선택한 번호 {targetNumbers.length}개와{' '}
                        <strong>
                          {A} ~ {B}회차
                        </strong>
                        의 과거 당첨 번호가 몇 개 일치하는지 분석한 결과입니다.
                      </>
                    )}
                  </Typography>

                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={headerCellSx}>구분</TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            출현 횟수
                          </TableCell>
                          <TableCell align="center" sx={{ ...headerCellSx, minWidth: 160 }}>
                            출현 비율
                          </TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            조회
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {[5, 4, 3, 2]
                          .filter((k) => k <= targetNumbers.length)
                          .map((k) => {
                            const count = matchCountStats[k as 2 | 3 | 4 | 5]?.length || 0;
                            const percentage =
                              totalRounds > 0 ? ((count / totalRounds) * 100).toFixed(2) : '0.00';
                            const maxMatchCount = Math.max(
                              1,
                              ...[2, 3, 4, 5]
                                .filter((kk) => kk <= targetNumbers.length)
                                .map((kk) => matchCountStats[kk as 2 | 3 | 4 | 5]?.length || 0)
                            );
                            const progressValue = (count / maxMatchCount) * 100;
                            return (
                              <TableRow
                                key={k}
                                hover
                                sx={{
                                  '&:nth-of-type(even)': {
                                    bgcolor: (theme) =>
                                      varAlpha(theme.vars.palette.grey['500Channel'], 0.03),
                                  },
                                }}
                              >
                                <TableCell>
                                  <Stack direction="row" spacing={1} alignItems="center">
                                    <Chip
                                      label={`${k}개`}
                                      size="small"
                                      color={k >= 4 ? 'warning' : 'default'}
                                      variant={k >= 4 ? 'filled' : 'outlined'}
                                      sx={{ fontWeight: 'bold', minWidth: 48 }}
                                    />
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                      번호 일치
                                    </Typography>
                                  </Stack>
                                </TableCell>
                                <TableCell align="center">
                                  <Typography
                                    variant="body2"
                                    sx={{ fontWeight: 'bold', color: 'primary.main' }}
                                  >
                                    {count}회
                                  </Typography>
                                </TableCell>
                                <TableCell align="center">
                                  <Stack spacing={0.5} alignItems="center">
                                    <Typography variant="caption">{percentage}%</Typography>
                                    <LinearProgress
                                      variant="determinate"
                                      value={progressValue}
                                      color={k >= 4 ? 'warning' : 'primary'}
                                      sx={{
                                        width: '100%',
                                        height: 6,
                                        borderRadius: 3,
                                        bgcolor: (theme) =>
                                          varAlpha(theme.vars.palette.primary.mainChannel, 0.08),
                                        '& .MuiLinearProgress-bar': { borderRadius: 3 },
                                      }}
                                    />
                                  </Stack>
                                </TableCell>
                                <TableCell align="center">
                                  <Tooltip title="일치 회차 목록 보기">
                                    <span>
                                      <Button
                                        size="small"
                                        variant="soft"
                                        onClick={() => handleOpenMatchModal(k)}
                                        disabled={count === 0}
                                        startIcon={<Iconify icon="solar:eye-bold" />}
                                      >
                                        보기
                                      </Button>
                                    </span>
                                  </Tooltip>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}

              {/* Tab 2: Individual Number Stats */}
              {currentTab === 2 && (
                <Box sx={{ p: 3 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    선택한 {targetNumbers.length}개 번호가 각각{' '}
                    <strong>
                      {A} ~ {B}회차
                    </strong>
                    의 과거 당첨 번호에 단독으로 출현한 횟수를 분석한 결과입니다.
                  </Typography>

                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={headerCellSx}>번호</TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            출현 횟수
                          </TableCell>
                          <TableCell align="center" sx={{ ...headerCellSx, minWidth: 160 }}>
                            출현 비율
                          </TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            조회
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {singleNumberStats.map((stat, idx) => {
                          const percentage =
                            totalRounds > 0
                              ? ((stat.count / totalRounds) * 100).toFixed(2)
                              : '0.00';
                          const progressValue = (stat.count / maxSingleCount) * 100;
                          return (
                            <TableRow
                              key={idx}
                              hover
                              sx={{
                                '&:nth-of-type(even)': {
                                  bgcolor: (theme) =>
                                    varAlpha(theme.vars.palette.grey['500Channel'], 0.03),
                                },
                              }}
                            >
                              <TableCell>
                                <LottoBall number={stat.number} size={32} />
                              </TableCell>
                              <TableCell align="center">
                                <Typography
                                  variant="body2"
                                  sx={{ fontWeight: 'bold', color: 'primary.main' }}
                                >
                                  {stat.count}회
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Stack spacing={0.5} alignItems="center">
                                  <Typography variant="caption">{percentage}%</Typography>
                                  <LinearProgress
                                    variant="determinate"
                                    value={progressValue}
                                    sx={{
                                      width: '100%',
                                      height: 6,
                                      borderRadius: 3,
                                      bgcolor: (theme) =>
                                        varAlpha(theme.vars.palette.primary.mainChannel, 0.08),
                                      '& .MuiLinearProgress-bar': { borderRadius: 3 },
                                    }}
                                  />
                                </Stack>
                              </TableCell>
                              <TableCell align="center">
                                <Tooltip title="출현 회차 목록 보기">
                                  <span>
                                    <Button
                                      size="small"
                                      variant="soft"
                                      onClick={() =>
                                        handleOpenComboModal(
                                          [stat.number],
                                          stat.count,
                                          stat.matchedRounds
                                        )
                                      }
                                      disabled={stat.count === 0}
                                      startIcon={<Iconify icon="solar:eye-bold" />}
                                    >
                                      보기
                                    </Button>
                                  </span>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}

              {/* Tab 3: Unappeared Companion Number Statistics */}
              {currentTab === 3 && (
                <Box sx={{ p: 3 }}>
                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ mb: 3 }}
                  >
                    <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '55%' }}>
                      선택한 번호 {targetNumbers.length}개와 나머지 번호 각각의 조합이 마지막으로
                      동반 출현한 이후 현재(<strong>{latestRound}회차</strong>)까지 미출현한 기간을
                      분석합니다.
                    </Typography>

                    <ToggleButtonGroup
                      value={companionSortOrder}
                      exclusive
                      onChange={(e, val) => val !== null && setCompanionSortOrder(val)}
                      size="small"
                      color="primary"
                    >
                      <ToggleButton value="desc" sx={{ px: 1.5, py: 0.3, fontSize: '0.75rem' }}>
                        <Iconify
                          icon="solar:sort-from-top-to-bottom-bold"
                          width={16}
                          sx={{ mr: 0.5 }}
                        />
                        미출현 긴 순
                      </ToggleButton>
                      <ToggleButton value="asc" sx={{ px: 1.5, py: 0.3, fontSize: '0.75rem' }}>
                        <Iconify
                          icon="solar:sort-from-bottom-to-top-bold"
                          width={16}
                          sx={{ mr: 0.5 }}
                        />
                        미출현 짧은 순
                      </ToggleButton>
                    </ToggleButtonGroup>
                  </Stack>

                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={headerCellSx}>짝번호</TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            최근 출현 회차
                          </TableCell>
                          <TableCell align="center" sx={{ ...headerCellSx, minWidth: 160 }}>
                            미출현 기간
                          </TableCell>
                          <TableCell align="center" sx={headerCellSx}>
                            조회
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {companionNumberStats.map((stat, idx) => {
                          const hasAppearance = stat.lastDrwNo > 0;
                          const progressValue = (stat.gap / maxCompanionGap) * 100;
                          return (
                            <TableRow
                              key={idx}
                              hover
                              sx={{
                                '&:nth-of-type(even)': {
                                  bgcolor: (theme) =>
                                    varAlpha(theme.vars.palette.grey['500Channel'], 0.03),
                                },
                              }}
                            >
                              <TableCell>
                                <Stack direction="row" spacing={1} alignItems="center">
                                  <LottoBall number={stat.number} size={32} />
                                  <Typography variant="caption" color="text.secondary">
                                    [ {targetNumbers.join(', ')}, {stat.number} ]
                                  </Typography>
                                </Stack>
                              </TableCell>
                              <TableCell align="center">
                                <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                  {hasAppearance ? `${stat.lastDrwNo}회` : '출현 기록 없음'}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Stack spacing={0.5} alignItems="center">
                                  <Typography
                                    variant="body2"
                                    sx={{ fontWeight: 'bold', color: 'error.main' }}
                                  >
                                    {stat.gap}회차 동안 미출현
                                  </Typography>
                                  <LinearProgress
                                    variant="determinate"
                                    value={progressValue}
                                    color="error"
                                    sx={{
                                      width: '100%',
                                      height: 6,
                                      borderRadius: 3,
                                      bgcolor: (theme) =>
                                        varAlpha(theme.vars.palette.error.mainChannel, 0.08),
                                      '& .MuiLinearProgress-bar': { borderRadius: 3 },
                                    }}
                                  />
                                </Stack>
                              </TableCell>
                              <TableCell align="center">
                                <Tooltip title="동반 출현 회차 목록 보기">
                                  <span>
                                    <Button
                                      size="small"
                                      variant="soft"
                                      onClick={() =>
                                        handleOpenComboModal(
                                          [...targetNumbers, stat.number],
                                          stat.matchedRounds.length,
                                          stat.matchedRounds
                                        )
                                      }
                                      disabled={stat.matchedRounds.length === 0}
                                      startIcon={<Iconify icon="solar:eye-bold" />}
                                    >
                                      보기
                                    </Button>
                                  </span>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Modal Dialog for displaying matched rounds */}
      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            pb: 1,
          }}
        >
          <Typography component="span" variant="h6">
            {modalTitle}
          </Typography>
          <IconButton onClick={() => setModalOpen(false)} size="small">
            <Iconify icon="mingcute:close-line" width={20} />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Stack spacing={0.5}>
              <Typography variant="caption" color="text.secondary">
                회차를 클릭하면 해당 회차 정보를 가져옵니다.
              </Typography>
              {modalRounds.length > 0 && (
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'error.main' }}>
                  현재 {latestRound}회차 동안 &ldquo;총 {unappearedRounds}회 미출현&rdquo;
                </Typography>
              )}
            </Stack>
            <ToggleButtonGroup
              value={modalSortOrder}
              exclusive
              onChange={(e, val) => val !== null && setModalSortOrder(val)}
              size="small"
              color="primary"
            >
              <ToggleButton value="desc" sx={{ px: 1.5, py: 0.3, fontSize: '0.75rem' }}>
                <Iconify icon="solar:sort-from-top-to-bottom-bold" width={16} sx={{ mr: 0.5 }} />
                최신순
              </ToggleButton>
              <ToggleButton value="asc" sx={{ px: 1.5, py: 0.3, fontSize: '0.75rem' }}>
                <Iconify icon="solar:sort-from-bottom-to-top-bold" width={16} sx={{ mr: 0.5 }} />
                과거순
              </ToggleButton>
            </ToggleButtonGroup>
          </Stack>

          <Box sx={{ maxHeight: 480, overflowY: 'auto' }}>
            <Grid container spacing={1.5}>
              {sortedModalRounds.map((r, idx) => {
                const gapInfo = getRoundGapInfo(r.drwNo, highlightNumbers);
                return (
                  <Grid size={{ xs: 12, sm: 6 }} key={idx}>
                    <Card
                      onClick={() => handleSelectRoundFromModal(r.drwNo)}
                      sx={{
                        p: 1.5,
                        cursor: 'pointer',
                        border: '1px solid',
                        borderColor: 'divider',
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          borderColor: 'primary.main',
                          bgcolor: (theme) =>
                            varAlpha(theme.vars.palette.primary.mainChannel, 0.04),
                          transform: 'translateY(-2px)',
                          boxShadow: (theme) => theme.shadows[4],
                        },
                      }}
                    >
                      <Stack spacing={1}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                          <Stack direction="row" spacing={0.8} alignItems="center">
                            <Typography
                              variant="subtitle2"
                              sx={{ fontWeight: 'bold', color: 'text.primary' }}
                            >
                              {r.drwNo}회
                            </Typography>
                            <Chip
                              label={gapInfo.isFirst ? '첫 출현' : `+${gapInfo.gap}회 만에`}
                              size="small"
                              color={gapInfo.isFirst ? 'info' : 'success'}
                              variant="soft"
                              sx={{ height: 20, fontSize: '0.675rem', fontWeight: 'bold' }}
                            />
                          </Stack>
                          <Typography variant="caption" color="text.disabled">
                            {r.drwNoDate}
                          </Typography>
                        </Stack>

                        <Stack direction="row" spacing={0.6} alignItems="center">
                          {r.numbers.map((num: number) => {
                            const isHighlighted = highlightNumbers.includes(num);
                            return (
                              <LottoBall
                                key={num}
                                number={num}
                                size={26}
                                highlighted={isHighlighted}
                              />
                            );
                          })}
                          <Typography variant="caption" sx={{ mx: 0.2, color: 'text.secondary' }}>
                            +
                          </Typography>
                          <LottoBall
                            number={r.bonus}
                            size={26}
                            highlighted={includeBonus && highlightNumbers.includes(r.bonus)}
                          />
                        </Stack>
                      </Stack>
                    </Card>
                  </Grid>
                );
              })}
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalOpen(false)} variant="contained">
            닫기
          </Button>
        </DialogActions>
      </Dialog>
    </DashboardContent>
  );
}
