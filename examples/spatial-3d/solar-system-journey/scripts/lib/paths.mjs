/**
 * 太阳系一镜到底的相机路径几何、速度与时间窗纯计算。
 *
 * 为每个站点生成「远入点 → 接近 → 近天体绕行 → 拉远 → 远出点」，
 * 站点之间用抬升到黄道面上方的空间弧连接。控制点按**分段速度曲线**（sin²）在等帧间隔上采样，
 * 原始路径相接；实际运动由 flight.ts 跨边界求值，须另查全过程。
 *
 * 本模块不读写文件、不解析 CLI：入口 `scripts/generate-paths.mjs` 打包 `scenes/layout.tsx`
 * 后把 THREE/LAYOUT/POSITIONS 交给 `createProposal`，再负责写出产物与 `--merge` 合并分镜。
 */

const FPS = 60;
const LEAD_IN = 360;
const TAIL = 759;
const ENTRY = 60;          // 旁白开始前的到站接近时间：1秒
const POST_SPEECH = 45;    // 普通站旁白后的离站衔接：0.75秒
const HERO_POST_SPEECH = 180; // hero旁白后保留3秒观察，维持8秒以上站点镜头
const HERO_STATIONS = new Set(['earth', 'saturn', 'oort']);
const MIN_TRANSIT = 210;   // 至少保留3.5秒连续空间移动；朝向插值覆盖到站前0.5秒
const MAX_TRANSIT = 300;   // 长距离移动最多5秒，按路径长度单独计算
const TRANSIT_SPEED = 12;  // 压缩世界单位/秒；只用于生成初始预算，须经动态粗预演复核

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
  {id: 'heliopause-line', text: '再向外，是日球层顶。太阳风，在这里与星际介质相遇。', frames: 359},
  {id: 'oort-line', text: '更远处，是推测中的奥尔特云。太阳，已成一个亮点。', frames: 332},
];

/** 非 LAYOUT 天体的区域锚点：柯伊伯带、日球层顶、奥尔特云。 */
const REGIONS = {
  kuiper: {anchor: [Math.cos(4.78) * 162, 12, Math.sin(4.78) * 162], d: 18},
  heliopause: {anchor: [Math.cos(5.05) * 228, 39, Math.sin(5.05) * 228], d: 21},
  oort: {anchor: [Math.cos(5.30) * 262.5, 60, Math.sin(5.30) * 262.5], d: 24},
};
/** 外层结构的外缘半径；与场景里的 ParticleBelt/OortCloud 参数一致，诊断由此读取。 */
const STRUCTURE_SIZE = {kuiper: 159, heliopause: 198, oort: 278};

const STATION_ORDER = ['sun', 'mercury', 'venus', 'earth', 'moon', 'mars', 'ceres', 'jupiter',
  'saturn', 'uranus', 'neptune', 'pluto', 'kuiper', 'heliopause', 'oort'];
// 正式相机统一使用 44 度 FOV（开场 55 度平缓收束）；站点不单独声明 FOV，避免死配置。
const STATION = {
  sun: {d: 9, tier: 'major'},
  mercury: {d: 2.6, tier: 'minor'},
  venus: {d: 3.6, tier: 'minor'},
  earth: {d: 4.2, tier: 'hero'},
  moon: {d: 1.6, tier: 'minor'},
  mars: {d: 3.2, tier: 'minor'},
  ceres: {d: 2.0, tier: 'minor'},
  jupiter: {d: 12, tier: 'major'},
  saturn: {d: 14, tier: 'hero', backlit: true},
  uranus: {d: 6, tier: 'minor'},
  neptune: {d: 6, tier: 'minor'},
  pluto: {d: 2.4, tier: 'minor'},
  kuiper: {d: 12, tier: 'minor'},
  heliopause: {d: 14, tier: 'major'},
  oort: {d: 16, tier: 'hero'},
};

// ---------------------------------------------------------------- 向量工具

// 入口从 esbuild 打包结果注入；本模块不自行解析 three，避免依赖仓库根 node_modules。
let THREE = null;

const UP = [0, 1, 0];
const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
const addv = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const subv = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const scale = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0]];
const norm = (a) => Math.hypot(a[0], a[1], a[2]);
const normalize = (a) => {
  const length = norm(a);
  return length < 1e-9 ? [0, 0, 1] : [a[0] / length, a[1] / length, a[2] / length];
};
const lerp3 = (a, b, k) => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k,
  a[2] + (b[2] - a[2]) * k];
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const V = (point) => new THREE.Vector3(...point);
const curveOf = (points) => new THREE.CatmullRomCurve3(points.map(V), false, 'catmullrom', 0.5);

