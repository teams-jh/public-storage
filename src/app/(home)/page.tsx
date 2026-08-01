import { redirect } from 'next/navigation';

import { CONFIG } from 'src/global-config';

// ----------------------------------------------------------------------

export default function Page() {
  redirect(CONFIG.auth.redirectPath);
}
