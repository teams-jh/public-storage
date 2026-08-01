'use client';

import dayjs from 'dayjs';
import 'dayjs/locale/ko';

import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider as Provider } from '@mui/x-date-pickers/LocalizationProvider';

// ----------------------------------------------------------------------

type Props = {
  children: React.ReactNode;
};

export function LocalizationProvider({ children }: Props) {
  dayjs.locale('ko');

  return (
    <Provider dateAdapter={AdapterDayjs} adapterLocale="ko">
      {children}
    </Provider>
  );
}
