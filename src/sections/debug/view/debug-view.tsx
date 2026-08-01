'use client';

import { useState, useEffect } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import CardContent from '@mui/material/CardContent';

import { Iconify } from 'src/components/iconify';

// ----------------------------------------------------------------------

interface DebugViewProps {
  onReset?: () => void;
}

export function DebugView({ onReset }: DebugViewProps) {
  const [sysInfo, setSysInfo] = useState<{
    env: string;
    screenWidth: number;
    screenHeight: number;
    userAgent: string;
    currentTime: string;
  }>({
    env: process.env.NODE_ENV || 'development',
    screenWidth: 0,
    screenHeight: 0,
    userAgent: '',
    currentTime: '',
  });

  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setSysInfo({
        env: process.env.NODE_ENV || 'development',
        screenWidth: window.innerWidth,
        screenHeight: window.innerHeight,
        userAgent: navigator.userAgent,
        currentTime: new Date().toLocaleString(),
      });
      setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] DebugView loaded.`]);
    }
  }, []);

  const handleClearStorage = () => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.clear();
        sessionStorage.clear();
        setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] Storage cleared.`]);
      } catch (err) {
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] Storage clear error: ${String(err)}`,
        ]);
      }
    }
  };

  const handleReload = () => {
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  };

  const handleResetMode = () => {
    if (onReset) {
      onReset();
    } else if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('toggle-debug-mode', { detail: { enabled: false } }));
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: 3 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Card
          sx={{
            p: 3,
            background: (theme) =>
              `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 100%)`,
            color: 'common.white',
            boxShadow: (theme) => theme.customShadows?.z16 || 4,
          }}
        >
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <Box
                sx={{
                  width: 44,
                  height: 44,
                  borderRadius: '12px',
                  bgcolor: 'rgba(255, 255, 255, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Iconify icon="solar:bug-bold" width={28} />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Debug View
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  개발 및 테스트용 디버그 콘솔
                </Typography>
              </Box>
            </Stack>
            <Chip
              label="임시 페이지"
              size="small"
              sx={{
                bgcolor: 'error.main',
                color: 'common.white',
                fontWeight: 'bold',
              }}
            />
          </Stack>
        </Card>

        {/* System Info */}
        <Card>
          <CardContent>
            <Typography
              variant="subtitle1"
              sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}
            >
              <Iconify icon="solar:devices-bold" width={20} />
              시스템 정보
            </Typography>
            <Stack spacing={1.5} divider={<Divider flexItem />}>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  환경 (Environment)
                </Typography>
                <Chip label={sysInfo.env} size="small" color="info" variant="soft" />
              </Stack>

              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  해상도 (Resolution)
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {sysInfo.screenWidth} x {sysInfo.screenHeight} px
                </Typography>
              </Stack>

              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  현재 시간
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {sysInfo.currentTime}
                </Typography>
              </Stack>

              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                  User Agent
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    wordBreak: 'break-all',
                    bgcolor: 'background.neutral',
                    p: 1,
                    borderRadius: 1,
                    fontFamily: 'monospace',
                  }}
                >
                  {sysInfo.userAgent || 'N/A'}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        {/* Actions */}
        <Card>
          <CardContent>
            <Typography
              variant="subtitle1"
              sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}
            >
              <Iconify icon="solar:settings-bold" width={20} />
              디버그 액션
            </Typography>
            <Stack spacing={1.5}>
              <Button
                variant="contained"
                color="primary"
                fullWidth
                startIcon={<Iconify icon="solar:home-2-bold" />}
                onClick={handleResetMode}
                sx={{ height: 44 }}
              >
                일반 홈 화면으로 돌아가기
              </Button>
              <Stack direction="row" spacing={1.5}>
                <Button
                  variant="outlined"
                  color="warning"
                  fullWidth
                  startIcon={<Iconify icon="solar:trash-bin-trash-bold" />}
                  onClick={handleClearStorage}
                >
                  스토리지 초기화
                </Button>
                <Button
                  variant="outlined"
                  color="info"
                  fullWidth
                  startIcon={<Iconify icon="solar:restart-bold" />}
                  onClick={handleReload}
                >
                  페이지 새로고침
                </Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>

        {/* Debug Logs */}
        <Card>
          <CardContent>
            <Typography
              variant="subtitle1"
              sx={{ fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}
            >
              <Iconify icon="solar:document-text-bold" width={20} />
              실시간 콘솔 로그
            </Typography>
            <Box
              sx={{
                bgcolor: 'grey.900',
                color: 'common.white',
                p: 2,
                borderRadius: 1.5,
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                minHeight: 120,
                maxHeight: 200,
                overflowY: 'auto',
              }}
            >
              {logs.length === 0 ? (
                <Typography variant="caption" sx={{ color: 'grey.500' }}>
                  로그가 없습니다.
                </Typography>
              ) : (
                logs.map((log, idx) => (
                  <div key={idx} style={{ marginBottom: 4 }}>
                    {log}
                  </div>
                ))
              )}
            </Box>
          </CardContent>
        </Card>
      </Stack>
    </Container>
  );
}
