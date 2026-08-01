import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'lotto-viewer-mobile',
  brand: {
    displayName: '로또 패턴 통계 분석', // 화면에 노출될 앱의 한글 이름으로 바꿔주세요.
    primaryColor: '#10b981', // 화면에 노출될 앱의 기본 색상으로 바꿔주세요.
    icon: 'https://static.toss.im/appsintoss/60445/374b6127-a993-4d49-84a6-35bcd1c0acd9.png', // 화면에 노출될 앱의 아이콘 이미지 주소로 바꿔주세요.
  },
  web: {
    host: 'localhost', //'192.168.55.120',
    port: 5173,
    commands: {
      dev: 'next dev -p 5173 -H 0.0.0.0',
      build: 'next build',
    },
  },
  permissions: [{
    name: 'clipboard',
    access: 'read',
  },
  {
    name: 'clipboard',
    access: 'write',
  },],
  outdir: 'out',
  webViewProps: {
    type: 'partner', // 게임 내비게이션
  }
});
