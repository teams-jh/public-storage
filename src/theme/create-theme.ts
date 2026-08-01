'use client';

import type { Theme, Components } from '@mui/material/styles';
import type { ThemeOptions } from './types';
import type { SettingsState } from 'src/components/settings';

import { hexToRgbChannel, createPaletteChannel } from 'minimal-shared/utils';

import { createTheme as createMuiTheme } from '@mui/material/styles';

import { mixins } from './core/mixins';
import { opacity } from './core/opacity';
import { themeConfig } from './theme-config';
import { createShadows } from './core/shadows';
import { components } from './core/components';
import { typography } from './core/typography';
import { createCustomShadows } from './core/custom-shadows';
import { applySettingsToTheme, applySettingsToComponents } from './with-settings';

// ----------------------------------------------------------------------

const { grey, common } = themeConfig.palette;

const lightPalette = {
  primary: createPaletteChannel(themeConfig.palette.primary),
  secondary: createPaletteChannel(themeConfig.palette.secondary),
  info: createPaletteChannel(themeConfig.palette.info),
  success: createPaletteChannel(themeConfig.palette.success),
  warning: createPaletteChannel(themeConfig.palette.warning),
  error: createPaletteChannel(themeConfig.palette.error),
  common: createPaletteChannel(themeConfig.palette.common),
  grey: createPaletteChannel(themeConfig.palette.grey),
  divider: `rgba(${hexToRgbChannel(grey[500])} / 0.2)`,
  text: {
    primary: grey[800],
    secondary: grey[600],
    disabled: grey[500],
    primaryChannel: hexToRgbChannel(grey[800]),
    secondaryChannel: hexToRgbChannel(grey[600]),
    disabledChannel: hexToRgbChannel(grey[500]),
  },
  background: {
    paper: '#FFFFFF',
    default: '#FFFFFF',
    neutral: grey[200],
    paperChannel: hexToRgbChannel('#FFFFFF'),
    defaultChannel: hexToRgbChannel('#FFFFFF'),
    neutralChannel: hexToRgbChannel(grey[200]),
  },
  action: {
    hover: `rgba(${hexToRgbChannel(grey[500])} / 0.08)`,
    selected: `rgba(${hexToRgbChannel(grey[500])} / 0.16)`,
    focus: `rgba(${hexToRgbChannel(grey[500])} / 0.24)`,
    disabled: `rgba(${hexToRgbChannel(grey[500])} / 0.8)`,
    disabledBackground: `rgba(${hexToRgbChannel(grey[500])} / 0.24)`,
    hoverOpacity: 0.08,
    selectedOpacity: 0.08,
    focusOpacity: 0.12,
    activatedOpacity: 0.12,
    disabledOpacity: 0.48,
  },
  shared: {
    inputOutlined: `rgba(${hexToRgbChannel(grey[500])} / 0.32)`,
    inputUnderline: `rgba(${hexToRgbChannel(grey[500])} / 0.08)`,
    paperOutlined: `rgba(${hexToRgbChannel(grey[500])} / 0.16)`,
    paperNeutral: grey[200],
    buttonOutlined: `rgba(${hexToRgbChannel(grey[500])} / 0.24)`,
  },
};

const darkPalette = {
  ...lightPalette,
};

export const baseTheme: ThemeOptions = {
  colorSchemes: {
    light: {
      palette: lightPalette,
      shadows: createShadows(hexToRgbChannel(themeConfig.palette.grey[500])),
      customShadows: createCustomShadows(themeConfig.palette),
      opacity,
    },
    dark: {
      palette: lightPalette,
      shadows: createShadows(hexToRgbChannel(themeConfig.palette.grey[500])),
      customShadows: createCustomShadows(themeConfig.palette),
      opacity,
    },
  },
  mixins,
  components,
  typography,
  shape: { borderRadius: 8 },
  direction: themeConfig.direction,
  cssVariables: themeConfig.cssVariables,
};

// ----------------------------------------------------------------------

type CreateThemeProps = {
  settingsState?: SettingsState;
  themeOverrides?: ThemeOptions;
  localeComponents?: { components?: Components<Theme> };
};

export function createTheme({
  settingsState,
  themeOverrides = {},
  localeComponents = {},
}: CreateThemeProps = {}): Theme {
  // Update core theme settings (colorSchemes, typography, etc.)
  const updatedCore = settingsState ? applySettingsToTheme(baseTheme, settingsState) : baseTheme;

  // Update component settings (only components)
  const updatedComponents = settingsState ? applySettingsToComponents(settingsState) : {};

  // Create and return the final theme
  const theme = createMuiTheme(updatedCore, updatedComponents, localeComponents, themeOverrides);

  return theme;
}
