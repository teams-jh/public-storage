import type { Metadata } from 'next';

import { OverviewRoundView } from 'src/sections/overview/round/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Lotto Viewer | 회차분석` };

export default function Page() {
  return <OverviewRoundView />;
}
