'use client';

import { useRef } from 'react';

import type { SxProps, Theme } from '@mui/material/styles';
import type { NavSectionProps } from 'src/components/nav-section';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { styled } from '@mui/material/styles';

import { paths } from 'src/routes/paths';
import { usePathname } from 'src/routes/hooks';
import { RouterLink } from 'src/routes/components';

import { CONFIG } from 'src/global-config';

// ----------------------------------------------------------------------

export type NavUnderBarProps = React.ComponentProps<'div'> & {
  sx?: SxProps<Theme>;
  data?: NavSectionProps['data'];
};

export function NavUnderBar({ data, sx, className, ...other }: NavUnderBarProps) {
  const pathname = usePathname();

  const homeClickCountRef = useRef(0);
  const lastHomeClickTimeRef = useRef(0);

  // Extract all navigation items from sections
  const items = data?.flatMap((section) => section.items) ?? [];

  return (
    <NavUnderBarRoot className={className} sx={sx} {...other}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-around',
          height: '100%',
          px: 0.5,
        }}
      >
        {items.map((item) => {
          const isActive =
            item.path === '/dashboard' || item.path === '/dashboard/'
              ? pathname === '/dashboard' || pathname === '/dashboard/'
              : pathname.startsWith(item.path);

          const isHome =
            item.path === paths.dashboard.root ||
            item.path === '/dashboard' ||
            item.path === '/dashboard/';

          return (
            <NavItemButton
              key={item.title}
              component={RouterLink}
              href={item.path}
              onClick={() => {
                if (isHome && CONFIG.isDebug) {
                  const now = Date.now();
                  if (now - lastHomeClickTimeRef.current < 2000) {
                    homeClickCountRef.current += 1;
                  } else {
                    homeClickCountRef.current = 1;
                  }
                  lastHomeClickTimeRef.current = now;

                  if (homeClickCountRef.current >= 5) {
                    homeClickCountRef.current = 0;
                    window.dispatchEvent(
                      new CustomEvent('toggle-debug-mode', { detail: { enabled: true } })
                    );
                  }
                }

                if (isActive && item.path === paths.dashboard.general.pattern) {
                  window.dispatchEvent(new CustomEvent('toggle-pattern-tab'));
                }
              }}
              sx={(theme) => {
                const activeColor = theme.palette.primary.main;
                const inactiveColor = theme.palette.text.secondary;
                const currentColor = isActive ? activeColor : inactiveColor;

                return {
                  color: currentColor,
                  '&:hover': {
                    color: activeColor,
                  },
                };
              }}
            >
              <Box
                sx={{
                  width: 24,
                  height: 24,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mb: 0.5,
                  '& svg': {
                    width: '100%',
                    height: '100%',
                    color: 'currentColor',
                  },
                  '& img': {
                    width: '100%',
                    height: '100%',
                  },
                  '& span': {
                    width: '100%',
                    height: '100%',
                    backgroundColor: 'currentColor',
                  },
                }}
              >
                {item.icon}
              </Box>
              <Typography
                variant="caption"
                noWrap
                sx={{
                  fontSize: '0.7rem',
                  fontWeight: isActive ? 700 : 500,
                  lineHeight: 1,
                }}
              >
                {item.title}
              </Typography>
            </NavItemButton>
          );
        })}
      </Box>
    </NavUnderBarRoot>
  );
}

// ----------------------------------------------------------------------

const NavUnderBarRoot = styled('div')(({ theme }) => ({
  left: 0,
  bottom: 0,
  width: '100%',
  height: 60,
  zIndex: theme.zIndex.appBar,
  position: 'sticky',
  backgroundColor: theme.palette.background.paper,
  borderTop: `1px solid ${theme.palette.divider}`,
  flexShrink: 0,
}));

const NavItemButton = styled(Box)<{ component?: React.ElementType; href?: string }>(() => ({
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  textDecoration: 'none',
  cursor: 'pointer',
  transition: 'color 0.2s ease-in-out',
}));
