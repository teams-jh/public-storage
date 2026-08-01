// import { toast } from 'src/components/snackbar';

export const getIsMobile = () => {
  if (typeof window === 'undefined') return false;

  const userAgent = window.navigator.userAgent;
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);

  // toast.info(`Is Mobile: ${isMobile}`);

  return isMobile;
};
