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
  allLotto: any[];
  endRound: number;
  includeBonus: boolean;
};

type Order = 'asc' | 'desc';

type MissingStat = {
  number: number;
  missingCount: number;
  latestRound: number;
  latestDate: string;
};

export function AnalyticsMissing({ allLotto, endRound, includeBonus }: Props) {
  const [orderBy, setOrderBy] = useState<string>('missingCount');
  const [order, setOrder] = useState<Order>('desc');

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const missingStats = useMemo(() => {
    const stats: MissingStat[] = Array.from({ length: 45 }, (_, i) => ({
      number: i + 1,
      missingCount: 0,
      latestRound: 0,
      latestDate: '-',
    }));

    // endRound 이전의 데이터만 고려
    // 회차 내림차순으로 정렬 (최신 회차가 먼저 오도록)
    const validRounds = allLotto
      .filter((r) => r.drwNo <= endRound)
      .sort((a, b) => b.drwNo - a.drwNo);

    // 각 번호별로 가장 최근 출현 회차 찾기
    for (let i = 0; i < stats.length; i++) {
      const num = stats[i].number;
      const found = validRounds.find((r) => {
        const isMainNumber = r.numbers.includes(num);
        const isBonusNumber = includeBonus && r.bonus === num;
        return isMainNumber || isBonusNumber;
      });

      if (found) {
        stats[i].latestRound = found.drwNo;
        stats[i].latestDate = found.drwNoDate;
        stats[i].missingCount = endRound - found.drwNo;
      } else {
        // 한 번도 출현하지 않은 경우 (데이터 상 불가능하지만 예외 처리)
        stats[i].latestRound = 0;
        stats[i].latestDate = '-';
        stats[i].missingCount = endRound;
      }
    }

    return stats;
  }, [allLotto, endRound, includeBonus]);

  const sortedData = useMemo(
    () =>
      [...missingStats].sort((a, b) => {
        const aValue: number | string = a[orderBy as keyof MissingStat];
        const bValue: number | string = b[orderBy as keyof MissingStat];

        if (aValue !== bValue) {
          if (order === 'asc') return aValue > bValue ? 1 : -1;
          return aValue < bValue ? 1 : -1;
        }

        // 값이 같을 경우 번호 오름차순
        return a.number - b.number;
      }),
    [missingStats, orderBy, order]
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
                  active={orderBy === 'missingCount'}
                  direction={orderBy === 'missingCount' ? order : 'asc'}
                  onClick={() => handleRequestSort('missingCount')}
                >
                  미출현 횟수
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
                      color: 'error.main',
                      fontSize: { xs: '0.8rem', sm: '0.875rem' },
                    }}
                  >
                    {row.missingCount}회
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
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Card>
  );
}
