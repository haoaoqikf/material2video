import fs from 'node:fs';
import path from 'node:path';
import { Config } from '@remotion/cli/config';

/** 本工程合成配置；所有别名指向作品自身安装，CLI从作品根读取。 */
const projectDir = process.cwd();
const srcDir = path.resolve(projectDir, 'src');

if (!fs.existsSync(path.join(srcDir, 'index.ts'))) {
  throw new Error(
    `remotion.config.ts 需要在 作品根目录 目录下执行（当前工作目录：${projectDir}）。` +
      `请在 作品根目录 下运行 pnpm studio / pnpm render，或用 --cwd 指定。`,
  );
}

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

Config.overrideWebpackConfig((currentConfiguration) => {
  const modulesDir = path.resolve(projectDir, 'node_modules');
  return {
    ...currentConfiguration,
    resolve: {
      ...currentConfiguration.resolve,
      alias: {
        ...currentConfiguration.resolve?.alias,
        '@': srcDir,
        // 固定本工程依赖，子路径写在包名前，避免前缀覆盖。
        'react/jsx-runtime': path.join(modulesDir, 'react/jsx-runtime'),
        'react-dom/client': path.join(modulesDir, 'react-dom/client'),
        react: modulesDir + '/react',
        'react-dom': modulesDir + '/react-dom',
        remotion: modulesDir + '/remotion',
        '@remotion/': modulesDir + '/@remotion/',
      },
    },
  };
});
