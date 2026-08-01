import type { CustomShadows } from '../types';
import type { ThemeConfig } from '../theme-config';

export type { CustomShadows };

import { varAlpha, hexToRgbChannel } from 'minimal-shared/utils';

// ----------------------------------------------------------------------

export function createShadowColor(colorChannel: string): string {
  return `0 8px 16px 0 ${varAlpha(colorChannel, 0.24)}`;
}

export function createCustomShadows(palette: ThemeConfig['palette']): CustomShadows {
  return {
    z1: `0 1px 2px 0 ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.16)}`,
    z4: `0 4px 8px 0 ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.16)}`,
    z8: `0 8px 16px 0 ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.16)}`,
    z12: `0 12px 24px -4px ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.16)}`,
    z16: `0 16px 32px -4px ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.16)}`,
    z20: `0 20px 40px -4px ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.16)}`,
    z24: `0 24px 48px 0 ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.16)}`,
    /********/
    dialog: `-40px 40px 80px -8px ${varAlpha(hexToRgbChannel(palette.common.black), 0.24)}`,
    card: `0 0 2px 0 ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.2)}, 0 12px 24px -4px ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.12)}`,
    dropdown: `0 0 2px 0 ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.24)}, -20px 20px 40px -4px ${varAlpha(hexToRgbChannel(palette.grey[500]), 0.24)}`,
    /********/
    primary: createShadowColor(hexToRgbChannel(palette.primary.main)),
    secondary: createShadowColor(hexToRgbChannel(palette.secondary.main)),
    info: createShadowColor(hexToRgbChannel(palette.info.main)),
    success: createShadowColor(hexToRgbChannel(palette.success.main)),
    warning: createShadowColor(hexToRgbChannel(palette.warning.main)),
    error: createShadowColor(hexToRgbChannel(palette.error.main)),
  };
}
