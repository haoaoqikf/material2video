/**
 * 把字体仓里的字体搬到两个打包器都能取到的位置，并登记字体清单。
 *
 * 字体的**来源与摘要**由仓库根 `fonts/registry.json` 管理，二进制不入库；
 * `src/assets/fonts.json` 声明画面实际注册的字体系列，源目录指向 `fonts/files`。
 * 两个打包器都只认工程内可服务的文件：Vite 从 `publicDir` 拷，Remotion 从
 * `public/` 拷。因此这里在构建前把字体同步进 `作品根目录public/fonts/`（已 gitignore），
 * 清单同时落盘给缺字机检与溯源使用。
 *
 * 关键约定：**源文件缺失或摘要不符必须让构建失败**。
 * 「安静地画出系统字体」正是本项目最怕的一类静默失败——成片出来了，字全变了，没有任何报错。
 */

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const webDir = path.resolve(scriptDir, '..');
const manifestPath = path.join(webDir, 'src/assets/fonts.json');
const targetDir = path.join(webDir, 'public/fonts');

function fail(message) {
  process.stderr.write(`sync-fonts: ${message}\n`);
  process.exit(1);
}

if (!fs.existsSync(manifestPath)) {
  fail(`找不到字体清单 ${path.relative(webDir, manifestPath)}`);
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const sourceDir = path.resolve(webDir, manifest.sourceDirFromWeb);
const licenseDir = path.resolve(webDir, manifest.licenseDirFromWeb || manifest.sourceDirFromWeb);
const registryPath = path.join(webDir, 'fonts/registry.json');
const restoreHint = '请先运行：uv run python fonts/fetch.py';

if (!fs.existsSync(registryPath)) {
  fail(`字体登记表缺失：${registryPath}（${restoreHint}）`);
}
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const registered = new Map((registry.fonts || []).map((entry) => [entry.file, entry]));

if (!fs.existsSync(sourceDir)) {
  fail(
    `字体源目录不存在：${sourceDir}\n` +
      `  （清单里的 sourceDirFromWeb 为 ${manifest.sourceDirFromWeb}，相对于 ${webDir}；${restoreHint}）`,
  );
}

fs.mkdirSync(targetDir, { recursive: true });

const entries = [];

for (const font of manifest.files) {
  const record = registered.get(font.file);
  if (!record) {
    fail(`字体 ${font.file} 未在 fonts/registry.json 登记（${restoreHint}）`);
  }
  const from = path.join(sourceDir, font.file);
  if (!fs.existsSync(from)) {
    fail(`字体文件缺失：${from}（清单声明了 ${font.family} 需要它；${restoreHint}）`);
  }
  const size = fs.statSync(from).size;
  if (size === 0) {
    fail(`字体文件是空的：${from}`);
  }
  if (size !== record.bytes) {
    fail(`字体字节数与登记不符：${from}（登记 ${record.bytes}，实际 ${size}）`);
  }
  // 目标副本可能仍是旧的正确字节；必须先验证源，不能因同尺寸目标存在而漏检。
  const sourceDigest = createHash('sha256').update(fs.readFileSync(from)).digest('hex');
  if (sourceDigest !== record.sha256) {
    fail(`字体源摘要与登记不符：${from}（登记 ${record.sha256}，实际 ${sourceDigest}；${restoreHint}）`);
  }

  const to = path.join(targetDir, font.file);
  const sameAsTarget = fs.existsSync(to) && fs.statSync(to).size === size;
  if (!sameAsTarget) {
    fs.copyFileSync(from, to);
  }

  const digest = createHash('sha256').update(fs.readFileSync(to)).digest('hex');
  if (digest !== record.sha256) {
    fail(`字体摘要与登记不符：${from}（登记 ${record.sha256}，实际 ${digest}；${restoreHint}）`);
  }
  entries.push({
    family: font.family,
    file: font.file,
    url: `fonts/${font.file}`,
    weight: font.weight,
    usage: font.usage,
    bytes: size,
    sha256: digest,
    license: font.license,
    licenseSource: `${manifest.licenseDirFromWeb || manifest.sourceDirFromWeb}/${font.license}`,
  });

  // 许可证必须一并就位：OFL 要求分发字体时随附许可证原文
  const licenseFrom = path.join(licenseDir, font.license);
  if (!fs.existsSync(licenseFrom)) {
    fail(`许可证文件缺失：${licenseFrom}（${font.family} 采用 SIL OFL 1.1，必须随字体分发）`);
  }
  fs.copyFileSync(licenseFrom, path.join(targetDir, font.license));
}

// 清单落盘：缺字机检与溯源都读它，而不是去解析样式表里的 @font-face 文本
fs.writeFileSync(
  path.join(targetDir, 'manifest.json'),
  `${JSON.stringify({ generatedBy: 'scripts/sync-fonts.mjs', fonts: entries }, null, 2)}\n`,
  'utf8',
);

process.stdout.write(
  `sync-fonts: ${entries.length} 套字体已就位（${entries
    .map((entry) => `${entry.family} ${Math.round(entry.bytes / 1024)}KB`)
    .join('，')}）\n`,
);