/** 径向单位向量与切向单位向量（俯视平面）。太阳用 -z 作为 u。 */
function frameOf(point) {
  const radius = Math.hypot(point[0], point[2]);
  const u = radius < 1e-6 ? [0, 0, -1] : [point[0] / radius, 0, point[2] / radius];
  return {u, t: [-u[2], 0, u[0]]};
}

/** 站点近天体弧：默认从日面侧绕向切向；土星逆光从外侧绕到内侧，让环张开。 */
function stationArc(anchor, d, backlit = false) {
  const {u, t} = frameOf(anchor);
  const at = (radial, tangent, height) => [anchor[0] + d * (radial * u[0] + tangent * t[0]),
    anchor[1] + height * d, anchor[2] + d * (radial * u[2] + tangent * t[2])];
  if (!backlit) {
    return [at(-0.75, -0.45, 0.30), at(-0.85, 0.0, 0.30), at(-0.65, 0.55, 0.30)];
  }
  return [at(0.85, 0.20, 0.30), at(0.45, 0.65, 0.45), at(-0.15, 0.80, 0.30)];
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
  const k = clamp((target - cumulative[low]) / span, 0, 1);
  return lerp3(points[low], points[high], k);
}

const tangentStart = (line) => normalize(subv(line.points[1], line.points[0]));
const tangentEnd = (line) => normalize(subv(line.points[line.points.length - 1],
  line.points[line.points.length - 2]));

/**
 * 空间过场：显式顶点 + Catmull-Rom。端点本身已抬高，过场再抬 0.12L，并向太阳外侧 bow。
 * 近垂直过场（地球→月球）走 bow=0 分支，避免叉积累降。
 */
function spaceArc(from, to, {liftScale = 0.12, bowScale = 0.08} = {}) {
  const chord = subv(to, from);
  const length = norm(chord);
  const horizontal = Math.hypot(chord[0], chord[2]);
  let normal = [0, 0, 0];
  let bow = 0;
  if (horizontal > 0.25 * length) {
    normal = normalize(cross(UP, [chord[0], 0, chord[2]]));
    const middle = [(from[0] + to[0]) / 2, 0, (from[2] + to[2]) / 2];
    if (dot(normal, middle) < 0) normal = scale(normal, -1);
    bow = bowScale * length;
  }
  const radiusFrom = Math.hypot(from[0], from[2]);
  const radiusTo = Math.hypot(to[0], to[2]);
  const lift = clamp(liftScale * length, 1.0, 0.35 * Math.min(radiusFrom, radiusTo));
  const apex = [(from[0] + to[0]) / 2 + bow * normal[0],
    (from[1] + to[1]) / 2 + lift,
    (from[2] + to[2]) / 2 + bow * normal[2]];
  return [from, lerp3(from, apex, 1 / 3), lerp3(from, apex, 2 / 3), apex,
    lerp3(apex, to, 1 / 3), lerp3(apex, to, 2 / 3), to];
}

/**
 * 分段采样：每个 phase 用闭式积分 D(f) 精确映射到自己的弧长，端点速度保持 v0/v1。
 * 速度形状在整个阶段展开 sin² 隆起，不把位移压在中间40%；
 * 实际相机另用跨镜头时间滤波平滑位置；必须检查全过程而非只看端点。
 * 控制点在全局等帧间隔上取，运行时 getPoint 的均匀参数化因此与速度曲线一致。
 */
const FLAT = 0;

function bumpShape(frame, frames) {
  const x = frame / frames;
  if (x <= FLAT || x >= 1 - FLAT) return 0;
  return Math.sin(Math.PI * (x - FLAT) / (1 - 2 * FLAT)) ** 2;
}

function bumpIntegral(frame, frames) {
  const start = FLAT * frames;
  const end = (1 - FLAT) * frames;
  if (frame <= start) return 0;
  if (frame >= end) return frames * (0.5 - FLAT);
  const u = (frame / frames - FLAT) / (1 - 2 * FLAT);
  return frames * (1 - 2 * FLAT)
    * (u / 2 - Math.sin(2 * Math.PI * u) / (4 * Math.PI));
}

