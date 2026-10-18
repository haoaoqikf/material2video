/**
 * 太阳系一镜到底的相机路径提案生成器。
 *
 * 只读 `scenes/layout.tsx`，按「站点弧 + 螺旋过场」生成 28 个镜头，并按**全局速度曲线**
 * 在等帧间隔上重新采样控制点：站点慢速绕行、过场两端接住相邻站点速度、hero 到站后落回慢速。
 * 因此相邻镜头的位置、方向与速度都连续，运行时 CameraRig 用 linear 缓动即可。
 *
 * 输出 `outputs/path-proposal.json` 与 `outputs/storyboard.generated.json`；
 * 不直接改 storyboard.json，人工复核报告后再合并。
 *
 * 用法：node examples/solar-system-journey/scripts/generate-paths.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';

const HERE = import.meta.dirname;
const EXAMPLE = path.resolve(HERE, '..');
const REPO = path.resolve(EXAMPLE, '../..');
const WEB = path.join(REPO, 'web');
// esbuild 安装在前端工作区；以 web/package.json 为基准解析，避免依赖当前工作目录。
const requireFromWeb = createRequire(path.join(WEB, 'package.json'));
const {build} = requireFromWeb('esbuild');

const FPS = 60;
const TOTAL = 8100;
const LEAD_IN = 360;
const HOLD = 180;
const TAIL = 669;

// ---------------------------------------------------------------- 输入数据

/** 旁白段与实测 TTS 帧长（来自 outputs/prepared.json；文本与语速不变即命中缓存）。 */
const SEGMENTS = [
  {id: 'sun-line', text: '从太阳出发吧。这颗恒星，照亮了我们的整个旅程。', frames: 309},
  {id: 'mercury-line', text: '第一站，水星。离太阳最近，满身古老的陨坑。', frames: 300},
  {id: 'venus-line', text: '接着是金星。厚厚的云，把这个世界藏了起来。', frames: 285},
  {id: 'earth-line', text: '这一颗，你一定认识。蓝色的地球，是我们的家。', frames: 297},
  {id: 'moon-line', text: '月球，是地球的天然卫星。一路陪伴着我们。', frames: 289},
  {id: 'mars-line', text: '再往外，是火星。红色尘土，给它披上了一件外衣。', frames: 313},
  {id: 'ceres-line', text: '经过谷神星，我们来到稀疏的小行星带。', frames: 225},
  {id: 'jupiter-line', text: '木星到了，太阳系最大的行星。看看它身上，一道道宽阔的云带。', frames: 373},
  {id: 'saturn-line', text: '下一站，土星。先别急着走，看看它慢慢展开的光环。', frames: 339},
  {id: 'uranus-line', text: '这是天王星。一颗几乎侧躺着自转的冰巨星。', frames: 294},
  {id: 'neptune-line', text: '更远处，是海王星。八颗行星中，它离太阳最远。', frames: 316},
  {id: 'pluto-line', text: '冥王星，是一颗矮行星。它身上，还藏着一颗心。', frames: 307},
  {id: 'kuiper-line', text: '这里是柯伊伯带，冰质小天体的家园。', frames: 216},
  {id: 'heliopause-line', text: '再向外，是日球层顶。太阳风，在这里与星际介质相遇。', frames: 356},
  {id: 'oort-line', text: '更远处，是推测中的奥尔特云。太阳，已成一个亮点。', frames: 332},
];

/** 非 LAYOUT 天体的区域锚点：柯伊伯带、日球层顶、奥尔特云。 */
const REGIONS = {
  kuiper: {anchor: [Math.cos(4.78) * 108, 8, Math.sin(4.78) * 108], d: 12},
  heliopause: {anchor: [Math.cos(5.05) * 152, 26, Math.sin(5.05) * 152], d: 14},
  oort: {anchor: [Math.cos(5.30) * 175, 40, Math.sin(5.30) * 175], d: 16},
};

