import 'src/global.css';

import type { Metadata, Viewport } from 'next';

import InitColorSchemeScript from '@mui/material/InitColorSchemeScript';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';

import { ThemeProvider } from 'src/theme';
import { CONFIG } from 'src/global-config';
import { themeConfig } from 'src/theme/theme-config';

import Box from '@mui/material/Box';
import TossBannerAd from '../../toss/toss-banner-ad';

import { Snackbar } from 'src/components/snackbar';
import { ProgressBar } from 'src/components/progress-bar';
import { MotionLazy } from 'src/components/animate/motion-lazy';
import { detectSettings } from 'src/components/settings/server';
import { LocalizationProvider } from 'src/components/localization-provider';
import { SettingsDrawer, defaultSettings, SettingsProvider } from 'src/components/settings';

// ----------------------------------------------------------------------

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: themeConfig.palette.primary.main,
};

export const metadata: Metadata = {
  icons: [
    {
      rel: 'icon',
      url: `${CONFIG.assetsDir}/favicon.ico`,
    },
  ],
};

// ----------------------------------------------------------------------

type RootLayoutProps = {
  children: React.ReactNode;
};

async function getAppConfig() {
  if (CONFIG.isStaticExport) {
    return {
      lang: 'ko',
      cookieSettings: undefined,
      dir: defaultSettings.direction,
    };
  } else {
    const settings = await detectSettings();

    return {
      lang: 'ko',
      cookieSettings: settings,
      dir: settings.direction,
    };
  }
}

export default async function RootLayout({ children }: RootLayoutProps) {
  const appConfig = await getAppConfig();

  return (
    <html lang={appConfig.lang} dir={appConfig.dir} suppressHydrationWarning>
      <body>
        <InitColorSchemeScript
          modeStorageKey={themeConfig.modeStorageKey}
          attribute={themeConfig.cssVariables.colorSchemeSelector}
          defaultMode={themeConfig.defaultMode}
        />

        <SettingsProvider
          defaultSettings={defaultSettings}
          cookieSettings={appConfig.cookieSettings}
        >
          <LocalizationProvider>
            <AppRouterCacheProvider options={{ key: 'css' }}>
              <ThemeProvider
                modeStorageKey={themeConfig.modeStorageKey}
                defaultMode={themeConfig.defaultMode}
              >
                <MotionLazy>
                  <Snackbar />
                  <ProgressBar />
                  <SettingsDrawer defaultSettings={defaultSettings} />
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      height: '100dvh',
                      width: '100vw',
                      overflow: 'hidden',
                    }}
                  >
                    <Box
                      sx={{
                        flex: '1 1 auto',
                        minHeight: 0,
                        overflowY: 'auto',
                        display: 'flex',
                        flexDirection: 'column',
                      }}
                    >
                      {children}
                    </Box>
                    <TossBannerAd />
                  </Box>
                </MotionLazy>
              </ThemeProvider>
            </AppRouterCacheProvider>
          </LocalizationProvider>
        </SettingsProvider>
      </body>
    </html>
  );
}
