'use client';

import { useMemo, useState } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Table from '@mui/material/Table';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import Switch from '@mui/material/Switch';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import TableHead from '@mui/material/TableHead';
import TableCell from '@mui/material/TableCell';
import Typography from '@mui/material/Typography';
import DialogTitle from '@mui/material/DialogTitle';
import ToggleButton from '@mui/material/ToggleButton';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TableContainer from '@mui/material/TableContainer';
import TableSortLabel from '@mui/material/TableSortLabel';
import TablePagination from '@mui/material/TablePagination';
import FormControlLabel from '@mui/material/FormControlLabel';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

import { getBallColor } from 'src/api/lottolibrary';

import { LottoPaper } from 'src/components/lotto/lotto-paper';

// ----------------------------------------------------------------------

type Props = {
  rounds: any[];
  includeBonus: boolean;
};

type Order = 'asc' | 'desc';

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

export function AnalyticsChemistry({ rounds, includeBonus }: Props) {
  const [tupleSize, setTupleSize] = useState<number>(2);
  const [orderBy, setOrderBy] = useState<string>('count');
  const [order, setOrder] = useState<Order>('desc');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [openSearch, setOpenSearch] = useState(false);
  const [searchNumbers, setSearchNumbers] = useState<number[]>([]);
  const [matchAll, setMatchAll] = useState(false);

  const handleSearchToggle = (num: number) => {
    setSearchNumbers((prev) => {
      if (prev.includes(num)) {
        return prev.filter((n) => n !== num);
      }
      if (prev.length >= tupleSize - 1) {
        // Cannot select more than tupleSize - 1 ideally because if we select tupleSize,
        // we are searching for that exact combination which exists or not.
        // But let's allow up to tupleSize.
        // If user selects 3 numbers for tuple size 2, result is always empty.
        // User asked: "select numbers included".
        // Let's cap at 6 or just let them pick.
        return [...prev, num];
      }
      return [...prev, num];
    });
  };

  const handleSearchConfirm = () => {
    setOpenSearch(false);
  };

  const handleSearchReset = () => {
    setSearchNumbers([]);
  };

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const chemistryStats = useMemo(() => {
    const statsMap = new Map<string, { count: number; latestRound: number; latestDate: string }>();

    rounds.forEach((r) => {
      const numbers = [...r.numbers];
      if (includeBonus && r.bonus) {
        numbers.push(r.bonus);
      }
      // Sort numbers to ensure consistency (e.g., "1,2" is same as "2,1")
      numbers.sort((a: number, b: number) => a - b);

      const combs = getCombinations(numbers, tupleSize);

      combs.forEach((comb) => {
        const key = comb.join(',');
        const existing = statsMap.get(key);

        if (existing) {
          statsMap.set(key, {
            count: existing.count + 1,
            latestRound: Math.max(existing.latestRound, r.drwNo),
            latestDate: r.drwNo > existing.latestRound ? r.drwNoDate : existing.latestDate,
          });
        } else {
          statsMap.set(key, {
            count: 1,
            latestRound: r.drwNo,
            latestDate: r.drwNoDate,
          });
        }
      });
    });

    const stats = Array.from(statsMap.entries()).map(([key, value]) => {
      const numbers = key.split(',').map(Number);
      const totalRounds = rounds.length;
      return {
        numbers,
        count: value.count,
        latestRound: value.latestRound,
        latestDate: value.latestDate,
        probability: totalRounds > 0 ? (value.count / totalRounds) * 100 : 0,
      };
    });

    // Filter by search numbers
    if (searchNumbers.length > 0) {
      return stats.filter((stat) =>
        matchAll
          ? searchNumbers.every((searchNum) => stat.numbers.includes(searchNum))
          : stat.numbers.some((num) => searchNumbers.includes(num))
      );
    }

    return stats;
  }, [rounds, includeBonus, tupleSize, searchNumbers, matchAll]);

  const sortedData = useMemo(
    () =>
      [...chemistryStats].sort((a, b) => {
        const aValue = a[orderBy as keyof typeof a];
        const bValue = b[orderBy as keyof typeof b];

        // Handle specific types if necessary, though simpler here
        if (orderBy === 'numbers') {
          // Sort by first number of the tuple for 'numbers' sort
          const aNum = a.numbers[0];
          const bNum = b.numbers[0];
          if (order === 'asc') return aNum - bNum;
          return bNum - aNum;
        }

        if (aValue !== bValue) {
          if (order === 'asc') return aValue > bValue ? 1 : -1;
          return aValue < bValue ? 1 : -1; // Default desc
        }

        return 0;
      }),
    [chemistryStats, orderBy, order]
  );

  // Pagination logic
  const paginatedData = sortedData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <Card sx={{ borderRadius: 2, overflow: 'hidden' }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        justifyContent="space-between"
        spacing={1.5}
        sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}
      >
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Typography variant="subtitle2" sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>
            조합 번호 수:
          </Typography>
          <ToggleButtonGroup
            value={tupleSize}
            exclusive
            onChange={(e, nextValue) => {
              if (nextValue !== null) {
                setTupleSize(nextValue);
              }
            }}
            size="small"
            color="primary"
          >
            <ToggleButton value={2} sx={{ fontWeight: 700, px: 1.5, py: 0.25, fontSize: '0.8rem' }}>
              2개
            </ToggleButton>
            <ToggleButton value={3} sx={{ fontWeight: 700, px: 1.5, py: 0.25, fontSize: '0.8rem' }}>
              3개
            </ToggleButton>
            <ToggleButton value={4} sx={{ fontWeight: 700, px: 1.5, py: 0.25, fontSize: '0.8rem' }}>
              4개
            </ToggleButton>
            <ToggleButton value={5} sx={{ fontWeight: 700, px: 1.5, py: 0.25, fontSize: '0.8rem' }}>
              5개
            </ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        <Button variant="outlined" size="small" onClick={() => setOpenSearch(true)}>
          {searchNumbers.length > 0
            ? `선택 번호: ${[...searchNumbers].sort((a, b) => a - b).join(', ')}`
            : '검색 번호 선택'}
        </Button>
      </Stack>

      <Dialog open={openSearch} onClose={() => setOpenSearch(false)} maxWidth="sm" fullWidth>
        <DialogTitle>검색 번호 선택</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
            <LottoPaper selectedNumbers={searchNumbers} onToggle={handleSearchToggle} />
          </Box>

          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Switch checked={matchAll} onChange={(e) => setMatchAll(e.target.checked)} />
              }
              label="선택 번호 모두 포함"
            />
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {matchAll
                ? '선택한 번호가 모두 포함된 조합만 검색됩니다.'
                : '선택한 번호가 하나라도 포함된 조합이 검색됩니다.'}
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleSearchReset} color="error">
            초기화
          </Button>
          <Button onClick={handleSearchConfirm} variant="contained">
            확인
          </Button>
        </DialogActions>
      </Dialog>

      <TableContainer>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  minWidth: { xs: 100, sm: 150 },
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'numbers'}
                  direction={orderBy === 'numbers' ? order : 'asc'}
                  onClick={() => handleRequestSort('numbers')}
                >
                  번호 조합
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  minWidth: { xs: 80, sm: 120 },
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'count'}
                  direction={orderBy === 'count' ? order : 'asc'}
                  onClick={() => handleRequestSort('count')}
                >
                  출현 빈도수
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  minWidth: { xs: 80, sm: 120 },
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'latestRound'}
                  direction={orderBy === 'latestRound' ? order : 'asc'}
                  onClick={() => handleRequestSort('latestRound')}
                >
                  최근 회차
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  minWidth: { xs: 100, sm: 150 },
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'latestDate'}
                  direction={orderBy === 'latestDate' ? order : 'asc'}
                  onClick={() => handleRequestSort('latestDate')}
                >
                  최근 출현 날짜
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  minWidth: { xs: 80, sm: 150 },
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'probability'}
                  direction={orderBy === 'probability' ? order : 'asc'}
                  onClick={() => handleRequestSort('probability')}
                >
                  출현 확률
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedData.map((row, index) => (
              <TableRow key={index} hover>
                <TableCell sx={{ px: { xs: 1, sm: 2 }, py: 1 }}>
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    {row.numbers.map((num) => (
                      <Box
                        key={num}
                        sx={{
                          width: { xs: 28, sm: 32 },
                          height: { xs: 28, sm: 32 },
                          aspectRatio: '1 / 1',
                          flexShrink: 0,
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          bgcolor: getBallColor(num),
                          color: '#fff',
                          fontWeight: 700,
                          fontSize: { xs: '0.75rem', sm: '0.8rem' },
                          boxShadow: (theme) =>
                            `inset 0 0 8px rgba(255,255,255,0.3), ${theme.shadows[2]}`,
                          border: searchNumbers.includes(num) ? '2px solid red' : 'none',
                          boxSizing: 'border-box',
                        }}
                      >
                        {num}
                      </Box>
                    ))}
                  </Stack>
                </TableCell>
                <TableCell sx={{ px: { xs: 1, sm: 2 }, py: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 700,
                      color: 'primary.main',
                      fontSize: { xs: '0.8rem', sm: '0.875rem' },
                    }}
                  >
                    {row.count}회
                  </Typography>
                </TableCell>
                <TableCell sx={{ px: { xs: 1, sm: 2 }, py: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{ fontWeight: 600, fontSize: { xs: '0.8rem', sm: '0.875rem' } }}
                  >
                    {row.latestRound}회
                  </Typography>
                </TableCell>
                <TableCell sx={{ px: { xs: 1, sm: 2 }, py: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      color: 'text.secondary',
                      fontSize: { xs: '0.75rem', sm: '0.875rem' },
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {row.latestDate.substring(0, 10)}
                  </Typography>
                </TableCell>
                <TableCell sx={{ px: { xs: 1, sm: 2 }, py: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 600, fontSize: { xs: '0.8rem', sm: '0.875rem' } }}
                    >
                      {row.probability.toFixed(2)}%
                    </Typography>
                    <Box
                      sx={{
                        height: 6,
                        width: 60,
                        bgcolor: 'divider',
                        borderRadius: 3,
                        overflow: 'hidden',
                        display: { xs: 'none', sm: 'block' },
                      }}
                    >
                      <Box
                        sx={{
                          height: '100%',
                          width: `${Math.min(row.probability * 2, 100)}%`, // Scale logic might need adjustment but 100% is fine cap
                          bgcolor: 'success.main', // Different color for variety? Or stay primary.
                          opacity: 0.6,
                        }}
                      />
                    </Box>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
            {paginatedData.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} sx={{ textAlign: 'center', py: 4 }}>
                  데이터가 없습니다.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        count={sortedData.length}
        page={page}
        onPageChange={(e, newPage) => setPage(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => {
          setRowsPerPage(parseInt(e.target.value, 10));
          setPage(0);
        }}
        rowsPerPageOptions={[10, 25, 50]}
      />
    </Card>
  );
}