function sampleShot(phases, stride = 8) {
  const totalFrames = phases.reduce((sum, phase) => sum + phase.frames, 0);
  const lines = phases.map(phase => {
    const line = polyline(phase.shape);
    const frames = phase.frames;
    const v0 = phase.v0;
    const v1 = phase.v1;
    const peak = (line.length / frames - (v0 + v1) / 2) / (0.5 - FLAT);
    if (peak < -1e-6) {
      throw new Error(`phase ${phase.name} 速度不可行：P=${peak.toFixed(4)}，需要降低端点速度`);
    }
    const distances = new Array(frames + 1);
    distances[0] = 0;
    for (let frame = 1; frame <= frames; frame += 1) {
      distances[frame] = v0 * frame + (v1 - v0) * frame * frame / (2 * frames)
        + peak * bumpIntegral(frame, frames);
    }
    let minSpeed = Infinity;
    let maxSpeed = -Infinity;
    for (let frame = 0; frame <= frames; frame += 1) {
      const speed = v0 + (v1 - v0) * frame / frames + peak * bumpShape(frame, frames);
      minSpeed = Math.min(minSpeed, speed);
      maxSpeed = Math.max(maxSpeed, speed);
    }
    return {...line, name: phase.name, frames, v0, v1, peak, distances,
      minSpeed, maxSpeed, startFrame: 0, distanceOffset: 0};
  });
  let frameCursor = 0;
  let distanceCursor = 0;
  for (const line of lines) {
    line.startFrame = frameCursor;
    line.distanceOffset = distanceCursor;
    frameCursor += line.frames;
    distanceCursor += line.length;
  }
  const points = [];
  const cumulative = [];
  let offset = 0;
  lines.forEach((line, index) => {
    line.points.forEach((point, position) => {
      if (index && position === 0) return; // 相邻 phase 共享端点，避免重复控制点
      const previous = points[points.length - 1];
      if (previous) offset += dist(previous, point);
      points.push(point);
      cumulative.push(offset);
    });
  });
  const globalLine = {points, cumulative};
  const distanceAt = (frame) => {
    const clamped = clamp(frame, 0, totalFrames);
    let index = 0;
    while (index < lines.length - 1
      && clamped >= lines[index].startFrame + lines[index].frames) index += 1;
    const line = lines[index];
    const local = clamp(clamped - line.startFrame, 0, line.frames);
    const low = Math.floor(local);
    const high = Math.min(line.frames, low + 1);
    const k = local - low;
    const distance = line.distances[low] + (line.distances[high] - line.distances[low]) * k;
    return line.distanceOffset + clamp(distance, 0, line.length);
  };
  const count = Math.min(64, Math.max(2, Math.ceil(totalFrames / stride) + 1));
  const path = [];
  for (let index = 0; index < count; index += 1) {
    path.push(positionAtDistance(globalLine, distanceAt((totalFrames * index) / (count - 1))));
  }
  return {path, lines, totalFrames};
}

/** 开场的单段速度形状：两端为 v0/v1，中间按 sin² 隆起。 */
function humpProfile(duration, length, v0, v1) {
  const ratio = v1 / v0;
  const peak = 2 * (length / (v0 * duration) - (1 + ratio) / 2);
  return (frame) => {
    const x = frame / duration;
    return v0 * ((1 - x) + ratio * x + Math.max(0, peak) * Math.sin(Math.PI * x) ** 2);
  };
}

/** 按单一速度曲线采样（开场用）。 */
function sampleBySpeed(shape, duration, count, profile) {
  const line = polyline(shape);
  const speeds = [];
  for (let frame = 0; frame < duration; frame += 1) speeds.push(Math.max(1e-6, profile(frame)));
  const raw = speeds.reduce((sum, value) => sum + value, 0);
  const scaleFactor = line.length / Math.max(1e-9, raw);
  const distances = [0];
  for (let frame = 0; frame < duration; frame += 1) {
    distances.push(distances[frame] + speeds[frame] * scaleFactor);
  }
  const out = [];
  for (let index = 0; index < count; index += 1) {
    const frame = Math.round((duration * index) / (count - 1));
    out.push(positionAtDistance(line, distances[Math.min(duration, frame)]));
  }
  return out;
}

// ---------------------------------------------------------------- 镜头常量

