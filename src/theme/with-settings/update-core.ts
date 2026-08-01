import type { ColorSystem } from '@mui/material/styles';
import type { SettingsState } from 'src/components/settings';
import type { ThemeOptions, ThemeColorScheme } from '../types';

import { setFont, hexToRgbChannel } from 'minimal-shared/utils';

import { themeConfig } from '../theme-config';

// ----------------------------------------------------------------------

/**
 * Updates the core theme with the provided settings state.
 * @param theme - The base theme options to update.
 * @param settingsState - The settings state containing direction, fontFamily, contrast, and primaryColor.
 * @returns Updated theme options with applied settings.
 */

export function applySettingsToTheme(
  theme: ThemeOptions,
  settingsState?: SettingsState
): ThemeOptions {
  const { direction, fontFamily, contrast = 'default' } = settingsState ?? {};

  const isDefaultContrast = contrast === 'default';

  const lightPalette = theme.colorSchemes?.light?.palette as ColorSystem['palette'];

  const updateColorScheme = (schemeName: ThemeColorScheme) => {
    const currentScheme = theme.colorSchemes?.[schemeName];

    const updatedPalette = {
      ...currentScheme?.palette,
      ...(schemeName === 'light' && {
        background: {
          ...lightPalette?.background,
          ...(!isDefaultContrast && {
            default: themeConfig.palette.grey[200],
            defaultChannel: hexToRgbChannel(themeConfig.palette.grey[200]),
          }),
        },
      }),
    };

    return {
      ...currentScheme,
      palette: updatedPalette,
    };
  };

  return {
    ...theme,
    direction,
    colorSchemes: {
      light: updateColorScheme('light'),
      dark: updateColorScheme('dark'),
    },
    typography: {
      ...theme.typography,
      fontFamily: setFont(fontFamily),
    },
  };
}
