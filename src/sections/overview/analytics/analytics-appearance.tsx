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

// ----------------------------------------------------------------------

type Props = {
  rounds: any[];
  includeBonus: boolean;
};

type Order = 'asc' | 'desc';

type AppearanceStat = {
  number: number;
  count: number;
  probability: number;
  latestRound: number;
  latestDate: string;
};

export function AnalyticsAppearance({ rounds, includeBonus }: Props) {
  const [orderBy, setOrderBy] = useState<string>('count');
  const [order, setOrder] = useState<Order>('desc');

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const appearanceStats = useMemo(() => {
    const stats: AppearanceStat[] = Array.from({ length: 45 }, (_, i) => ({
      number: i + 1,
      count: 0,
      probability: 0,
      latestRound: 0,
      latestDate: '-',
    }));

    // rounds를 회차 내림차순으로 정렬 (최신 회차가 먼저 오도록)
    const sortedRounds = [...rounds].sort((a, b) => b.drwNo - a.drwNo);

    sortedRounds.forEach((r) => {
      r.numbers.forEach((n: number) => {
        if (n >= 1 && n <= 45) {
          stats[n - 1].count += 1;
          // 최신 출현 정보 업데이트 (첫 번째로 발견된 것이 가장 최신)
          if (stats[n - 1].latestRound === 0) {
            stats[n - 1].latestRound = r.drwNo;
            stats[n - 1].latestDate = r.drwNoDate;
          }
        }
      });
      if (includeBonus) {
        if (r.bonus >= 1 && r.bonus <= 45) {
          stats[r.bonus - 1].count += 1;
          if (stats[r.bonus - 1].latestRound === 0) {
            stats[r.bonus - 1].latestRound = r.drwNo;
            stats[r.bonus - 1].latestDate = r.drwNoDate;
          }
        }
      }
    });

    const totalRounds = rounds.length;
    stats.forEach((s) => {
      s.probability = totalRounds > 0 ? (s.count / totalRounds) * 100 : 0;
    });

    return stats;
  }, [rounds, includeBonus]);

  const sortedData = useMemo(
    () =>
      [...appearanceStats].sort((a, b) => {
        let aValue: number | string = a[orderBy as keyof AppearanceStat];
        let bValue: number | string = b[orderBy as keyof AppearanceStat];

        // 날짜 정렬 처리
        if (orderBy === 'latestDate') {
          aValue = a.latestRound; // 날짜 대신 회차로 정렬 (더 정확함)
          bValue = b.latestRound;
        }

        if (aValue !== bValue) {
          if (order === 'asc') return aValue > bValue ? 1 : -1;
          return aValue < bValue ? 1 : -1;
        }

        // If values are equal (e.g., same count), always sort by number ascending
        return a.number - b.number;
      }),
    [appearanceStats, orderBy, order]
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
                  출현 빈도수
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
                    {row.latestRound > 0 ? `${row.latestRound}회` : '-'}
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
                    {formatDate(row.latestDate)}
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
                          width: `${Math.min(row.probability * 2, 100)}%`,
                          bgcolor: 'primary.main',
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
