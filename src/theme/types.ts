import type {
  Theme,
  Shadows,
  Components,
  ColorSystemOptions,
  CssVarsThemeOptions,
  SupportedColorScheme,
  ThemeOptions as MuiThemeOptions,
} from '@mui/material/styles';
// ----------------------------------------------------------------------

/**
 * Theme options
 * Extended type that includes additional properties for color schemes and CSS variables.
 *
 * @see https://github.com/mui/material-ui/blob/master/packages/mui-material/src/styles/createTheme.ts
 */

export type ThemeColorScheme = SupportedColorScheme;
export type ThemeCssVariables = Pick<
  CssVarsThemeOptions,
  | 'cssVarPrefix'
  | 'rootSelector'
  | 'colorSchemeSelector'
  | 'disableCssColorScheme'
  | 'shouldSkipGeneratingVar'
>;

export type CustomShadows = {
  z1: string;
  z4: string;
  z8: string;
  z12: string;
  z16: string;
  z20: string;
  z24: string;
  primary: string;
  secondary: string;
  info: string;
  success: string;
  warning: string;
  error: string;
  card: string;
  dialog: string;
  dropdown: string;
};

type ColorSchemeOptionsExtended = ColorSystemOptions & {
  shadows?: Partial<Shadows>;
  customShadows?: Partial<CustomShadows>;
};

export type SchemesRecord<T> = Partial<Record<ThemeColorScheme, T>>;

export type ThemeOptions = Omit<MuiThemeOptions, 'components'> &
  Pick<CssVarsThemeOptions, 'defaultColorScheme'> & {
    colorSchemes?: SchemesRecord<ColorSchemeOptionsExtended>;
    cssVariables?: ThemeCssVariables;
    components?: Components<Theme>;
  };

// ----------------------------------------------------------------------

/**
 * DeepPartial utility type that recursively makes all properties of T optional.
 * This is useful for partial configurations and merging deeply nested objects.
 * Supports objects, arrays, and primitive types.
 */
export type DeepPartial<T> = T extends object ? { [P in keyof T]?: DeepPartial<T[P]> } : T;
