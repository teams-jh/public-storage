'use client';

import { useState, useEffect } from 'react';

import Stack from '@mui/material/Stack';

import { CONFIG } from 'src/global-config';

import { HomeLottoDisplay } from '../home-lotto-display';
import { DebugView } from './debug-view';

// ----------------------------------------------------------------------

const DEBUG_MODE_KEY = 'is_home_debug_mode_active';

export function HomeView() {
  const [isDebugMode, setIsDebugMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined' && CONFIG.isDebug) {
      return sessionStorage.getItem(DEBUG_MODE_KEY) === 'true';
    }
    return false;
  });

  useEffect(() => {
    if (!CONFIG.isDebug) return undefined;

    const handleToggleDebugMode = (event: CustomEvent<{ enabled?: boolean }>) => {
      setIsDebugMode((prev) => {
        const nextState = event.detail?.enabled !== undefined ? event.detail.enabled : !prev;
        if (typeof window !== 'undefined') {
          sessionStorage.setItem(DEBUG_MODE_KEY, String(nextState));
        }
        return nextState;
      });
    };

    window.addEventListener('toggle-debug-mode', handleToggleDebugMode as EventListener);
    return () => {
      window.removeEventListener('toggle-debug-mode', handleToggleDebugMode as EventListener);
    };
  }, []);

  const handleResetDebug = () => {
    setIsDebugMode(false);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(DEBUG_MODE_KEY, 'false');
    }
  };

  if (isDebugMode && CONFIG.isDebug) {
    return <DebugView onReset={handleResetDebug} />;
  }

  return (
    <Stack
      sx={{
        position: 'relative',
        bgcolor: 'background.default',
        gap: 3,
        alignItems: 'center',
        py: 5,
      }}
    >
      <HomeLottoDisplay />
    </Stack>
  );
}