const post = {bloom: 0.35, dof: 0.08, grain: 0.012, vignette: 0.16,
  chromaticAberration: 0.04, lut: 'deep-space'};
const focusOf = (id) => (REGIONS[id] ? 'sun' : id);
const distanceOf = (id) => (REGIONS[id] ? REGIONS[id].d : STATION[id].d);
const nameOf = (id) => (id === 'earth' ? 'earth-hero' : id === 'saturn' ? 'saturn-hero'
  : id === 'oort' ? 'oort-hero' : `${id}-station`);

function transitFramesFor(length) {
  const estimated = Math.round((length / TRANSIT_SPEED * FPS) / 30) * 30;
  return clamp(estimated, MIN_TRANSIT, MAX_TRANSIT);
}

/**
 * 生成完整路径提案：几何 → 时间与阶段 → 镜头 → 检查 → 分镜与报告。
 *
 * @param {{THREE: object, LAYOUT: object, POSITIONS: object}} input 由入口从 scenes/layout.tsx 打包取得。
 * @returns {{shots: Array, storyboard: object, report: object, problems: string[],
 *   boundarySpeedMax: number, minDistances: Array, speeds: Array, approachRatios: Array}}
 */
export function createProposal({THREE: three, LAYOUT, POSITIONS}) {
  THREE = three;

  // -------------------------------------------------------------- 几何

  const problems = [];
  const anchors = {};
  for (const id of STATION_ORDER) anchors[id] = REGIONS[id] ? REGIONS[id].anchor : POSITIONS[id];

  /** 与 test_solar_system_camera.py 完全一致的障碍半径：太阳×1.5、土星×2.27、其余×1.05。 */
  const OBSTACLES = Object.entries(LAYOUT).map(([id, item]) => ({
    id, center: POSITIONS[id],
    radius: id === 'sun' ? item.radius * 1.5
      : id === 'saturn' ? item.radius * 2.27 : item.radius * 1.05,
  }));

  const arcs = {};
  for (const id of STATION_ORDER) {
    arcs[id] = stationArc(anchors[id], STATION[id].d, Boolean(STATION[id].backlit));
  }
  // 土星环的展开依赖旧版验证过的 4 点弧：它跨越环平面并从低处抬升。
  // 这些是相对土星的旧版世界偏移；环的朝向由世界坐标固定，与轨道方位角无关。
  arcs.saturn = [[8.334, 0.396, -15.195], [11.420, 0.792, -10.745],
    [15.670, 2.624, 0.474], [10.742, 4.455, 11.411]].reverse().map(offset => addv(anchors.saturn, offset));
  // 太阳保持已核对的俯冲入口；月球抬高以避开近邻地球。
  arcs.sun = [[3.15,1.8,7.65],[5.85,2.7,4.95],[6.75,3.15,2.25]];
  arcs.moon = arcs.moon.map(point => [point[0], point[1] + 0.8, point[2]]);
  const tailEnd = [Math.cos(5.55) * 495, 142.5, Math.sin(5.55) * 495];

  const F_in = {};
  const F_out = {};
  // 远点沿近景视角同侧延伸，避免越过天顶时相机的上方向发生翻转。
  for (const id of STATION_ORDER) {
    if (id === 'sun') continue;
    const anchor = anchors[id], d = STATION[id].d;
    F_in[id] = addv(anchor, scale(subv(arcs[id][0], anchor), 1.8));
    F_in[id][1] += 0.20 * d;
    F_out[id] = addv(anchor, scale(subv(arcs[id].at(-1), anchor), 1.9));
    F_out[id][1] += 0.24 * d;
  }
  const mercuryPos = POSITIONS.mercury;
  F_out.sun = scale(normalize([mercuryPos[0],
    0.9 * Math.hypot(mercuryPos[0], mercuryPos[2]), mercuryPos[2]]), 12.5);

  const transitShapes = [];
  for (let index = 0; index < STATION_ORDER.length - 1; index += 1) {
    transitShapes.push(spaceArc(F_out[STATION_ORDER[index]],
      F_in[STATION_ORDER[index + 1]]));
  }
  const tailShape = spaceArc(F_out.oort, tailEnd, {bowScale: 0.05});

  // 每段过场时间由其几何路径长度得出；头尾衔接时间独立计算，不再用统一9秒预算。
  const transitFrames = transitShapes.map(shape => transitFramesFor(polyline(shape).length));
  const holdFrames = transitFrames.map((frames, index) =>
    (HERO_STATIONS.has(STATION_ORDER[index]) ? HERO_POST_SPEECH : POST_SPEECH) + frames + ENTRY);
  const windows = {};
  let cursor = LEAD_IN;
  SEGMENTS.forEach((segment, index) => {
    windows[segment.id] = {startFrame: cursor, endFrame: cursor + segment.frames};
    cursor += segment.frames + (index < SEGMENTS.length - 1 ? holdFrames[index] : 0);
  });
  const totalFrames = cursor + TAIL;
  if (totalFrames > 600 * FPS) throw new Error(`成片超出600秒：${totalFrames / FPS}`);

  // M 点用实际过场首末切线反推，保证站点出口/入口与过场同向。
  const M_in = {};
  const M_out = {};
  for (let index = 0; index < STATION_ORDER.length; index += 1) {
    const id = STATION_ORDER[index];
    const A = arcs[id][0];
    const C = arcs[id][arcs[id].length - 1];
    if (index > 0) {
      const incoming = polyline(transitShapes[index - 1]);
      const direction = tangentEnd(incoming);
      const segment = subv(A, F_in[id]);
      const tau = clamp(0.40 * dot(segment, direction), 0.25 * norm(segment),
        0.60 * norm(segment));
      M_in[id] = addv(F_in[id], scale(direction, tau));
    }
    const outgoing = index < STATION_ORDER.length - 1 ? polyline(transitShapes[index])
      : polyline(tailShape);
    const direction = tangentStart(outgoing);
    const segment = subv(F_out[id], C);
    const tau = clamp(0.40 * dot(segment, direction), 0.25 * norm(segment),
      0.60 * norm(segment));
    M_out[id] = subv(F_out[id], scale(direction, tau));
  }

  // -------------------------------------------------------------- 时间与阶段

  const plans = STATION_ORDER.map((id, index) => {
    const window = windows[SEGMENTS[index].id];
    const speechFrames = window.endFrame - window.startFrame;
    const exitFrames = 120;
    const postSpeechFrames = HERO_STATIONS.has(id) ? HERO_POST_SPEECH : POST_SPEECH;
    return {id, index, window, speechFrames, exitFrames, postSpeechFrames,
      tier: STATION[id].tier, segment: SEGMENTS[index].id};
  });

  for (const plan of plans) {
    plan.start = plan.id === 'sun' ? plan.window.startFrame
      : plan.window.startFrame - ENTRY;
    plan.end = plan.window.endFrame + plan.postSpeechFrames;
    const stationFrames = plan.end - plan.start;
    const entry = plan.id === 'sun' ? 0 : ENTRY;
    plan.orbitFrames = stationFrames - entry - plan.exitFrames;
    if (plan.orbitFrames < 20) throw new Error(`${plan.id} 绕行帧数不足：${plan.orbitFrames}`);
  }

  const gaps = [];
  for (let index = 0; index < plans.length - 1; index += 1) {
    const previous = plans[index];
    const next = plans[index + 1];
    gaps.push({index, previous, next,
      frames: next.start - previous.end,
      transitFrames: transitFrames[index],
      shape: transitShapes[index]});
  }

  for (const plan of plans) {
    const id = plan.id;
    const A = arcs[id][0];
    const C = arcs[id][arcs[id].length - 1];
    const phases = [];

    if (id !== 'sun') phases.push({name: 'entry', shape: [F_in[id], M_in[id], A],
      frames: ENTRY});
    phases.push({name: 'orbit', shape: arcs[id], frames: plan.orbitFrames});
    phases.push({name: 'exit', shape: [C, M_out[id], F_out[id]], frames: plan.exitFrames});
    plan.phases = phases;
    const orbit = phases.find(phase => phase.name === 'orbit');
    const entry = phases.find(phase => phase.name === 'entry');
    const exit = phases.find(phase => phase.name === 'exit');
    plan.orbitLength = polyline(orbit.shape).length;
    plan.entryLength = entry ? polyline(entry.shape).length : 0;
    plan.exitLength = polyline(exit.shape).length;
    plan.S = plan.orbitLength / plan.orbitFrames;
  }

  for (const gap of gaps) {
    if (gap.frames !== gap.transitFrames) throw new Error('段间视觉预算与路径不符');
    gap.length = polyline(gap.shape).length;
    gap.V = gap.length / gap.frames;
  }
  const tailLength = polyline(tailShape).length;
  const tailV = tailLength / (TAIL - 90);

  // 端点速度：过场两端 clamp 到平均速度的 0.35–0.80，再用入口/出口长度保证积分可行。
  for (let index = 0; index < plans.length; index += 1) {
    const plan = plans[index];
    if (index > 0) {
      const gap = gaps[index - 1];
      plan.vIn = Math.min(clamp(1.30 * plan.S, 0.35 * gap.V, 0.80 * gap.V),
        2 * plan.entryLength / ENTRY - plan.S);
      if (!(plan.vIn > 0)) problems.push(`${plan.id} 入口速度不可行：${plan.vIn.toFixed(4)}`);
    }
    const gap = index < gaps.length ? gaps[index] : null;
    const average = gap ? gap.V : tailV;
    plan.vOut = Math.min(clamp(1.25 * plan.S, 0.35 * average, 0.80 * average),
      2 * plan.exitLength / plan.exitFrames - plan.S);
    if (!(plan.vOut > 0)) problems.push(`${plan.id} 出口速度不可行：${plan.vOut.toFixed(4)}`);
  }
  // 入场速度必须在过场平均速度的可行范围内；用最终 vOut/vIn 重建过场 profile。

  for (const plan of plans) {
    for (const phase of plan.phases) {
      if (phase.name === 'entry') {
        phase.v0 = plan.vIn;
        phase.v1 = plan.S;
      } else if (phase.name === 'orbit') {
        phase.v0 = plan.S;
        phase.v1 = plan.S;
      } else {
        phase.v0 = plan.S;
        phase.v1 = plan.vOut;
      }
    }
  }

  // -------------------------------------------------------------- 镜头生成

  const shots = [];
  const stationShots = [];
  const transitShots = [];
  const phaseStats = {};
  const push = (shot) => shots.push(shot);

  // 开场：从系统上方连续俯冲到太阳站 A 点。
  const openShape = [
    [0, 380, 120], [0, 330, 118], [15, 260, 100], [35, 190, 65],
    [30, 120, 35], [12, 60, 20], [5, 28, 14], arcs.sun[0],
  ];
  const openLine = polyline(openShape);
  const sunSpeed = plans[0].S;
  const openHumpFrames = 270;
  const openHump = humpProfile(openHumpFrames,
    Math.max(1e-3, openLine.length - sunSpeed * 90), 0.4, sunSpeed);
  push({
    id: 'aerial-dive', target: 'sun', tier: 'minor', startFrame: 0, endFrame: LEAD_IN,
    camera: {path: sampleBySpeed(openShape, LEAD_IN, 14,
      frame => (frame >= openHumpFrames ? sunSpeed : openHump(frame))), fov: 55,
      easing: 'linear'},
    focus: {target: 'sun', distance: 40},
    note: '从太阳系上方连续俯冲到太阳，无切换。',
  });

  for (const plan of plans) {
    const sampled = sampleShot(plan.phases);
    const stationShot = {
      id: nameOf(plan.id), target: plan.id, tier: plan.tier, segment: plan.segment,
      startFrame: plan.start, endFrame: plan.end,
      camera: {path: sampled.path, fov: 44, easing: 'linear'},
      focus: {target: focusOf(plan.id), distance: distanceOf(plan.id)},
      post,
      note: '站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。',
    };
    phaseStats[stationShot.id] = sampled.lines.map(line => ({name: line.name,
      frames: line.frames, length: line.length, v0: line.v0, v1: line.v1, peak: line.peak,
      minSpeed: line.minSpeed, maxSpeed: line.maxSpeed}));
    stationShots.push(stationShot);
    push(stationShot);

    const gap = plan.index < gaps.length ? gaps[plan.index] : null;
    if (gap) {
      const next = plans[plan.index + 1];
      const focusTarget = focusOf(next.id);
      const focusPosition = focusTarget === 'sun' ? [0, 0, 0] : anchors[next.id];
      const from = dist(gap.shape[0], focusPosition);
      const to = dist(gap.shape[gap.shape.length - 1], focusPosition);
      const sampledTransit = sampleShot([{name: 'transit', shape: gap.shape, frames: gap.frames,
        v0: plan.vOut, v1: next.vIn}]);
      const transitShot = {
        id: `${plan.id}-to-${next.id}`, target: next.id, tier: 'minor',
        startFrame: plan.end, endFrame: next.start,
        camera: {path: sampledTransit.path, fov: 44, easing: 'linear'},
        focus: {target: focusTarget, from: Math.max(0.02, from), to: Math.max(0.02, to)},
        post,
        note: '空间过场：抬升到黄道面上方，目标从远处持续接近。',
      };
      phaseStats[transitShot.id] = sampledTransit.lines.map(line => ({name: line.name,
        frames: line.frames, length: line.length, v0: line.v0, v1: line.v1, peak: line.peak,
        minSpeed: line.minSpeed, maxSpeed: line.maxSpeed}));
      transitShots.push(transitShot);
      push(transitShot);
    }
  }

  // 收尾：从奥尔特云远出点继续向外拉远。
    const tail = sampleShot([{name: 'tail', shape: tailShape,
    frames: TAIL - plans.at(-1).postSpeechFrames,
    v0: plans[plans.length - 1].vOut, v1: 1.15 * plans[plans.length - 1].vOut}]);
  push({
    id: 'oort-tail', target: 'oort', tier: 'minor', startFrame: plans.at(-1).end, endFrame: totalFrames,
    camera: {path: tail.path, fov: 44, easing: 'linear'},
    focus: {target: 'sun', distance: 600},
    post,
    note: '收尾：继续向外，太阳成为亮点。',
  });

  // -------------------------------------------------------------- 检查

  const minDistances = [];
  for (const shot of shots) {
    const curve = curveOf(shot.camera.path);
    let nearest = {id: null, distance: Infinity};
    for (let index = 0; index <= 240; index += 1) {
      const point = curve.getPoint(index / 240).toArray();
      if (norm(point) > 900) problems.push(`${shot.id} 越出星空壳：${norm(point).toFixed(1)}`);
      for (const obstacle of OBSTACLES) {
        const gap = dist(point, obstacle.center) - obstacle.radius;
        if (gap < nearest.distance) nearest = {id: obstacle.id, distance: gap};
        if (gap < 0.4) problems.push(`${shot.id} 靠近 ${obstacle.id}：余量 ${gap.toFixed(2)}`);
      }
    }
    minDistances.push({shot: shot.id, nearest});
  }

  const shotPosition = (shot, frame) => {
    const span = Math.max(1, shot.endFrame - shot.startFrame);
    return curveOf(shot.camera.path).getPoint(
      clamp((frame - shot.startFrame) / span, 0, 1)).toArray();
  };

  for (let index = 1; index < shots.length; index += 1) {
    const previous = shots[index - 1];
    const current = shots[index];
    const gap = dist(previous.camera.path[previous.camera.path.length - 1], current.camera.path[0]);
    if (gap > 1e-6) problems.push(`${previous.id} → ${current.id} 位置不连续：${gap.toFixed(3)}`);
    if (previous.endFrame !== current.startFrame) {
      problems.push(`${previous.id} → ${current.id} 时间窗不相接`);
    }
  }

  const speeds = [];
  let boundarySpeedMax = 0;
  for (let index = 1; index < shots.length; index += 1) {
    const previous = shots[index - 1];
    const current = shots[index];
    const before = dist(shotPosition(previous, current.startFrame - 5),
      shotPosition(previous, current.startFrame - 1)) / 4;
    const after = dist(shotPosition(current, current.startFrame + 1),
      shotPosition(current, current.startFrame + 5)) / 4;
    const ratio = Math.max(before, after) / Math.max(1e-6, Math.min(before, after));
    boundarySpeedMax = Math.max(boundarySpeedMax, ratio);
    speeds.push({boundary: `${previous.id} -> ${current.id}`, before: Number(before.toFixed(4)),
      after: Number(after.toFixed(4)), ratio: Number(ratio.toFixed(2))});
    if (ratio > 1.8) problems.push(`${previous.id} → ${current.id} 速度突变 ×${ratio.toFixed(2)}`);
  }

  const approachRatios = [];
  for (const shot of stationShots) {
    if (shot.target === 'sun') continue;
    const anchor = anchors[shot.target];
    const curve = curveOf(shot.camera.path);
    let nearest = Infinity;
    for (let index = 0; index <= 240; index += 1) {
      nearest = Math.min(nearest, dist(curve.getPoint(index / 240).toArray(), anchor));
    }
    const first = dist(shot.camera.path[0], anchor) / Math.max(1e-9, nearest);
    const last = dist(shot.camera.path[shot.camera.path.length - 1], anchor)
      / Math.max(1e-9, nearest);
    approachRatios.push({shot: shot.id, first: Number(first.toFixed(2)),
      last: Number(last.toFixed(2)), nearest: Number(nearest.toFixed(2))});
    if (first < 1.35 || last < 1.35) {
      problems.push(`${shot.id} 接近/拉远不足：首 ${first.toFixed(2)}× / 末 ${last.toFixed(2)}×`);
    }
  }

  const transitElevation = [];
  for (const shot of transitShots) {
    const curve = curveOf(shot.camera.path);
    let maxY = -Infinity;
    for (let index = 0; index <= 240; index += 1) {
      maxY = Math.max(maxY, curve.getPoint(index / 240).y);
    }
    const arc = polyline(shot.camera.path).length;
    const need = Math.max(1.5, 0.10 * arc);
    transitElevation.push({shot: shot.id, maxY: Number(maxY.toFixed(2)),
      arc: Number(arc.toFixed(2)), need: Number(need.toFixed(2))});
    if (maxY < need) problems.push(`${shot.id} 过场没有离面抬升：${maxY.toFixed(2)} < ${need.toFixed(2)}`);
  }

  const farPointGaps = [];
  for (const [kind, points] of Object.entries({in: F_in, out: F_out})) {
    for (const [id, point] of Object.entries(points)) {
      const gap = OBSTACLES.reduce((least, item) =>
        Math.min(least, dist(point, item.center) - item.radius), Infinity);
      farPointGaps.push({kind, id, gap: Number(gap.toFixed(2))});
      if (gap < 0.6) problems.push(`${id} 远${kind}点余量不足：${gap.toFixed(2)}`);
    }
  }

  if (shots[0].startFrame !== 0 || shots[shots.length - 1].endFrame !== totalFrames) {
    problems.push(`镜头没有覆盖 0–${totalFrames}`);
  }

  // -------------------------------------------------------------- 分镜与报告

  const storyboard = {
    version: 8,
    schemaVersion: 8,
    fps: FPS,
    width: 1920,
    height: 1080,
    title: '太阳系之旅：一次连续的旅程',
    input: {kind: 'article'},
    targetSeconds: totalFrames / FPS,
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
      durationFrames: totalFrames,
      transition: 'cut',
      leadInFrames: LEAD_IN,
      tailFrames: TAIL,
      readingHoldFrames: 0,
      narrationSegments: SEGMENTS.map((segment, index) => ({
        id: segment.id, text: segment.text,
        ...(index < SEGMENTS.length - 1 ? {holdFrames: holdFrames[index]} : {}),
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
    totalFrames,
    transitBudgets: transitFrames.map((frames, index) => ({
      from: STATION_ORDER[index], to: STATION_ORDER[index + 1], frames, seconds: frames / FPS,
      pathLength: Number(polyline(transitShapes[index]).length.toFixed(2)),
    })),
    shots: shots.map(item => ({id: item.id, start: item.startFrame, end: item.endFrame,
      tier: item.tier, segment: item.segment ?? null, target: item.target,
      points: item.camera.path.length,
      length: Number(polyline(item.camera.path).length.toFixed(2)),
      endPoint: item.camera.path[item.camera.path.length - 1].map(value => Number(value.toFixed(3))),
      phases: phaseStats[item.id] ?? null})),
    obstacles: OBSTACLES,
    structureRadius: STRUCTURE_SIZE,
    minDistances,
    speeds,
    boundarySpeedMax: Number(boundarySpeedMax.toFixed(2)),
    approachRatios,
    transitElevation,
    farPointGaps,
    problems,
  };

  return {shots, storyboard, report, problems, boundarySpeedMax, minDistances, speeds,
    approachRatios, totalFrames};
}

export {
  FPS, LEAD_IN, TAIL, ENTRY, POST_SPEECH, SEGMENTS, REGIONS, STRUCTURE_SIZE,
  STATION_ORDER, STATION, post, UP, clamp, addv, subv, scale, dot, cross, norm, normalize,
  lerp3, dist, V, curveOf, frameOf, stationArc, polyline, positionAtDistance, tangentStart,
  tangentEnd, spaceArc, FLAT, bumpShape, bumpIntegral, sampleShot, humpProfile, sampleBySpeed,
  focusOf, distanceOf, nameOf,
};
