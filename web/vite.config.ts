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
      // 依赖白名单的裸包：作品模块在仓库外的内容根，node_modules
      // 向上查找找不到 web/ 的依赖，这里固定指到本工程安装的版本，
      // 与 tsconfig paths / remotion.config.ts 的别名保持同一口径。
      // 具体路径排在包名前面，避免前缀匹配吃掉子路径。
      'react/jsx-runtime': `${here}node_modules/react/jsx-runtime`,
      'react-dom/client': `${here}node_modules/react-dom/client`,
      react: `${here}node_modules/react`,
      'react-dom': `${here}node_modules/react-dom`,
      remotion: `${here}node_modules/remotion`,
      echarts: `${here}node_modules/echarts`,
      '@dagrejs/dagre': `${here}node_modules/@dagrejs/dagre`,
      'lucide-react': `${here}node_modules/lucide-react`,
      '@remotion/': `${here}node_modules/@remotion/`,
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
