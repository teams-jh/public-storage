import type { AxiosRequestConfig } from 'axios';

import axios from 'axios';

import { CONFIG } from 'src/global-config';

// ----------------------------------------------------------------------

const axiosInstance = axios.create({
  baseURL: CONFIG.serverUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error?.response?.data?.message || error?.message || 'Something went wrong!';
    console.error('Axios error:', message);
    return Promise.reject(new Error(message));
  }
);

export default axiosInstance;

// ----------------------------------------------------------------------

export const fetcher = async <T = unknown>(
  args: string | [string, AxiosRequestConfig]
): Promise<T> => {
  const [url] = Array.isArray(args) ? args : [args, {}];

  if (url === endpoints.chat) {
    return { messages: [] } as any;
  }
  if (url === endpoints.kanban) {
    return { board: { columns: [] } } as any;
  }
  if (url === endpoints.calendar) {
    return { events: [] } as any;
  }
  if (url === endpoints.auth.me) {
    return {
      user: {
        id: 'e99f09a7-dd88-49d5-b1c8-1daf80c2d7b1',
        displayName: 'Jaydon Frankie',
        email: 'demo@minimals.cc',
        photoURL: '/assets/images/avatar/avatar-25.jpg',
        phoneNumber: '+1 415-555-2671',
        country: 'United States',
        address: '90210 Broadway, LA',
        state: 'California',
        city: 'Los Angeles',
        zipCode: '90210',
        about:
          'Praesent turpis. Phasellus viverra nulla ut metus varius laoreet. Phasellus tempus.',
        role: 'admin',
        isPublic: true,
      },
    } as any;
  }
  if (url === endpoints.mail.list) {
    return { mails: [] } as any;
  }
  if (url === endpoints.post.list) {
    return { posts: [] } as any;
  }
  if (url === endpoints.product.list) {
    return { products: [] } as any;
  }

  return Promise.resolve({} as any);
};

// ----------------------------------------------------------------------

export const endpoints = {
  chat: '/api/chat',
  kanban: '/api/kanban',
  calendar: '/api/calendar',
  auth: {
    me: '/api/auth/me',
    signIn: '/api/auth/sign-in',
    signUp: '/api/auth/sign-up',
  },
  mail: {
    list: '/api/mail/list',
    details: '/api/mail/details',
    labels: '/api/mail/labels',
  },
  post: {
    list: '/api/post/list',
    details: '/api/post/details',
    latest: '/api/post/latest',
    search: '/api/post/search',
  },
  product: {
    list: '/api/product/list',
    details: '/api/product/details',
    search: '/api/product/search',
  },
} as const;
