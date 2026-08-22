import aitDevtools from "@apps-in-toss/devtools/unplugin";
import type { NextConfig } from 'next';

const isStaticExport = true;

/** @type {import('next').NextConfig} */
const nextConfig: any = {
  trailingSlash: true,
  output: isStaticExport ? 'export' : undefined,
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || '',
  assetPrefix: process.env.NEXT_PUBLIC_BASE_PATH || '',
  images: {
    unoptimized: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  env: {
    BUILD_STATIC_EXPORT: JSON.stringify(isStaticExport),
  },
  webpack(config: any, { dev, isServer }: any) {
    if (dev && !isServer) {
      config.plugins.unshift(aitDevtools.webpack());
    }

    config.module.rules.push({
      test: /\.svg$/,
      use: ['@svgr/webpack'],
    });

    return config;
  },
  turbopack: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
  },
};

export default nextConfig;