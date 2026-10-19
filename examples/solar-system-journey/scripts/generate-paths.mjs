/**
 * 太阳系一镜到底的相机路径提案生成器（入口）。
 *
 * 只读 `scenes/layout.tsx`，几何、速度与时间窗由 `lib/paths.mjs` 纯计算得出；
 * 本入口负责 CLI 参数、打包布局、写出 `outputs/path-proposal.json` 与
 * `outputs/storyboard.generated.json`，加 `--merge` 时合并 shots 与核定时间预算，
 * 保留旁白原文，最后打印报告。
 *
 * 用法：node examples/solar-system-journey/scripts/generate-paths.mjs [--merge]
 */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {FPS, LEAD_IN, TAIL, SEGMENTS, createProposal} from './lib/paths.mjs';

const HERE = import.meta.dirname;
const EXAMPLE = path.resolve(HERE, '..');
const REPO = path.resolve(EXAMPLE, '../..');
const WEB = path.join(REPO, 'web');
// esbuild 安装在前端工作区；以 web/package.json 为基准解析，避免依赖当前工作目录。
const requireFromWeb = createRequire(path.join(WEB, 'package.json'));
const {build} = requireFromWeb('esbuild');

// ---------------------------------------------------------------- 布局载入

const bundle = path.join(EXAMPLE, 'outputs/.layout-bundle.cjs');
fs.mkdirSync(path.dirname(bundle), {recursive: true});
const layout = path.join(EXAMPLE, 'scenes/layout.tsx');
const entry = `
import * as THREE from 'three';
import {LAYOUT, positionOf} from ${JSON.stringify(layout)};
const POSITIONS = {};
for (const id of Object.keys(LAYOUT)) POSITIONS[id] = positionOf(id).toArray();
module.exports = {THREE, LAYOUT, POSITIONS};
`;
await build({stdin: {contents: entry, resolveDir: WEB}, bundle: true, platform: 'node', format: 'cjs',
  outfile: bundle, nodePaths: [path.join(WEB, 'node_modules')],
  alias: {'m2v/code-scene': path.join(WEB, 'src/code-scene/sdk.tsx')}});
const requireFrom = createRequire(import.meta.url);
const {THREE, LAYOUT, POSITIONS} = requireFrom(bundle);

// ---------------------------------------------------------------- 路径提案

const {shots, storyboard, report, problems, boundarySpeedMax, minDistances, speeds, approachRatios,
  totalFrames}
  = createProposal({THREE, LAYOUT, POSITIONS});

// ---------------------------------------------------------------- 产物写出

const outDir = path.join(EXAMPLE, 'outputs');
fs.mkdirSync(outDir, {recursive: true});
fs.writeFileSync(path.join(outDir, 'path-proposal.json'),
  JSON.stringify({report, storyboard}, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(outDir, 'storyboard.generated.json'),
  JSON.stringify(storyboard, null, 2) + '\n', 'utf8');

if (process.argv.includes('--merge') && !problems.length) {
  const target = path.join(EXAMPLE, 'storyboard.json');
  const current = JSON.parse(fs.readFileSync(target, 'utf8'));
  const existing = current.scenes[0].narrationSegments ?? [];
  const expected = new Set(SEGMENTS.map(segment => segment.id));
  const unknown = existing.filter(segment => !expected.has(segment.id)).map(segment => segment.id);
  if (unknown.length) {
    throw new Error(`storyboard 存在生成器未知的旁白段：${unknown.join('、')}；请先更新 SEGMENTS`);
  }
  for (const segment of SEGMENTS) {
    const old = existing.find(item => item.id === segment.id);
    if (old && old.text !== segment.text) {
      throw new Error(`旁白 ${segment.id} 文本与生成器预算不一致；请更新 SEGMENTS 的文本/frames 并重新量测，不能静默回退`);
    }
  }
  // 只更新镜头、时间预算与段间留白；保留旁白原文、claims 与作者扩展字段。
  const narrationSegments = storyboard.scenes[0].narrationSegments.map(item => {
    const old = existing.find(candidate => candidate.id === item.id) ?? {};
    const next = {...old, ...item};
    if (!('holdFrames' in item)) delete next.holdFrames;
    return next;
  });
  current.scenes[0].content.props.shots = storyboard.scenes[0].content.props.shots;
  Object.assign(current.scenes[0], {durationFrames: totalFrames, leadInFrames: LEAD_IN, tailFrames: TAIL, narrationSegments});
  current.targetSeconds = totalFrames / FPS;
  fs.writeFileSync(target, JSON.stringify(current, null, 2) + '\n', 'utf8');
  console.log('已合并镜头与时间预算（旁白原文未改变，claims 与扩展字段保留）');
}

// ---------------------------------------------------------------- 报告打印

console.log(`镜头 ${shots.length} 个，${totalFrames} 帧 / ${(totalFrames / FPS).toFixed(1)} 秒，覆盖 ${shots[0].startFrame}–${shots[shots.length - 1].endFrame}`);
console.log('逐段跨站预算：');
for (const item of report.transitBudgets) {
  console.log(`  ${item.from} → ${item.to}: ${item.seconds.toFixed(1)} 秒，路径 ${item.pathLength} 单位`);
}
console.log(`问题 ${problems.length} 项；边界速度最大 ×${boundarySpeedMax.toFixed(2)}`);
for (const problem of problems.slice(0, 20)) console.log('  ! ' + problem);
console.log('速度突变最大的 5 个边界：');
for (const speed of [...speeds].sort((a, b) => b.ratio - a.ratio).slice(0, 5)) {
  console.log(`  ${speed.boundary}: ${speed.before} → ${speed.after} (×${speed.ratio})`);
}
const nearest = [...minDistances].sort((a, b) => a.nearest.distance - b.nearest.distance).slice(0, 4);
for (const item of nearest) {
  console.log(`  最近 ${item.shot} / ${item.nearest.id}: ${item.nearest.distance.toFixed(2)}`);
}
const lowestApproach = [...approachRatios].sort((a, b) =>
  Math.min(a.first, a.last) - Math.min(b.first, b.last)).slice(0, 3);
for (const item of lowestApproach) {
  console.log(`  接近比 ${item.shot}: 首 ${item.first}× / 末 ${item.last}×（最近 ${item.nearest}）`);
}
if (problems.length) process.exitCode = 1;
