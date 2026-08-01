import type { NavSectionProps } from 'src/components/nav-section';

import { paths } from 'src/routes/paths';

import { CONFIG } from 'src/global-config';

import { Label } from 'src/components/label';
import { Iconify } from 'src/components/iconify';
import { SvgColor } from 'src/components/svg-color';

// ----------------------------------------------------------------------

const icon = (name: string) => (
  <SvgColor src={`${CONFIG.assetsDir}/assets/icons/navbar/${name}.svg`} />
);

const ICONS = {
  dashboard: icon('ic-dashboard'),
  pattern: <Iconify icon="solar:sort-by-alphabet-bold" />,
  analytics: icon('ic-analytics'),
  round: <Iconify icon="solar:calendar-date-bold" />,
  history: <Iconify icon="solar:cup-star-bold" />,
  drawing: <Iconify icon="solar:restart-bold" />,
};

// ----------------------------------------------------------------------

export const navData: NavSectionProps['data'] = [
  /**
   * Overview
   */
  {
    subheader: 'Overview',
    items: [
      { title: 'Home', path: paths.dashboard.root, icon: ICONS.dashboard },
      { title: '패턴분석', path: paths.dashboard.general.pattern, icon: ICONS.pattern },
      { title: '통계분석', path: paths.dashboard.general.analytics, icon: ICONS.analytics },
      { title: '회차분석', path: paths.dashboard.general.round, icon: ICONS.round },
      { title: '과거순위', path: paths.dashboard.general.history, icon: ICONS.history },
      { title: '번호생성', path: paths.dashboard.general.drawing, icon: ICONS.drawing },
    ],
  },
];
