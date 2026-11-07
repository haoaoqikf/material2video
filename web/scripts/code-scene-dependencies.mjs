/** 可扩展的作品依赖登记；只加载本地、版本已锁定的直接依赖。 */
import fs from 'node:fs';
import path from 'node:path';

const packageName = /^(?:@[a-z0-9_.-]+\/)?[a-z0-9][a-z0-9_.-]*$/;
const exactVersion = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;
const loaders = new Set(['dataurl', 'file', 'binary', 'text', 'json']);
const scriptExtensions = new Set(['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']);

export function readSceneDependencies(web) {
  const filename = path.join(web, 'code-scene-dependencies.json');
  const data = JSON.parse(fs.readFileSync(filename, 'utf8'));
  if (data.schemaVersion !== 1 || !data.packages || Array.isArray(data.packages)
      || typeof data.packages !== 'object' || !data.loaders || Array.isArray(data.loaders)
      || typeof data.loaders !== 'object' || Object.keys(data).some(k => !['schemaVersion', 'packages', 'loaders'].includes(k))) {
    throw new Error('代码场景依赖登记结构无效');
  }
  for (const [name, entry] of Object.entries(data.packages)) {
    if (!packageName.test(name) || !entry || typeof entry !== 'object'
        || Object.keys(entry).some(k => !['version', 'source', 'license', 'integration'].includes(k))
        || !exactVersion.test(entry.version ?? '')
        || !['source', 'license', 'integration'].every(k => typeof entry[k] === 'string' && entry[k].trim())
        || !/^https:\/\//.test(entry.source)) {
      throw new Error(`代码场景依赖登记无效：${name}`);
    }
  }
  for (const [extension, loader] of Object.entries(data.loaders)) {
    if (!/^\.[a-z0-9]+$/.test(extension) || scriptExtensions.has(extension) || !loaders.has(loader)) {
      throw new Error(`代码场景资源加载登记无效：${extension}`);
    }
  }
  return data;
}

export function requireRegisteredDependency(web, registry, name) {
  const entry = Object.hasOwn(registry.packages, name) ? registry.packages[name] : undefined;
  if (!entry) throw new Error(`未登记的作品依赖：${name}；完成选型、适配验证后加入 web/code-scene-dependencies.json`);
  const root = path.join(web, 'node_modules', ...name.split('/'));
  let installed;
  try { installed = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')); }
  catch (error) { throw new Error(`已登记依赖未安装或元数据不可读：${name}；请运行 pnpm -C web install`, {cause: error}); }
  if (installed.name !== name || installed.version !== entry.version) {
    throw new Error(`作品依赖版本失配：${name}，登记 ${entry.version}，实际 ${installed.version}`);
  }
  return fs.realpathSync(root);
}
