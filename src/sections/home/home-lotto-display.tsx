import { useState } from 'react';
import { m } from 'framer-motion';

import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';

import { paths } from 'src/routes/paths';
import { useRouter } from 'src/routes/hooks';

import * as LottoLibrary from 'src/api/lottolibrary';

import { Iconify } from 'src/components/iconify';
import { varFade, varContainer, MotionViewport } from 'src/components/animate';

// ----------------------------------------------------------------------

export function HomeLottoDisplay() {
  const router = useRouter();

  const [currentIndex, setCurrentIndex] = useState(LottoLibrary.getLength() - 1);
  const [isEditing, setIsEditing] = useState(false);
  const [tempRound, setTempRound] = useState('');

  const currentLotto = LottoLibrary.getLottoByIndex(currentIndex);

  if (!currentLotto) {
    return null;
  }

  const { numbers, bonus, drwNo, drwNoDate } = currentLotto;

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  };

  const handleNext = () => {
    if (currentIndex < LottoLibrary.getLength() - 1) {
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handleRoundClick = () => {
    setTempRound(String(drwNo));
    setIsEditing(true);
  };

  const handleRoundChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTempRound(event.target.value);
  };

  const handleRoundSubmit = () => {
    const newRound = parseInt(tempRound, 10);
    const maxRound = LottoLibrary.getLength();

    if (!isNaN(newRound) && newRound >= 1 && newRound <= maxRound) {
      setCurrentIndex(newRound - 1);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleRoundSubmit();
    } else if (event.key === 'Escape') {
      setIsEditing(false);
    }
  };

  return (
    <Container
      component={MotionViewport}
      sx={{ py: 10, px: { xs: 3, sm: 4, md: 0 }, textAlign: 'center' }}
    >
      <m.div variants={varFade('inUp')}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="center"
          spacing={{ xs: 0.5, md: 2 }}
          sx={{ mb: 5 }}
        >
          <IconButton onClick={handlePrev} disabled={currentIndex === 0}>
            <Iconify icon="eva:arrow-ios-back-fill" width={28} />
          </IconButton>

          <Stack direction="column" spacing={0.5} justifyContent="center" alignItems="center">
            <Box
              sx={{
                minHeight: { xs: '2rem', sm: '2.5rem', md: '3.5rem' },
                display: 'flex',
                alignItems: 'center',
              }}
            >
              {isEditing ? (
                <TextField
                  variant="standard"
                  autoFocus
                  value={tempRound}
                  onChange={handleRoundChange}
                  onBlur={handleRoundSubmit}
                  onKeyDown={handleKeyDown}
                  sx={{
                    width: '80px',
                    '& .MuiInputBase-root': {
                      lineHeight: 1.5,
                    },
                    '& .MuiInputBase-input': {
                      fontSize: { xs: '1.2rem', sm: '1.5rem', md: '2rem' },
                      fontWeight: 'bold',
                      color: '#007aff',
                      textAlign: 'center',
                      p: 0,
                      pb: '2px',
                      caretColor: 'rgba(0, 122, 255, 0.4)',
                    },
                    '& .MuiInput-underline:before': {
                      borderBottomColor: 'rgba(0, 122, 255, 0.2)',
                    },
                    '& .MuiInput-underline:hover:not(.Mui-disabled):before': {
                      borderBottomColor: 'rgba(0, 122, 255, 0.3)',
                    },
                    '& .MuiInput-underline:after': {
                      borderBottomColor: 'rgba(0, 122, 255, 0.4)',
                    },
                  }}
                />
              ) : (
                <Typography
                  variant="h3"
                  onClick={handleRoundClick}
                  sx={{
                    color: '#007aff',
                    fontWeight: 'bold',
                    fontSize: { xs: '1.2rem', sm: '1.5rem', md: '2rem' },
                    whiteSpace: 'nowrap',
                    cursor: 'pointer',
                    '&:hover': { opacity: 0.8 },
                  }}
                >
                  {drwNo}회
                </Typography>
              )}
            </Box>
            <Typography
              variant="body1"
              sx={{
                color: 'text.secondary',
                fontSize: { xs: '0.75rem', sm: '0.875rem', md: '1rem' },
                whiteSpace: 'nowrap',
              }}
            >
              {drwNoDate}
            </Typography>
          </Stack>

          <IconButton onClick={handleNext} disabled={currentIndex === LottoLibrary.getLength() - 1}>
            <Iconify icon="eva:arrow-ios-forward-fill" width={28} />
          </IconButton>
        </Stack>
      </m.div>

      <Stack
        key={drwNo}
        component={m.div}
        initial="initial"
        animate="animate"
        variants={{
          initial: {},
          ...varContainer(),
        }}
        direction="row"
        spacing={{ xs: 0.5, sm: 1, md: 3 }}
        justifyContent="center"
        alignItems="center"
        flexWrap="nowrap"
      >
        {numbers.map((num, index) => (
          <m.div key={num} variants={varFade('inUp')} custom={index}>
            <LottoLibrary.Ball
              sx={{
                background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent 60%), ${LottoLibrary.getBallColor(
                  num
                )}`,
              }}
            >
              {num}
            </LottoLibrary.Ball>
          </m.div>
        ))}

        <m.div variants={varFade('inUp')} custom={6}>
          <Typography
            variant="h3"
            sx={{
              mx: { xs: 0.5, sm: 1, md: 2 },
              fontSize: { xs: '1.2rem', sm: '1.5rem', md: '2rem' },
              color: 'text.secondary',
            }}
          >
            +
          </Typography>
        </m.div>

        <m.div variants={varFade('inUp')} custom={7}>
          <LottoLibrary.Ball
            sx={{
              background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent 60%), ${LottoLibrary.getBallColor(
                bonus
              )}`,
            }}
          >
            {bonus}
          </LottoLibrary.Ball>
        </m.div>
      </Stack>

      <m.div variants={varFade('inUp')}>
        <Button
          size="large"
          variant="contained"
          onClick={() => router.push(paths.dashboard.general.pattern)}
          sx={{ mt: 5 }}
        >
          패턴 분석하러 가기
        </Button>
      </m.div>
    </Container>
  );
}
