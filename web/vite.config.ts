import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const here = fileURLToPath(new URL('.', import.meta.url));

/**
 * 契约页的构建与开发服务。
 *
 * 契约页只做一件事：把 composition 挂进一个可被 Playwright 驱动的页面，
 * 并暴露 `window.__A2V__`（version 2）。它复用与 Remotion 渲染路径**同一份**源码
 * 与同一个样式入口，因此体检量到的画面与成片由同一套代码产生。
 *
 * `base: './'` 是必需的：契约页由渲染/体检时的静态服务器挂在别名前缀下
 * （`/__a2v_web__/dist/contract/contract.html`），绝对路径的 `/assets/...`
 * 会落到服务器根的 404 上。资源一律相对页面走，挂在哪都能取到。
 */
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': `${here}src`,
      // 作品代码场景可导入的唯一项目内部模块（依赖白名单的成员）
      '@a2v/scene': `${here}src/code-scene/index.ts`,
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