const STATION_ORDER = ['sun', 'mercury', 'venus', 'earth', 'moon', 'mars', 'ceres', 'jupiter',
  'saturn', 'uranus', 'neptune', 'pluto', 'kuiper', 'heliopause', 'oort'];
const STATION = {
  sun: {d: 9, tier: 'major', fov: 44},
  mercury: {d: 2.6, tier: 'minor', fov: 41},
  venus: {d: 3.6, tier: 'minor', fov: 41},
  earth: {d: 4.2, tier: 'hero', fov: 40, transitFrames: 180, tailInHold: 30},
  moon: {d: 1.6, tier: 'minor', fov: 40},
  mars: {d: 3.2, tier: 'minor', fov: 41},
  ceres: {d: 2.0, tier: 'minor', fov: 40},
  jupiter: {d: 12, tier: 'major', fov: 40},
  saturn: {d: 14, tier: 'hero', fov: 40, transitFrames: 180, backlit: true},
  uranus: {d: 6, tier: 'minor', fov: 40},
  neptune: {d: 6, tier: 'minor', fov: 40},
  pluto: {d: 2.4, tier: 'minor', fov: 40},
  kuiper: {d: 12, tier: 'minor', fov: 42},
  heliopause: {d: 14, tier: 'major', fov: 42},
  oort: {d: 16, tier: 'hero', fov: 42, transitFrames: 180},
};
/** 相邻站点之间的过场时长（帧）；被 hero 吸收的过场写 0。 */
const TRANSIT = {
  'sun-mercury': 180, 'mercury-venus': 180, 'venus-earth': 0, 'earth-moon': 150,
  'moon-mars': 180, 'mars-ceres': 180, 'ceres-jupiter': 180, 'jupiter-saturn': 0,
  'saturn-uranus': 180, 'uranus-neptune': 180, 'neptune-pluto': 180,
  'pluto-kuiper': 180, 'kuiper-heliopause': 180, 'heliopause-oort': 0,
};

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

// ---------------------------------------------------------------- 向量工具

const V = (p) => new THREE.Vector3(...p);
const add = (p, q, r, s) => [p[0] + q[0] + r[0] + s[0], p[1] + q[1] + r[1] + s[1],
  p[2] + q[2] + r[2] + s[2]];
const scaled = (v, k) => [v[0] * k, v[1] * k, v[2] * k];
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const curveOf = (points) => new THREE.CatmullRomCurve3(points.map(V), false, 'catmullrom', 0.5);

/** 径向单位向量与切向单位向量（俯视平面）。太阳用 -z 作为 u，使首段过场不切过日面。 */
function frameOf(point) {
  const radius = Math.hypot(point[0], point[2]);
  const u = radius < 1e-6 ? [0, 0, -1] : [point[0] / radius, 0, point[2] / radius];
  return {u, t: [-u[2], 0, u[0]]};
}

/** 站点三点：默认从日面侧绕向切向；逆光变体从外侧绕到内侧，让环张开。 */
function stationArc(anchor, d, backlit = false) {
  const {u, t} = frameOf(anchor);
  if (!backlit) {
    return [
      add(anchor, scaled(u, -0.85 * d), scaled(t, 0.35 * d), [0, 0.20 * d, 0]),
      add(anchor, scaled(u, -0.55 * d), scaled(t, 0.65 * d), [0, 0.30 * d, 0]),
      add(anchor, scaled(u, -0.25 * d), scaled(t, 0.75 * d), [0, 0.35 * d, 0]),
    ];
  }
  return [
    add(anchor, scaled(u, 0.85 * d), scaled(t, 0.20 * d), [0, 0.30 * d, 0]),
    add(anchor, scaled(u, 0.45 * d), scaled(t, 0.65 * d), [0, 0.45 * d, 0]),
    add(anchor, scaled(u, -0.15 * d), scaled(t, 0.80 * d), [0, 0.30 * d, 0]),
  ];
}

