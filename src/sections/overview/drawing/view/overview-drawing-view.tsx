'use client';

import { useState, useCallback } from 'react';

import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';

import * as LottoLibrary from 'src/api/lottolibrary';
import { DashboardContent } from 'src/layouts/dashboard';
import { Iconify } from 'src/components/iconify';

import { LottoPaper } from 'src/components/lotto/lotto-paper';

import { useLottoGenerator } from '../use-lotto-generator';
import { DrawingGeneratedResults } from '../drawing-generated-results';

// ----------------------------------------------------------------------

export function OverviewDrawingView() {
  const {
    includedNumbers,
    excludedNumbers,
    generatedResults,
    setIncludedNumbers,
    setExcludedNumbers,
    handleToggleIncluded,
    handleToggleExcluded,
    handleGenerate,
    handleReset,
    handleAutoSelect,
    handleShare,
  } = useLottoGenerator();

  const [openResultModal, setOpenResultModal] = useState(false);

  const latestDraw = LottoLibrary.getLatestLottoNumber();

  const handleGenerateAndOpenModal = useCallback(() => {
    const success = handleGenerate();
    if (success) {
      setOpenResultModal(true);
    }
  }, [handleGenerate]);

  return (
    <DashboardContent maxWidth="xl">
      {/* 우측 상단 고정 초기화 아이콘 버튼 */}
      <Box
        sx={{
          position: 'fixed',
          top: { xs: 76, md: 96 },
          right: { xs: 16, md: 28 },
          zIndex: 1100,
        }}
      >
        <Tooltip title="초기화" arrow>
          <IconButton
            onClick={handleReset}
            sx={{
              p: 1.25,
              borderRadius: '50%',
              bgcolor: (theme) =>
                theme.palette.mode === 'light'
                  ? 'rgba(255, 255, 255, 0.85)'
                  : 'rgba(22, 28, 36, 0.85)',
              boxShadow: (theme) => theme.customShadows.z16,
              border: (theme) => `1px solid ${theme.palette.divider}`,
              backdropFilter: 'blur(8px)',
              '&:hover': {
                bgcolor: (theme) =>
                  theme.palette.mode === 'light' ? 'rgba(255, 255, 255, 1)' : 'rgba(22, 28, 36, 1)',
              },
            }}
          >
            <Iconify icon="solar:restart-bold" width={22} />
          </IconButton>
        </Tooltip>
      </Box>

      {latestDraw && (
        <Stack spacing={3} sx={{ mb: 5, alignItems: 'center' }}>
          <Stack spacing={1} sx={{ textAlign: 'center' }}>
            <Typography variant="h4">{latestDraw.drwNo}회 당첨결과</Typography>
            <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
              ({latestDraw.drwNoDate} 추첨)
            </Typography>
          </Stack>

          <Stack direction="row" spacing={{ xs: 1, md: 2 }} alignItems="center">
            {latestDraw.numbers.map((num) => (
              <LottoLibrary.Ball
                key={num}
                sx={{
                  width: { xs: 30, md: 48, lg: 64 },
                  height: { xs: 30, md: 48, lg: 64 },
                  fontSize: { xs: '0.8rem', md: '1.2rem', lg: '1.6rem' },
                  background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent 60%), ${LottoLibrary.getBallColor(
                    num
                  )}`,
                  boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
                }}
              >
                {num}
              </LottoLibrary.Ball>
            ))}
            <Typography variant="h5" sx={{ mx: { xs: 1, md: 2 }, color: 'text.disabled' }}>
              +
            </Typography>
            <LottoLibrary.Ball
              sx={{
                width: { xs: 30, md: 48, lg: 64 },
                height: { xs: 30, md: 48, lg: 64 },
                fontSize: { xs: '0.8rem', md: '1.2rem', lg: '1.6rem' },
                background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent 60%), ${LottoLibrary.getBallColor(
                  latestDraw.bonus
                )}`,
                boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
              }}
            >
              {latestDraw.bonus}
            </LottoLibrary.Ball>
          </Stack>
        </Stack>
      )}

      <Box
        sx={{
          width: '100%',
          display: 'flex',
          justifyContent: 'center',
          pb: 2,
        }}
      >
        <Stack
          direction="row"
          spacing={{ xs: 1, md: 4 }}
          sx={{
            transform: { xs: 'scale(0.8)', sm: 'scale(0.9)', md: 'scale(1)' },
            transformOrigin: 'top center',
            width: { xs: 'calc(100% / 0.8)', sm: 'calc(100% / 0.9)', md: '100%' },
            maxWidth: { xs: 450, sm: 500, md: '100%' },
            justifyContent: 'center',
          }}
        >
          {/* 왼쪽: 포함수 */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Typography
              variant="subtitle1"
              sx={{
                textAlign: 'center',
                mb: 1,
                color: 'text.secondary',
                fontSize: { xs: '0.85rem', md: '1rem' },
                fontWeight: 700,
                whiteSpace: 'nowrap',
              }}
            >
              반드시 포함할 숫자
            </Typography>
            <LottoPaper
              headerText="1,000원"
              selectedNumbers={includedNumbers}
              disabledNumbers={excludedNumbers}
              onToggle={handleToggleIncluded}
              onReset={() => setIncludedNumbers([])}
              onAutoSelect={() => handleAutoSelect('included')}
              maxSelection={6}
              color="#FF7575"
            />
          </Box>

          {/* 오른쪽: 제외수 */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Typography
              variant="subtitle1"
              sx={{
                textAlign: 'center',
                mb: 1,
                color: 'text.secondary',
                fontSize: { xs: '0.85rem', md: '1rem' },
                fontWeight: 700,
                whiteSpace: 'nowrap',
              }}
            >
              절대 나오면 안되는 숫자
            </Typography>
            <LottoPaper
              headerText="1,000원"
              selectedNumbers={excludedNumbers}
              disabledNumbers={includedNumbers}
              onToggle={handleToggleExcluded}
              onReset={() => setExcludedNumbers([])}
              onAutoSelect={() => handleAutoSelect('excluded')}
              maxSelection={39}
              color="#7E91FF"
            />
          </Box>
        </Stack>
      </Box>

      {/* 하단 번호 생성 버튼 */}
      <Box
        sx={{
          mt: 3,
          mb: 4,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <Button
          variant="contained"
          color="primary"
          size="large"
          onClick={handleGenerateAndOpenModal}
          startIcon={<Iconify icon="solar:wand-bold" width={24} />}
          sx={{
            py: 1.5,
            px: 6,
            fontSize: '1.05rem',
            fontWeight: 'bold',
            borderRadius: '28px',
            boxShadow: (theme) => theme.customShadows.z16,
          }}
        >
          번호 생성
        </Button>
      </Box>

      {/* 결과 생성 모달 */}
      <Dialog
        open={openResultModal}
        onClose={() => setOpenResultModal(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            p: 0,
            m: { xs: 1.5, sm: 2 },
            width: { xs: 'calc(100% - 24px)', sm: '100%' },
            minHeight: { xs: '70vh', sm: '75vh' },
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        <DialogTitle
          sx={{
            m: 0,
            px: { xs: 2, sm: 3 },
            py: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Typography variant="h6" component="div" sx={{ fontWeight: 'bold' }}>
            추천 로또 번호 결과
          </Typography>
          <IconButton
            aria-label="close"
            onClick={() => setOpenResultModal(false)}
            sx={{ color: (theme) => theme.palette.grey[500] }}
          >
            <Iconify icon="mingcute:close-line" />
          </IconButton>
        </DialogTitle>

        <DialogContent
          dividers
          sx={{
            borderBottom: 'none',
            px: { xs: 1.5, sm: 3 },
            py: { xs: 2, sm: 3 },
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          <DrawingGeneratedResults
            results={generatedResults}
            includedNumbers={includedNumbers}
            onShare={handleShare}
          />
        </DialogContent>

        <DialogActions
          sx={{
            px: { xs: 2, sm: 3 },
            pb: 2.5,
            pt: 1.5,
            justifyContent: 'space-between',
          }}
        >
          <Button
            variant="outlined"
            color="inherit"
            onClick={() => {
              handleReset();
              setOpenResultModal(false);
            }}
            startIcon={<Iconify icon="solar:restart-bold" />}
          >
            초기화
          </Button>
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleGenerate}
              startIcon={<Iconify icon="solar:wand-bold" />}
            >
              다시 생성
            </Button>
            <Button variant="outlined" color="inherit" onClick={() => setOpenResultModal(false)}>
              닫기
            </Button>
          </Stack>
        </DialogActions>
      </Dialog>
    </DashboardContent>
  );
}
