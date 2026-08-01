'use client';

import { useMemo, useState } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Table from '@mui/material/Table';
import Stack from '@mui/material/Stack';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import TableHead from '@mui/material/TableHead';
import TableCell from '@mui/material/TableCell';
import Typography from '@mui/material/Typography';
import TableContainer from '@mui/material/TableContainer';
import TableSortLabel from '@mui/material/TableSortLabel';

import { getBallColor } from 'src/api/lottolibrary';

import { Label } from 'src/components/label';

// ----------------------------------------------------------------------

type Props = {
  allLotto: any[];
  startRound: number;
  endRound: number;
  includeBonus: boolean;
};

type Order = 'asc' | 'desc';

type CarryOverStat = {
  number: number;
  count: number;
  probability: number;
  appearanceCount: number;
  latestCarryRound: number;
  latestCarryDate: string;
};

export function AnalyticsCarryOver({ allLotto, startRound, endRound, includeBonus }: Props) {
  const [orderBy, setOrderBy] = useState<string>('count');
  const [order, setOrder] = useState<Order>('desc');

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const carryOverStats = useMemo(() => {
    const stats: CarryOverStat[] = Array.from({ length: 45 }, (_, i) => ({
      number: i + 1,
      count: 0,
      probability: 0,
      appearanceCount: 0,
      latestCarryRound: 0,
      latestCarryDate: '-',
    }));

    // First calculate appearance counts for probability denominator
    allLotto.forEach((r) => {
      if (r.drwNo >= startRound && r.drwNo <= endRound) {
        r.numbers.forEach((n: number) => {
          if (n >= 1 && n <= 45) stats[n - 1].appearanceCount += 1;
        });
        if (includeBonus) {
          if (r.bonus >= 1 && r.bonus <= 45) stats[r.bonus - 1].appearanceCount += 1;
        }
      }
    });

    // Calculate carry-over frequency (내림차순으로 처리하여 최신 이월 먼저 찾기)
    const sortedLotto = [...allLotto].sort((a, b) => b.drwNo - a.drwNo);

    sortedLotto.forEach((r, index) => {
      if (r.drwNo >= startRound + 1 && r.drwNo <= endRound) {
        // 이전 회차 찾기 (drwNo - 1)
        const prevRound = allLotto.find((x) => x.drwNo === r.drwNo - 1);
        if (!prevRound) return;

        const currentNumbers = [...r.numbers];
        if (includeBonus) currentNumbers.push(r.bonus);

        const prevNumbers = [...prevRound.numbers];
        if (includeBonus) prevNumbers.push(prevRound.bonus);

        currentNumbers.forEach((num) => {
          if (num >= 1 && num <= 45 && prevNumbers.includes(num)) {
            stats[num - 1].count += 1;
            // 최신 이월 정보 업데이트 (첫 번째로 발견된 것이 가장 최신)
            if (stats[num - 1].latestCarryRound === 0) {
              stats[num - 1].latestCarryRound = r.drwNo;
              stats[num - 1].latestCarryDate = r.drwNoDate;
            }
          }
        });
      }
    });

    stats.forEach((s) => {
      s.probability = s.appearanceCount > 0 ? (s.count / s.appearanceCount) * 100 : 0;
    });

    return stats;
  }, [allLotto, startRound, endRound, includeBonus]);

  const latestRoundNumbers = useMemo(() => {
    const latest = allLotto.find((r) => r.drwNo === endRound);
    if (!latest) return [];
    const nums = [...latest.numbers];
    if (includeBonus) nums.push(latest.bonus);
    return nums;
  }, [allLotto, endRound, includeBonus]);

  const sortedData = useMemo(
    () =>
      [...carryOverStats].sort((a, b) => {
        let aValue: number | string = a[orderBy as keyof CarryOverStat];
        let bValue: number | string = b[orderBy as keyof CarryOverStat];

        // 날짜 정렬 처리
        if (orderBy === 'latestCarryDate') {
          aValue = a.latestCarryRound;
          bValue = b.latestCarryRound;
        }

        if (aValue !== bValue) {
          if (order === 'asc') return aValue > bValue ? 1 : -1;
          return aValue < bValue ? 1 : -1;
        }

        // If values are equal (e.g., same count), always sort by number ascending
        return a.number - b.number;
      }),
    [carryOverStats, orderBy, order]
  );

  // 날짜 포맷팅 함수
  const formatDate = (dateStr: string) => {
    if (dateStr === '-') return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' });
  };

  return (
    <Card sx={{ borderRadius: 2, overflow: 'hidden' }}>
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
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'number'}
                  direction={orderBy === 'number' ? order : 'asc'}
                  onClick={() => handleRequestSort('number')}
                >
                  번호
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'count'}
                  direction={orderBy === 'count' ? order : 'asc'}
                  onClick={() => handleRequestSort('count')}
                >
                  이월 빈도수
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'latestCarryRound'}
                  direction={orderBy === 'latestCarryRound' ? order : 'asc'}
                  onClick={() => handleRequestSort('latestCarryRound')}
                >
                  최근 이월 회차
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'latestCarryDate'}
                  direction={orderBy === 'latestCarryDate' ? order : 'asc'}
                  onClick={() => handleRequestSort('latestCarryDate')}
                >
                  최근 이월 날짜
                </TableSortLabel>
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  bgcolor: 'background.neutral',
                  px: { xs: 1, sm: 2 },
                  py: 1,
                  whiteSpace: 'nowrap',
                }}
              >
                <TableSortLabel
                  active={orderBy === 'probability'}
                  direction={orderBy === 'probability' ? order : 'asc'}
                  onClick={() => handleRequestSort('probability')}
                >
                  이월 확률
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedData.map((row) => (
              <TableRow key={row.number} hover>
                <TableCell sx={{ px: { xs: 1, sm: 2 }, py: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Box
                      sx={{
                        width: { xs: 32, sm: 36 },
                        height: { xs: 32, sm: 36 },
                        aspectRatio: '1 / 1',
                        flexShrink: 0,
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: getBallColor(row.number),
                        color: '#fff',
                        fontWeight: 700,
                        fontSize: { xs: '0.85rem', sm: '0.9rem' },
                        boxShadow: (theme) =>
                          `inset 0 0 8px rgba(255,255,255,0.3), ${theme.shadows[2]}`,
                      }}
                    >
                      {row.number}
                    </Box>
                    {latestRoundNumbers.includes(row.number) && (
                      <Label
                        color="info"
                        variant="soft"
                        sx={{ ml: 0.5, fontSize: '0.7rem', px: 0.5 }}
                      >
                        최신
                      </Label>
                    )}
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
                    {row.latestCarryRound > 0 ? `${row.latestCarryRound}회` : '-'}
                  </Typography>
                </TableCell>
                <TableCell sx={{ px: { xs: 1, sm: 2 }, py: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: 'text.secondary',
                      fontSize: { xs: '0.75rem', sm: '0.875rem' },
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {formatDate(row.latestCarryDate)}
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
                          width: `${Math.min(row.probability * 3, 100)}%`,
                          bgcolor: 'success.main',
                          opacity: 0.6,
                        }}
                      />
                    </Box>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Card>
  );
}