/** 两个点之间的对数螺线中间点；短距离用更少的点。 */
function transitShape(from, to, samples) {
  const a0 = Math.atan2(from[2], from[0]);
  const a1 = Math.atan2(to[2], to[0]);
  let da = a1 - a0;
  while (da > Math.PI) da -= 2 * Math.PI;
  while (da < -Math.PI) da += 2 * Math.PI;
  const r0 = Math.max(1e-3, Math.hypot(from[0], from[2]));
  const r1 = Math.max(1e-3, Math.hypot(to[0], to[2]));
  const lift = 0.03 * Math.max(r0, r1);
  const points = [];
  for (let index = 1; index <= samples; index += 1) {
    const k = index / (samples + 1);
    const angle = a0 + da * k;
    const radius = Math.exp(Math.log(r0) + (Math.log(r1) - Math.log(r0)) * k);
    points.push([Math.cos(angle) * radius, from[1] + (to[1] - from[1]) * k + lift * Math.sin(Math.PI * k),
      Math.sin(angle) * radius]);
  }
  return [from, ...points, to];
}

/** 按弧长取路径上的一点。 */
function pointAt(pathPoints, fraction) {
  return curveOf(pathPoints).getPointAt(Math.min(1, Math.max(0, fraction))).toArray();
}

/** 路径的稠密采样与累计弧长。 */
function polyline(shape, samples = 600) {
  const curve = curveOf(shape);
  const points = [];
  const cumulative = [0];
  for (let index = 0; index <= samples; index += 1) {
    const point = curve.getPoint(index / samples).toArray();
    points.push(point);
    if (index) cumulative.push(cumulative[index - 1] + dist(points[index - 1], point));
  }
  return {points, cumulative, length: cumulative[cumulative.length - 1]};
}

function positionAtDistance(line, target) {
  const {points, cumulative} = line;
  let low = 0;
  let high = cumulative.length - 1;
  while (low < high - 1) {
    const middle = (low + high) >> 1;
    if (cumulative[middle] <= target) low = middle;
    else high = middle;
  }
  const span = Math.max(1e-9, cumulative[high] - cumulative[low]);
  const k = Math.min(1, Math.max(0, (target - cumulative[low]) / span));
  return [points[low][0] + (points[high][0] - points[low][0]) * k,
    points[low][1] + (points[high][1] - points[low][1]) * k,
    points[low][2] + (points[high][2] - points[low][2]) * k];
}

/**
 * 按速度曲线在等帧间隔上采样控制点。
 * `parts` 为若干段（每段有自己的形状与时长）；`profile(frame)` 返回该帧的目标速度形状，
 * 之后统一缩放到总弧长，保证终点正好落在路径末端。
 */
function sampleBySpeed(parts, duration, count, profile) {
  const shapes = parts.map(part => ({...polyline(part.shape), duration: part.duration}));
  const points = [];
  const cumulative = [];
  let offset = 0;
  shapes.forEach((shape, index) => {
    shape.points.forEach((point, position) => {
      if (index && position === 0) return; // 相邻子路径共享端点，避免重复控制点
      const previous = points[points.length - 1];
      if (previous) offset += dist(previous, point);
      points.push(point);
      cumulative.push(offset);
    });
  });
  const total = offset;
  const speeds = [];
  for (let frame = 0; frame < duration; frame += 1) speeds.push(Math.max(1e-6, profile(frame)));
  const raw = speeds.reduce((sum, value) => sum + value, 0);
  const scale = total / Math.max(1e-9, raw);
  const distances = [0];
  for (let frame = 0; frame < duration; frame += 1) distances.push(distances[frame] + speeds[frame] * scale);
  const line = {points, cumulative};
  const out = [];
  for (let index = 0; index < count; index += 1) {
    const frame = Math.round((duration * index) / (count - 1));
    out.push(positionAtDistance(line, distances[Math.min(duration, frame)]));
  }
  const endSpeed = speeds[speeds.length - 1] * scale;
  return {path: out, endSpeed};
}

