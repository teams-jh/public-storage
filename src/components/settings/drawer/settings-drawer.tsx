'use client';

import type { SettingsDrawerProps } from '../types';

import { useCallback } from 'react';
import { hasKeys, varAlpha } from 'minimal-shared/utils';

import Box from '@mui/material/Box';
import Badge from '@mui/material/Badge';
import Drawer from '@mui/material/Drawer';
import SvgIcon from '@mui/material/SvgIcon';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';

import { themeConfig } from 'src/theme/theme-config';

import { settingIcons } from './icons';
import { Iconify } from '../../iconify';
import { Scrollbar } from '../../scrollbar';
import { SmallBlock, LargeBlock } from './styles';
import { FullScreenButton } from './fullscreen-button';
import { FontSizeOptions, FontFamilyOptions } from './font-options';
import { useSettingsContext } from '../context/use-settings-context';

// ----------------------------------------------------------------------

export function SettingsDrawer({ sx, defaultSettings }: SettingsDrawerProps) {
  const settings = useSettingsContext();

  // Visible options by default settings
  const visibility = {
    fontSize: hasKeys(defaultSettings, ['fontSize']),
    fontFamily: hasKeys(defaultSettings, ['fontFamily']),
  };

  const handleReset = useCallback(() => {
    settings.onReset();
  }, [settings]);

  const renderHead = () => (
    <Box
      sx={{
        py: 2,
        pr: 1,
        pl: 2.5,
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <Typography variant="h6" sx={{ flexGrow: 1 }}>
        Settings
      </Typography>

      <FullScreenButton />

      <Tooltip title="Reset all">
        <IconButton onClick={handleReset}>
          <Badge color="error" variant="dot" invisible={!settings.canReset}>
            <Iconify icon="solar:restart-bold" />
          </Badge>
        </IconButton>
      </Tooltip>

      <Tooltip title="Close">
        <IconButton onClick={settings.onCloseDrawer}>
          <Iconify icon="mingcute:close-line" />
        </IconButton>
      </Tooltip>
    </Box>
  );

  const renderFont = () => (
    <LargeBlock title="Font" sx={{ gap: 2.5 }}>
      {visibility.fontFamily && (
        <SmallBlock
          label="Family"
          canReset={settings.state.fontFamily !== defaultSettings.fontFamily}
          onReset={() => {
            settings.setState({ fontFamily: defaultSettings.fontFamily });
          }}
        >
          <FontFamilyOptions
            value={settings.state.fontFamily}
            onChangeOption={(newOption) => {
              settings.setState({ fontFamily: newOption });
            }}
            options={[
              themeConfig.fontFamily.primary,
              'Inter Variable',
              'DM Sans Variable',
              'Nunito Sans Variable',
            ]}
            icon={<SvgIcon sx={{ width: 28, height: 28 }}>{settingIcons.font}</SvgIcon>}
          />
        </SmallBlock>
      )}
      {visibility.fontSize && (
        <SmallBlock
          label="Size"
          canReset={settings.state.fontSize !== defaultSettings.fontSize}
          onReset={() => {
            settings.setState({ fontSize: defaultSettings.fontSize });
          }}
          sx={{ gap: 5 }}
        >
          <FontSizeOptions
            options={[12, 20]}
            value={settings.state.fontSize}
            onChangeOption={(newOption) => {
              settings.setState({ fontSize: newOption });
            }}
          />
        </SmallBlock>
      )}
    </LargeBlock>
  );

  return (
    <Drawer
      anchor="right"
      open={settings.openDrawer}
      onClose={settings.onCloseDrawer}
      slotProps={{
        backdrop: { invisible: true },
        paper: {
          sx: [
            (theme) => ({
              ...theme.mixins.paperStyles(theme, {
                color: varAlpha(theme.vars.palette.background.defaultChannel, 0.9),
              }),
              width: 360,
            }),
            ...(Array.isArray(sx) ? sx : [sx]),
          ],
        },
      }}
    >
      {renderHead()}

      <Scrollbar>
        <Box
          sx={{
            pb: 5,
            gap: 6,
            px: 2.5,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Box sx={{ mt: -2 }} />
          {(visibility.fontFamily || visibility.fontSize) && renderFont()}
        </Box>
      </Scrollbar>
    </Drawer>
  );
}
