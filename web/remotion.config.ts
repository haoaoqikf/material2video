import fs from 'node:fs';
import path from 'node:path';
import { Config } from '@remotion/cli/config';
import { enableTailwind } from '@remotion/tailwind-v4';

/**
 * Remotion 渲染路径的配置。
 *
 * 三件事，各自都有理由：
 *
 * - **Tailwind 走 Remotion 自己的 webpack 集成**（`@remotion/tailwind-v4`）：
 *   与契约页的 Vite 集成读同一份 `src/styles/index.css`，两条路径产出同一套样式。
 *   这是「预览与导出同源」在构建层的落实，也是它唯一可能悄悄漂移的地方；
 * - **解析 `@/` 别名**：源码用它指向 `src/`，两个打包器都要认识它，
 *   否则同一份源码在浏览器里能跑、在渲染时解析不到；
 * - **中间帧仍是 JPEG**：既有的性能取舍有实测依据（1080 × 1920 下单帧 JPEG 约 66ms，
 *   PNG 约 225ms）。逐像素比对时才改用 PNG，那是命令行开关的事，不是默认值。
 *
 * 成片的编码参数不由这里决定：`yuv420p(tv, bt709)`、宽高偶数、AAC-LC 44.1kHz 立体声
 * 仍由渲染入口统一保证，页面与打包配置都不干预。
 *
 * 注意别名只能按 `process.cwd()` 解析：Remotion CLI 会把这份配置与它自己的代码
 * 一起打成 CJS 再加载，因此 `import.meta.url` 为空、`__dirname` 指向 CLI 的目录，
 * 两者都会把 `@` 解析到错误的位置（实测过）。所以**命令必须在 `web/` 下执行**，
 * 下面的存在性检查负责在跑错目录时立刻报错，而不是让 webpack 报一堆找不到模块。
 */
const projectDir = process.cwd();
const srcDir = path.resolve(projectDir, 'src');

if (!fs.existsSync(path.join(srcDir, 'index.ts'))) {
  throw new Error(
    `remotion.config.ts 需要在 web/ 目录下执行（当前工作目录：${projectDir}）。` +
      `请在 web/ 下运行 pnpm studio / pnpm render，或用 --cwd 指定。`,
  );
}

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

Config.overrideWebpackConfig((currentConfiguration) => {
  const withTailwind = enableTailwind(currentConfiguration);
  const modulesDir = path.resolve(projectDir, 'node_modules');
  return {
    ...withTailwind,
    resolve: {
      ...withTailwind.resolve,
      alias: {
        ...withTailwind.resolve?.alias,
        '@': srcDir,
        // 作品代码场景可导入的唯一项目内部模块（与 vite/tsconfig 同一约定）
        '@m2v/scene': path.resolve(srcDir, 'code-scene/index.ts'),
        // 依赖白名单的裸包：作品模块在仓库外的内容根，向上查找找不到
        // web/ 的依赖；webpack 别名把子路径写在包名前，避免前缀覆盖。
        'react/jsx-runtime': path.join(modulesDir, 'react/jsx-runtime'),
        'react-dom/client': path.join(modulesDir, 'react-dom/client'),
        react: modulesDir + '/react',
        'react-dom': modulesDir + '/react-dom',
        remotion: modulesDir + '/remotion',
        echarts: modulesDir + '/echarts',
        '@dagrejs/dagre': modulesDir + '/@dagrejs/dagre',
        'lucide-react': modulesDir + '/lucide-react',
        '@remotion/': modulesDir + '/@remotion/',
      },
    },
  };
});