/** 站点/过场的速度形状：两端为 v0/v1，中间按 sin² 隆起（两端导数为 0，控制点间隔不会突然变长）。 */
function humpProfile(duration, length, v0, v1) {
  const ratio = v1 / v0;
  const peak = 2 * (length / (v0 * duration) - (1 + ratio) / 2);
  return (frame) => {
    const x = frame / duration;
    return v0 * ((1 - x) + ratio * x + Math.max(0, peak) * Math.sin(Math.PI * x) ** 2);
  };
}

// ---------------------------------------------------------------- 时间轴

const windows = {};
let cursor = LEAD_IN;
SEGMENTS.forEach((segment, index) => {
  windows[segment.id] = {startFrame: cursor, endFrame: cursor + segment.frames};
  cursor += segment.frames + (index < SEGMENTS.length - 1 ? HOLD : 0);
});
const SPEECH_END = cursor;
const EXPECTED = LEAD_IN + SEGMENTS.reduce((sum, item) => sum + item.frames, 0)
  + (SEGMENTS.length - 1) * HOLD + TAIL;
if (EXPECTED !== TOTAL) throw new Error(`帧预算不闭合：${EXPECTED} != ${TOTAL}`);

// ---------------------------------------------------------------- 站点几何

const anchors = {};
for (const id of STATION_ORDER) anchors[id] = REGIONS[id] ? REGIONS[id].anchor : POSITIONS[id];
const arcs = {};
for (const id of STATION_ORDER) {
  arcs[id] = stationArc(anchors[id], STATION[id].d, Boolean(STATION[id].backlit));
}
const tailEnd = [Math.cos(5.55) * 330, 95, Math.sin(5.55) * 330];
const tailApproach = [Math.cos(5.42) * 232, 60, Math.sin(5.42) * 232];
const nextArrival = (id) => {
  const index = STATION_ORDER.indexOf(id);
  return index < STATION_ORDER.length - 1 ? arcs[STATION_ORDER[index + 1]][0] : tailApproach;
};

/** 站点离开点：沿「本站 C → 下一站 A」的螺线最多走 2 个单位，让出站方向与过场同向。 */
const departures = {};
for (const id of STATION_ORDER) {
  const target = nextArrival(id);
  const from = arcs[id][2];
  const route = transitShape(from, target, dist(from, target) < 10 ? 1 : 2);
  const fraction = Math.min(0.25, 2.0 / Math.max(1e-6, polyline(route, 120).length));
  departures[id] = pointAt(route, fraction);
}

// ---------------------------------------------------------------- 站点时长与速度

/** 每个站点的「站点阶段」时长：hero 扣除吸收的前置过场，其余等于旁白段。 */
const stationPlan = {};
for (let index = 0; index < STATION_ORDER.length; index += 1) {
  const id = STATION_ORDER[index];
  const config = STATION[id];
  const window = windows[SEGMENTS[index].id];
  const absorbed = index > 0 && TRANSIT[`${STATION_ORDER[index - 1]}-${id}`] === 0;
  const start = index === 0 ? LEAD_IN : (absorbed ? windows[SEGMENTS[index - 1].id].endFrame
    : window.startFrame);
  const end = window.endFrame + (config.tailInHold ?? 0);
  const stationShape = [...arcs[id], departures[id]];
  const stationLength = polyline(stationShape).length;
  let stationDuration;
  let transitDuration = 0;
  if (absorbed) {
    transitDuration = window.startFrame - start;
    stationDuration = end - window.startFrame;
  } else {
    stationDuration = end - start;
  }
  const speed = stationLength / stationDuration;
  stationPlan[id] = {index, start, end, stationShape, stationLength, stationDuration,
    transitDuration, speed, absorbed, segment: SEGMENTS[index].id};
}

// ---------------------------------------------------------------- 镜头生成

const post = {bloom: 0.35, dof: 0.08, grain: 0.012, vignette: 0.16,
  chromaticAberration: 0.04, lut: 'deep-space'};
