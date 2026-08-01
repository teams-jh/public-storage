import type { Metadata } from 'next';

import { OverviewHistoryView } from 'src/sections/overview/history/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Lotto Viewer | 과거순위` };

export default function Page() {
  return <OverviewHistoryView />;
}
