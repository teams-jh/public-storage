import type { Shadows } from '@mui/material/styles';

import { varAlpha } from 'minimal-shared/utils';

import { createTheme } from '@mui/material/styles';

// ----------------------------------------------------------------------

function updateShadowColor(shadow: string, colorChannel: string): string {
  return shadow.replace(/rgba\(\d+,\d+,\d+,(.*?)\)/g, (_, alpha) =>
    varAlpha(colorChannel, parseFloat(alpha))
  );
}

export function createShadows(colorChannel: string): Shadows {
  // Get default MUI shadows
  const { shadows: defaultShadows } = createTheme();

  return defaultShadows.map((shadow) => updateShadowColor(shadow, colorChannel)) as Shadows;
}