const focusOf = (id) => (REGIONS[id] ? 'sun' : id);
const distanceOf = (id) => (REGIONS[id] ? REGIONS[id].d : STATION[id].d);
const shots = [];
const push = (shot) => shots.push(shot);
const nameOf = (id) => (id === 'earth' ? 'earth-hero' : id === 'saturn' ? 'saturn-hero'
  : id === 'oort' ? 'oort-hero' : `${id}-station`);

// 开场：从系统上方连续俯冲到太阳站 A 点。
const openShape = [
  [0, 380, 120], [0, 330, 118], [15, 260, 100], [35, 190, 65],
  [30, 120, 35], [12, 60, 20], [5, 28, 14], arcs.sun[0],
];
const openLine = polyline(openShape);
const sunSpeed = stationPlan.sun.speed;
// 最后 1.5 秒匀速贴近日面，避免最后一个控制点间隔仍带着俯冲速度。
const openApproach = 90;
const openHumpFrames = LEAD_IN - openApproach;
const openHump = humpProfile(openHumpFrames,
  Math.max(1e-3, openLine.length - sunSpeed * openApproach), 0.4, sunSpeed);
const open = sampleBySpeed([{shape: openShape, duration: LEAD_IN}], LEAD_IN, 14,
  frame => (frame >= openHumpFrames ? sunSpeed : openHump(frame)));
push({
  id: 'aerial-dive', target: 'sun', tier: 'minor', startFrame: 0, endFrame: LEAD_IN,
  camera: {path: open.path, fov: 55, easing: 'linear'},
  focus: {target: 'sun', distance: 40},
  note: '从太阳系上方连续俯冲到太阳，无切换。',
});

for (let index = 0; index < STATION_ORDER.length; index += 1) {
  const id = STATION_ORDER[index];
  const plan = stationPlan[id];
  const config = STATION[id];
  const previous = index ? STATION_ORDER[index - 1] : null;
  const parts = [];
  let vStart = plan.speed;
  let profile;
  if (plan.absorbed) {
    const from = departures[previous];
    const route = transitShape(from, arcs[id][0], dist(from, arcs[id][0]) < 10 ? 1 : 2);
    const length = polyline(route).length;
    const v0 = stationPlan[previous].speed;
    const ratio = plan.speed / v0;
    const peak = 2 * (length / (v0 * plan.transitDuration) - (1 + ratio) / 2);
    profile = (frame) => {
      if (frame >= plan.transitDuration) return plan.speed;
      const x = frame / plan.transitDuration;
      return v0 * ((1 - x) + ratio * x + Math.max(0, peak) * Math.sin(Math.PI * x) ** 2);
    };
    parts.push({shape: route, duration: plan.transitDuration});
    parts.push({shape: plan.stationShape, duration: plan.stationDuration});
  } else {
    parts.push({shape: plan.stationShape, duration: plan.stationDuration});
    const length = plan.stationLength;
    profile = () => length / plan.stationDuration;
  }
  const count = config.tier === 'hero' ? 16 : 8;
  const sampled = sampleBySpeed(parts, plan.end - plan.start, count, profile);
  push({
    id: nameOf(id), target: id, tier: config.tier, segment: plan.segment,
    startFrame: plan.start, endFrame: plan.end,
    camera: {path: sampled.path, fov: config.fov, easing: 'linear'},
    focus: {target: focusOf(id), distance: distanceOf(id)},
    post,
    note: config.tier === 'hero' ? '站点主体镜头；吸收前置过场并保持连续速度。' : '站点连续镜头。',
  });

  // 独立过场：两端速度分别接住相邻站点。
  const next = STATION_ORDER[index + 1];
  const frames = next ? TRANSIT[`${id}-${next}`] : 0;
  if (next && frames > 0) {
    const from = departures[id];
    const to = arcs[next][0];
    const route = transitShape(from, to, dist(from, to) < 10 ? 1 : 2);
    const length = polyline(route).length;
    const v0 = plan.speed;
    const v1 = stationPlan[next].speed;
    push({
      id: `${id}-to-${next}`, target: next, tier: 'minor',
      startFrame: plan.end, endFrame: plan.end + frames,
      camera: {path: sampleBySpeed([{shape: route, duration: frames}], frames, 12,
        humpProfile(frames, length, v0, v1)).path, fov: 42, easing: 'linear'},
      focus: {target: focusOf(next), distance: 40},
      post,
      note: '过场：焦点已对准下一站，镜头边界无朝向与速度跳变。',
    });
  }
}

