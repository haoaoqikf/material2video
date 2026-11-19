import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const here = fileURLToPath(new URL('.', import.meta.url));

/**
 * 契约页的构建与开发服务。
 *
 * 契约页只做一件事：把 composition 挂进一个可被 Playwright 驱动的页面，
 * 并暴露 `window.__M2V__`（version 6）。它复用与 Remotion 渲染路径**同一份**源码
 * 与同一个样式入口，因此量测到的画面与成片由同一套代码产生。
 *
 * `base: './'` 是必需的：契约页由渲染/体检时的静态服务器挂在别名前缀下
 * （`/__m2v_web__/dist/contract/contract.html`），绝对路径的 `/assets/...`
 * 会落到服务器根的 404 上。资源一律相对页面走，挂在哪都能取到。
 */
export default defineConfig({
  base: './',
  plugins: [react()],
  resolve: {
    alias: {
      '@': `${here}src`,
      // React 与 Remotion 固定指向本工程安装的版本，
      // 与 tsconfig paths / remotion.config.ts 的别名保持同一口径。
      // 具体路径排在包名前面，避免前缀匹配吃掉子路径。
      'react/jsx-runtime': `${here}node_modules/react/jsx-runtime`,
      'react-dom/client': `${here}node_modules/react-dom/client`,
      react: `${here}node_modules/react`,
      'react-dom': `${here}node_modules/react-dom`,
      remotion: `${here}node_modules/remotion`,
    },
  },
  build: {
    outDir: 'dist/contract',
    emptyOutDir: true,
    rollupOptions: {
      input: { contract: `${here}contract.html` },
    },
  },
  server: {
    port: 5178,
    strictPort: true,
  },
});
