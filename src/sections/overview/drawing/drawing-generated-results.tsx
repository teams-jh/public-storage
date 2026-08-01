import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';

import * as LottoLibrary from 'src/api/lottolibrary';

import { Iconify } from 'src/components/iconify';

type Props = {
  results: number[][];
  includedNumbers: number[];
  onShare: () => void;
};

export function DrawingGeneratedResults({ results, includedNumbers, onShare }: Props) {
  if (results.length === 0) return null;

  return (
    <Box sx={{ py: 1, textAlign: 'center', width: '100%' }}>
      <Stack direction="row" alignItems="center" justifyContent="center" spacing={1} sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
          추천 로또 번호
        </Typography>
        <Tooltip title="공유하기">
          <IconButton onClick={onShare} color="primary" size="small">
            <Iconify icon="mdi:share-variant" width={22} />
          </IconButton>
        </Tooltip>
      </Stack>

      <Stack spacing={{ xs: 2.5, sm: 3.5 }} sx={{ width: '100%', alignItems: 'center' }}>
        {results.map((result, setIndex) => (
          <Stack
            key={setIndex}
            direction="row"
            spacing={0}
            justifyContent="center"
            alignItems="center"
            sx={{ width: '100%' }}
          >
            <Typography
              variant="subtitle1"
              sx={{
                minWidth: { xs: 24, sm: 32 },
                textAlign: 'center',
                fontWeight: 800,
                color: 'primary.main',
                fontSize: { xs: '0.95rem', sm: '1.15rem' },
                mr: { xs: 0.75, sm: 1.5 },
              }}
            >
              {String.fromCharCode(65 + setIndex)}
            </Typography>

            <Stack
              direction="row"
              spacing={{ xs: 0.5, sm: 1 }}
              justifyContent="center"
              alignItems="center"
            >
              {result.map((num) => {
                const ballColor = LottoLibrary.getBallColor(num);
                const isIncluded = includedNumbers.includes(num);

                return (
                  <LottoLibrary.Ball
                    key={num}
                    sx={{
                      width: { xs: 42, sm: 54, md: 62 },
                      height: { xs: 42, sm: 54, md: 62 },
                      fontSize: { xs: '1rem', sm: '1.2rem', md: '1.35rem' },
                      fontWeight: 'bold',
                      flexShrink: 0,
                      background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent 60%), ${ballColor}`,
                      boxShadow: isIncluded
                        ? {
                            xs: `0 0 0 2px white, 0 0 0 3.5px ${ballColor}, 0 3px 6px rgba(0,0,0,0.35)`,
                            md: `0 0 0 3px white, 0 0 0 5.5px ${ballColor}, 0 4px 10px rgba(0,0,0,0.35)`,
                          }
                        : '0 4px 10px rgba(0,0,0,0.2)',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {num}
                  </LottoLibrary.Ball>
                );
              })}
            </Stack>
          </Stack>
        ))}
      </Stack>

      <Typography variant="caption" sx={{ mt: 3, display: 'block', color: 'text.secondary' }}>
        * 테두리가 있는 공은 사용자가 지정한 포함수입니다.
      </Typography>
    </Box>
  );
}