// 收尾：从奥尔特云站离开点继续向外拉远。
const tailFrom = departures.oort;
const tailRoute = transitShape(tailFrom, tailEnd, 2);
const tailShape = [tailRoute[0], pointAt(tailRoute, 0.35), pointAt(tailRoute, 0.68), tailEnd];
const tailLength = polyline(tailShape).length;
const oortSpeed = stationPlan.oort.speed;
push({
  id: 'oort-tail', target: 'oort', tier: 'minor',
  startFrame: SPEECH_END, endFrame: TOTAL,
  camera: {path: sampleBySpeed([{shape: tailShape, duration: TAIL}], TAIL, 12,
    humpProfile(TAIL, tailLength, oortSpeed, oortSpeed * 1.15)).path, fov: 42, easing: 'linear'},
  focus: {target: 'sun', distance: 600},
  post,
  note: '收尾：继续向外，太阳成为亮点。',
});

// ---------------------------------------------------------------- 检查

const problems = [];
const minDistances = [];
const obstacles = Object.entries(LAYOUT).map(([id, item]) => ({id, center: POSITIONS[id], radius: item.radius}));
obstacles.find(item => item.id === 'saturn').radius = 2.27 * LAYOUT.saturn.radius;
obstacles.push({id: 'sun-clearance', center: [0, 0, 0], radius: LAYOUT.sun.radius * 1.5});

for (const shot of shots) {
  const curve = curveOf(shot.camera.path);
  const samples = 240;
  let nearest = {id: null, distance: Infinity};
  for (let index = 0; index <= samples; index += 1) {
    const point = curve.getPoint(index / samples).toArray();
    if (Math.hypot(...point) > 900) problems.push(`${shot.id} 越出星空壳：${Math.hypot(...point).toFixed(1)}`);
    for (const obstacle of obstacles) {
      const gap = dist(point, obstacle.center) - obstacle.radius;
      if (gap < nearest.distance) nearest = {id: obstacle.id, distance: gap};
      if (gap < 0.4) problems.push(`${shot.id} 靠近 ${obstacle.id}：余量 ${gap.toFixed(2)}`);
    }
  }
  minDistances.push({shot: shot.id, nearest});
}

const shotPosition = (shot, frame) => {
  const span = Math.max(1, shot.endFrame - shot.startFrame);
  const raw = (frame - shot.startFrame) / span;
  return curveOf(shot.camera.path).getPoint(Math.min(1, Math.max(0, raw))).toArray();
};

for (let index = 1; index < shots.length; index += 1) {
  const previous = shots[index - 1];
  const current = shots[index];
  const gap = dist(previous.camera.path[previous.camera.path.length - 1], current.camera.path[0]);
  if (gap > 1e-6) problems.push(`${previous.id} → ${current.id} 位置不连续：${gap.toFixed(3)}`);
  if (previous.endFrame !== current.startFrame) problems.push(`${previous.id} → ${current.id} 时间窗不相接`);
}

const speeds = [];
for (let index = 1; index < shots.length; index += 1) {
  const previous = shots[index - 1];
  const current = shots[index];
  const vBefore = dist(shotPosition(previous, current.startFrame - 5),
    shotPosition(previous, current.startFrame - 1)) / 4;
  const vAfter = dist(shotPosition(current, current.startFrame + 1),
    shotPosition(current, current.startFrame + 5)) / 4;
  const ratio = Math.max(vBefore, vAfter) / Math.max(1e-6, Math.min(vBefore, vAfter));
  speeds.push({boundary: `${previous.id} -> ${current.id}`, before: Number(vBefore.toFixed(4)),
    after: Number(vAfter.toFixed(4)), ratio: Number(ratio.toFixed(2))});
  if (ratio > 1.8) problems.push(`${previous.id} → ${current.id} 速度突变 ×${ratio.toFixed(2)}`);
}

if (shots[0].startFrame !== 0 || shots[shots.length - 1].endFrame !== TOTAL) {
  problems.push('镜头没有覆盖 0–8100');
}

// ---------------------------------------------------------------- 分镜

const storyboard = {
  version: 8,
  schemaVersion: 8,
  fps: FPS,
  width: 1920,
  height: 1080,
  title: '太阳系之旅：一次连续的旅程',
  input: {kind: 'article'},
  targetSeconds: 135,
  scenes: [{
    id: 'solar-journey',
    template: 'code',
    content: {
      title: '从太阳到奥尔特云',
      entry: 'scenes/journey.tsx',
      props: {
        look: {profile: 'deep-space-cinematic', lut: 'deep-space', bloom: 0.7, dof: 0.45,
          grain: 0.035, vignette: 0.22, exposure: {ev: -0.2, mode: 'look'},
          motion: {subframes: 1, supersample: 1}},
        shots,
      },
    },
    durationFrames: TOTAL,
    transition: 'cut',
    leadInFrames: LEAD_IN,
    tailFrames: TAIL,
    readingHoldFrames: 0,
    narrationSegments: SEGMENTS.map((segment, index) => ({
      id: segment.id, text: segment.text,
      ...(index < SEGMENTS.length - 1 ? {holdFrames: HOLD} : {}),
    })),
  }],
  soundtrack: {
    music: {sourceRef: 'assets/sound/score.wav', gainDb: -2, loop: false,
      fadeInMs: 1800, fadeOutMs: 3500},
    effects: [
      {sourceRef: 'assets/sound/shimmer.wav', sceneId: 'solar-journey', segmentId: 'saturn-line',
        offsetMs: 2000, gainDb: -16},
      {sourceRef: 'assets/sound/whoosh.wav', sceneId: 'solar-journey', segmentId: 'heliopause-line',
        offsetMs: 600, gainDb: -20},
    ],
  },
};

const report = {
  windows,
  shots: shots.map(item => ({id: item.id, start: item.startFrame, end: item.endFrame,
    tier: item.tier, segment: item.segment ?? null, target: item.target,
    points: item.camera.path.length, length: Number(polyline(item.camera.path).length.toFixed(2)),
    endPoint: item.camera.path[item.camera.path.length - 1].map(value => Number(value.toFixed(3)))})),
  minDistances,
  speeds,
  problems,
};
const outDir = path.join(EXAMPLE, 'outputs');
fs.mkdirSync(outDir, {recursive: true});
fs.writeFileSync(path.join(outDir, 'path-proposal.json'),
  JSON.stringify({report, storyboard}, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(outDir, 'storyboard.generated.json'),
  JSON.stringify(storyboard, null, 2) + '\n', 'utf8');

console.log(`镜头 ${shots.length} 个，覆盖 ${shots[0].startFrame}–${shots[shots.length - 1].endFrame}`);
console.log(`问题 ${problems.length} 项`);
for (const problem of problems.slice(0, 20)) console.log('  ! ' + problem);
console.log('速度突变最大的 6 个边界：');
for (const speed of [...speeds].sort((a, b) => b.ratio - a.ratio).slice(0, 6)) {
  console.log(`  ${speed.boundary}: ${speed.before} → ${speed.after} (×${speed.ratio})`);
}
const nearest = [...minDistances].sort((a, b) => a.nearest.distance - b.nearest.distance).slice(0, 4);
for (const item of nearest) console.log(`  最近 ${item.shot} / ${item.nearest.id}: ${item.nearest.distance.toFixed(2)}`);
if (problems.length) process.exitCode = 1;
