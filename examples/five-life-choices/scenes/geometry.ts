/**
 * 人生五选择的纯几何、相机与确定性世界数据。
 *
 * 世界坐标：x 为时间（年龄 × AGE_SCALE），y 为分支高度，z 为纵深。
 * 所有随时间变化的值只由 elapsedSeconds 推导；随机形状用固定种子，
 * 不读挂钟、不用随机数，确保同一帧在任何一次录制里完全一致。
 */

export const DURATION_SECONDS = 60;
export const AGE_SCALE = 96;
export const NEAR = 42;
export const AGE_MARKS = [0, 10, 18, 22, 30, 40, 60, 80] as const;
export const DECISION_AGES = [22, 25, 30, 35, 45] as const;

export type Vec3 = [number, number, number];
export type Viewport = {x: number; y: number; width: number; height: number};

export type CameraKey = {
  t: number;
  pos: Vec3;
  target: Vec3;
  fov: number;
  roll?: number;
};

export type CameraState = {pos: Vec3; target: Vec3; fov: number; roll: number};

export type CameraFrame = {
  pos: Vec3;
  forward: Vec3;
  right: Vec3;
  up: Vec3;
  focal: number;
  cx: number;
  cy: number;
  x0: number;
  width: number;
  height: number;
  roll: number;
};

export type ViewPoint = {x: number; y: number; z: number};
export type Projected = {
  x: number;
  y: number;
  z: number;
  scale: number;
  rel: number;
  visible: boolean;
};

// ------------------------------------------------------------------ 基础数学

export const clamp = (value: number, min = 0, max = 1) =>
  Math.min(max, Math.max(min, value));

export const smooth = (value: number) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};

export const span = (t: number, from: number, to: number) =>
  smooth((t - from) / (to - from));

export const ageX = (age: number) => age * AGE_SCALE;

export const add = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const mul = (a: Vec3, k: number): Vec3 => [a[0] * k, a[1] * k, a[2] * k];
export const lerp3 = (a: Vec3, b: Vec3, u: number): Vec3 =>
  [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u];
const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a: Vec3, b: Vec3): Vec3 =>
  [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const length = (a: Vec3) => Math.hypot(a[0], a[1], a[2]);
const normalize = (a: Vec3): Vec3 => {
  const l = length(a) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};

/** 32 位线性同余；同一种子在所有机器上给出同一串数。 */
export function seeded(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

/** 三次贝塞尔，用于支路、跑道与决策树。 */
export function cubic(p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3, u: number): Vec3 {
  const v = 1 - u;
  const a = v * v * v;
  const b = 3 * v * v * u;
  const c = 3 * v * u * u;
  const d = u * u * u;
  return [
    a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
    a * p0[2] + b * p1[2] + c * p2[2] + d * p3[2],
  ];
}

export function bezierPoints(p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3, steps = 48): Vec3[] {
  const points: Vec3[] = [];
  for (let i = 0; i <= steps; i += 1) points.push(cubic(p0, p1, p2, p3, i / steps));
  return points;
}

/** Catmull-Rom，用于相机位置与朝向，避免在每个关键帧停顿。 */
function catmull(a: Vec3, b: Vec3, c: Vec3, d: Vec3, u: number): Vec3 {
  const u2 = u * u;
  const u3 = u2 * u;
  const f = (i: number) => 0.5 * (
    2 * b[i] + (-a[i] + c[i]) * u
    + (2 * a[i] - 5 * b[i] + 4 * c[i] - d[i]) * u2
    + (-a[i] + 3 * b[i] - 3 * c[i] + d[i]) * u3
  );
  return [f(0), f(1), f(2)];
}

// ------------------------------------------------------------------ 人生路径

/** 未做选择时的底轨：轻微起伏，提供空间感。 */
export function basePoint(age: number): Vec3 {
  return [
    ageX(age),
    18 * Math.sin(age / 5.2) + 7 * Math.sin(age / 2.1),
    46 * Math.sin(age / 8.4),
  ];
}

/** 行业段的长期坡度：25 岁时为 0，60 岁时约 210。 */
const industryRise = (age: number) => 210 * Math.pow(clamp((age - 25) / 35), 1.25);

/**
 * 走完全片的主路径。每个选择都在之后缓慢叠加偏移，因此路径连续、
 * 不会在幕与幕之间跳变；决策树也从同一条路径上长出来。
 */
export function lifePoint(age: number): Vec3 {
  const p = basePoint(age);
  const city = smooth((age - 21.5) / 3.5);
  const industry = clamp((age - 25) / 35);
  const partner = smooth((age - 29.5) / 4);
  const invest = smooth((age - 34.5) / 8);
  const learning = smooth((age - 44) / 5);
  p[1] += industryRise(age) + 10 * partner + 40 * invest + 20 * learning - 12 * city;
  p[2] += 150 * city + 40 * industry + 70 * partner - 40 * learning;
  return p;
}

/** 时间到年龄：各幕在决策点附近放慢，但始终向前。 */
const AGE_KEYS: {t: number; age: number}[] = [
  {t: 0, age: 0},
  {t: 1.6, age: 7},
  {t: 3.2, age: 14},
  {t: 5.0, age: 20},
  {t: 7.0, age: 22},
  {t: 9.0, age: 22.8},
  {t: 12.0, age: 24},
  {t: 16.0, age: 25},
  {t: 19.0, age: 26.5},
  {t: 23.0, age: 28},
  {t: 27.0, age: 29.5},
  {t: 30.0, age: 31},
  {t: 35.5, age: 33},
  {t: 38.0, age: 38},
  {t: 40.5, age: 46},
  {t: 44.0, age: 60},
  {t: 52.0, age: 60},
  {t: 60.0, age: 60},
];

export function ageAt(t: number): number {
  if (t <= AGE_KEYS[0].t) return AGE_KEYS[0].age;
  for (let i = 1; i < AGE_KEYS.length; i += 1) {
    if (t <= AGE_KEYS[i].t) {
      const a = AGE_KEYS[i - 1];
      const b = AGE_KEYS[i];
      return a.age + (b.age - a.age) * smooth((t - a.t) / (b.t - a.t));
    }
  }
  return AGE_KEYS[AGE_KEYS.length - 1].age;
}

export const pointAt = (t: number): Vec3 => lifePoint(ageAt(t));

// ------------------------------------------------------------------ 相机

const at = (age: number, offset: Vec3): Vec3 => add(lifePoint(age), offset);

/**
 * 镜头关键帧。默认机位在轨道右上方，让轨道从左下进入、向右上远方延伸；
 * 行业段拉远看高度差，学习段升高看上下两条长期版本，结尾后拉看整棵树。
 */
export const CAMERA_KEYS: CameraKey[] = [
  {t: 0.0, pos: at(-1.5, [-260, 190, 430]), target: at(7, [0, 10, 0]), fov: 46, roll: 0},
  {t: 2.2, pos: at(6, [-200, 170, 400]), target: at(14, [0, 10, 0]), fov: 46, roll: -0.5},
  {t: 4.8, pos: at(15, [-150, 160, 370]), target: at(23, [0, 0, 0]), fov: 44, roll: -0.3},
  {t: 7.0, pos: at(20.2, [-160, 190, 460]), target: at(23.5, [0, 30, 50]), fov: 46, roll: 0},
  {t: 9.2, pos: at(22.6, [-40, 260, 700]), target: at(25.5, [0, 40, 90]), fov: 46, roll: 0.4},
  {t: 12.0, pos: at(24, [0, 280, 740]), target: at(27, [0, 40, 110]), fov: 46, roll: 0.3},
  {t: 16.0, pos: at(25.2, [60, 300, 900]), target: at(29, [0, 20, -20]), fov: 44, roll: 0.6},
  {t: 19.0, pos: at(26.5, [100, 280, 920]), target: at(32, [0, 30, -60]), fov: 44, roll: 0.4},
  {t: 23.0, pos: at(28, [160, 340, 1050]), target: at(36, [0, 40, -80]), fov: 45, roll: 0.8},
  {t: 25.2, pos: at(29.5, [220, 700, 1800]), target: at(39, [0, 20, -100]), fov: 48, roll: 1.2},
  {t: 27.0, pos: at(27.8, [160, 500, 1400]), target: at(33, [0, 20, -20]), fov: 45, roll: 0.8},
  {t: 30.0, pos: at(29.5, [-40, 220, 980]), target: at(33, [0, 80, 20]), fov: 44, roll: 0},
  {t: 33.0, pos: at(30.5, [-20, 210, 950]), target: at(34, [0, 80, 30]), fov: 44, roll: -0.2},
  {t: 35.5, pos: at(31.5, [0, 240, 980]), target: at(35, [0, 80, 30]), fov: 44, roll: 0},
  {t: 37.0, pos: [ageX(27) - 400, 420, 1550], target: [ageX(33), 220, -420], fov: 42, roll: 0},
  {t: 39.0, pos: [ageX(43) - 400, 440, 1500], target: [ageX(48), 235, -420], fov: 42, roll: 0},
  {t: 40.2, pos: [ageX(53) - 360, 450, 1450], target: [ageX(57), 245, -420], fov: 42, roll: 0},
  {t: 42.0, pos: [ageX(56) - 350, 460, 1420], target: [ageX(58), 250, -420], fov: 42, roll: 0},
  {t: 44.0, pos: [ageX(58) - 350, 520, 1450], target: [ageX(58), 250, -420], fov: 42, roll: 0},
  {t: 46.0, pos: [ageX(46), 1080, 2050], target: [ageX(46) + 180, -40, 0], fov: 50, roll: -0.6},
  {t: 49.0, pos: [ageX(48), 1120, 2150], target: [ageX(48) + 220, -40, 0], fov: 50, roll: -0.4},
  {t: 52.0, pos: [ageX(50), 1520, 2850], target: [ageX(45) + 250, 0, 0], fov: 48, roll: 0.3},
  {t: 54.5, pos: [ageX(48), 1500, 3950], target: [ageX(48), 80, 0], fov: 50, roll: 0.25},
  {t: 57.0, pos: [ageX(49), 1550, 4100], target: [ageX(49), 80, 0], fov: 50, roll: 0.15},
  {t: 60.0, pos: [ageX(50), 1600, 4200], target: [ageX(50), 80, 0], fov: 50, roll: 0},
];

export function cameraAt(t: number): CameraState {
  const keys = CAMERA_KEYS;
  if (t <= keys[0].t) {
    return {pos: keys[0].pos, target: keys[0].target, fov: keys[0].fov, roll: keys[0].roll ?? 0};
  }
  for (let i = 1; i < keys.length; i += 1) {
    if (t <= keys[i].t) {
      const a = keys[i - 1];
      const b = keys[i];
      const p0 = keys[Math.max(0, i - 2)];
      const p3 = keys[Math.min(keys.length - 1, i + 1)];
      const u = (t - a.t) / (b.t - a.t);
      const blend = smooth(u);
      return {
        pos: catmull(p0.pos, a.pos, b.pos, p3.pos, u),
        target: catmull(p0.target, a.target, b.target, p3.target, u),
        fov: a.fov + (b.fov - a.fov) * blend,
        roll: (a.roll ?? 0) + ((b.roll ?? 0) - (a.roll ?? 0)) * blend,
      };
    }
  }
  const last = keys[keys.length - 1];
  return {pos: last.pos, target: last.target, fov: last.fov, roll: last.roll ?? 0};
}

export function cameraFrame(cam: CameraState, viewport: Viewport): CameraFrame {
  const forward = normalize(sub(cam.target, cam.pos));
  let right = cross(forward, [0, 1, 0]);
  if (length(right) < 1e-4) right = [1, 0, 0];
  right = normalize(right);
  const up = normalize(cross(right, forward));
  return {
    pos: cam.pos,
    forward,
    right,
    up,
    focal: (viewport.height / 2) / Math.tan((cam.fov * Math.PI) / 360),
    cx: viewport.x + viewport.width / 2,
    cy: viewport.y + viewport.height / 2,
    x0: viewport.x,
    width: viewport.width,
    height: viewport.height,
    roll: (cam.roll * Math.PI) / 180,
  };
}

export function viewOf(frame: CameraFrame, point: Vec3): ViewPoint {
  const d = sub(point, frame.pos);
  return {x: dot(d, frame.right), y: dot(d, frame.up), z: dot(d, frame.forward)};
}

export function projectView(frame: CameraFrame, view: ViewPoint): Projected {
  if (view.z <= NEAR) return {x: 0, y: 0, z: view.z, scale: 0, rel: 0, visible: false};
  const sx = frame.cx + (view.x * frame.focal) / view.z;
  const sy = frame.cy - (view.y * frame.focal) / view.z;
  const cos = Math.cos(frame.roll);
  const sin = Math.sin(frame.roll);
  const rx = frame.cx + (sx - frame.cx) * cos - (sy - frame.cy) * sin;
  const ry = frame.cy + (sx - frame.cx) * sin + (sy - frame.cy) * cos;
  const scale = frame.focal / view.z;
  return {x: rx, y: ry, z: view.z, scale, rel: (scale * 1200) / frame.focal, visible: true};
}

export function projectPoint(frame: CameraFrame, point: Vec3): Projected {
  return projectView(frame, viewOf(frame, point));
}

/** 近远雾化：近处淡入，远处留一点轮廓。 */
export const fogAlpha = (z: number) =>
  clamp((z - 70) / 180) * (0.14 + 0.86 * clamp(1 - (z - 620) / 5400));

/** 幕窗口淡入淡出的通用包络。 */
export const actAlpha = (t: number, from: number, to: number, fade = 0.55) =>
  span(t, from, from + fade) * (1 - span(t, to - fade, to));

// ------------------------------------------------------------------ 城市

export type CityLane = {nameIndex: number; dy: number; dz: number; chosen: boolean};

export const CITY_LANES: CityLane[] = [
  {nameIndex: 0, dy: 120, dz: -330, chosen: false},
  {nameIndex: 1, dy: 60, dz: -120, chosen: false},
  {nameIndex: 2, dy: 20, dz: 20, chosen: false},
  {nameIndex: 3, dy: -10, dz: 150, chosen: true},
  {nameIndex: 4, dy: -80, dz: 340, chosen: false},
];

export type Branch = {nameIndex: number; chosen: boolean; points: Vec3[]; anchor: Vec3};

export function cityBranches(): Branch[] {
  const start = lifePoint(22);
  return CITY_LANES.map((lane) => {
    const end = add(lifePoint(27), [0, lane.dy, lane.dz]);
    const c1 = lerp3(start, end, 0.36);
    const c2 = add(lerp3(start, end, 0.76), [0, lane.dy * 0.22, 0]);
    const points = bezierPoints(start, c1, c2, end, 42);
    return {nameIndex: lane.nameIndex, chosen: lane.chosen, points, anchor: points[Math.floor(points.length * 0.82)]};
  });
}

export const CITY_BRANCHES = cityBranches();

export type Building = {base: Vec3; height: number; width: number; phase: number};

export function cityBuildings(): Building[] {
  const random = seeded(0x1f2e3d4c);
  const buildings: Building[] = [];
  for (let i = 0; i < 26; i += 1) {
    const age = 22.7 + (i / 26) * 4.6 + random() * 0.22;
    const anchor = lifePoint(age);
    const spread = 150 + random() * 390;
    const base: Vec3 = [anchor[0], anchor[1] - 150, anchor[2] + spread];
    buildings.push({
      base,
      height: 60 + random() * 190,
      width: 14 + random() * 22,
      phase: random() * Math.PI * 2,
    });
  }
  return buildings;
}

export const CITY_BUILDINGS = cityBuildings();

export type NetworkNode = {at: Vec3; reveal: number};
export type NetworkEdge = {a: number; b: number; reveal: number};

export function cityNetwork(): {nodes: NetworkNode[]; edges: NetworkEdge[]} {
  const random = seeded(0x5a6b7c8d);
  const nodes: NetworkNode[] = [];
  for (let i = 0; i < 7; i += 1) {
    const age = 23.2 + i * 0.62;
    const anchor = lifePoint(age);
    nodes.push({
      at: [anchor[0] + random() * 90, anchor[1] + 50 + random() * 240, anchor[2] + 170 + random() * 250],
      reveal: 10.2 + i * 0.62,
    });
  }
  const edges: NetworkEdge[] = [];
  for (let i = 1; i < nodes.length; i += 1) {
    edges.push({a: i, b: i - 1, reveal: nodes[i].reveal});
    if (i > 1) edges.push({a: i, b: Math.max(0, i - 2), reveal: nodes[i].reveal + 0.1});
    if (i > 3) edges.push({a: i, b: i - 3, reveal: nodes[i].reveal + 0.18});
  }
  return {nodes, edges};
}

export const CITY_NETWORK = cityNetwork();

// ------------------------------------------------------------------ 行业

export type IndustryLane = {nameIndex: number; dy: number; dz: number; chosen: boolean; points: Vec3[]};

export const INDUSTRY_LANES: {nameIndex: number; dy: number; dz: number; chosen: boolean}[] = [
  {nameIndex: 0, dy: -560, dz: 480, chosen: false},
  {nameIndex: 1, dy: -300, dz: 240, chosen: false},
  {nameIndex: 2, dy: 0, dz: 0, chosen: true},
  {nameIndex: 3, dy: 260, dz: -220, chosen: false},
  {nameIndex: 4, dy: 520, dz: -480, chosen: false},
];

export function industryLanes(): IndustryLane[] {
  const start = lifePoint(25);
  const baseEnd = lifePoint(60);
  return INDUSTRY_LANES.map((lane) => {
    const end = add(baseEnd, [0, lane.dy, lane.dz]);
    const c1 = lerp3(start, end, 0.44);
    const c2 = add(lerp3(start, end, 0.8), [0, lane.dy * 0.12, lane.dz * 0.08]);
    return {...lane, points: bezierPoints(start, c1, c2, end, 64)};
  });
}

export const INDUSTRY_PATHS = industryLanes();

/** 跑道上的光点位置：同一条时间参数，速度接近。 */
export function lanePoint(points: Vec3[], u: number): Vec3 {
  const index = Math.min(points.length - 1, Math.max(0, Math.floor(u * (points.length - 1))));
  return points[index];
}

// ------------------------------------------------------------------ 伴侣

export type PartnerTrack = {side: 'left' | 'right'; self: Vec3[]; partner: Vec3[]};

export function partnerTracks(): PartnerTrack[] {
  const start = lifePoint(30);
  const build = (dz: number, dy: number, wobble: number) => {
    const end = add(lifePoint(38), [0, dy, dz]);
    const c1 = lerp3(start, end, 0.4);
    const c2 = lerp3(start, end, 0.78);
    const self = bezierPoints(add(start, [0, 0, dz * 0.2]), c1, c2, end, 56);
    const partner = self.map((point, index) => {
      const u = index / (self.length - 1);
      return [
        point[0] + wobble * Math.sin(u * 9.5 + 0.7) * 0.16,
        point[1] - 64 + wobble * Math.sin(u * 7.2) * 0.1,
        point[2] + 62 + wobble * Math.cos(u * 8.1) * 0.12,
      ] as Vec3;
    });
    return {self, partner, side: dz > 0 ? 'left' : 'right'} as PartnerTrack;
  };
  return [build(300, -40, 90), build(-300, 40, 16)];
}

export const PARTNER_TRACKS = partnerTracks();

// ------------------------------------------------------------------ 投资

export const CHART_Z = -420;
export const CHART_Y0 = -210;
export const CHART_VALUE_SCALE = 1.5;

export const chartY = (value: number) => CHART_Y0 + (value - 100) * CHART_VALUE_SCALE;

export type CurvePoint = {age: number; value: number; at: Vec3};

function investmentCurve(kind: 'flat' | 'invest'): CurvePoint[] {
  const points: CurvePoint[] = [];
  for (let age = 25; age <= 60.001; age += 0.25) {
    const value = kind === 'flat'
      ? 100 + (age - 25) * 0.9
      : 100 * Math.pow(1.05, age - 25);
    points.push({age, value, at: [ageX(age), chartY(value), CHART_Z]});
  }
  return points;
}

export const INVEST_FLAT = investmentCurve('flat');
export const INVEST_GROW = investmentCurve('invest');

export function curvePointAt(points: CurvePoint[], age: number): CurvePoint {
  const index = Math.min(points.length - 1, Math.max(0, Math.round((age - 25) / 0.25)));
  return points[index];
}

// ------------------------------------------------------------------ 学习

export const LEARNING_DY = -620;
export const LEARNING_DZ = -80;
export const UPPER_DY = 620;

export function learningPoint(age: number): Vec3 {
  const anchor = basePoint(age);
  return [anchor[0], anchor[1] + LEARNING_DY, anchor[2] + LEARNING_DZ];
}

export function learningPoints(from = 0, to = 80, step = 0.5): Vec3[] {
  const points: Vec3[] = [];
  for (let age = from; age <= to + 0.001; age += step) points.push(learningPoint(age));
  return points;
}

export const LEARNING_PATH = learningPoints();

export type LearningNode = {at: Vec3; reveal: number};

export function learningNodes(): LearningNode[] {
  const random = seeded(0x7e8f9a0b);
  return [29, 33, 37, 41, 46, 51, 56].map((age, index) => {
    const anchor = learningPoint(age);
    return {
      at: [anchor[0], anchor[1] + 80 + random() * 150, anchor[2] + 80 + random() * 170],
      reveal: 45.6 + index * 0.34,
    };
  });
}

export const LEARNING_NODES = learningNodes();

export function upperBandPoints(): Vec3[] {
  const points: Vec3[] = [];
  for (let age = 25; age <= 70.001; age += 0.5) {
    const anchor = basePoint(age);
    points.push([anchor[0], anchor[1] + UPPER_DY, anchor[2]]);
  }
  return points;
}

export const UPPER_BAND = upperBandPoints();

// ------------------------------------------------------------------ 决策树

export type TreePath = {points: Vec3[]; bright: boolean; alpha: number};

const TREE_OPTIONS: {age: number; options: [number, number][]}[] = [
  {age: 22, options: [[0, 0], [200, -440], [100, -180], [60, 60], [-200, 450]]},
  {age: 25, options: [[0, 0], [-560, 620], [-260, 320], [320, -300], [620, -640]]},
  {age: 30, options: [[0, 0], [-220, 260], [180, -260], [360, 420]]},
  {age: 35, options: [[0, 0], [420, 320], [-300, -320]]},
  {age: 45, options: [[0, 0], [320, 260], [-260, -260]]},
  {age: 55, options: [[0, 0], [260, 200], [-240, -200]]},
  {age: 65, options: [[0, 0], [200, 160], [-200, -160]]},
];

export function decisionTree(): TreePath[] {
  const random = seeded(0x2468ace0);
  const paths: TreePath[] = [];
  for (let index = 0; index < 100; index += 1) {
    const bright = index === 0;
    const choices = TREE_OPTIONS.map((decision) => {
      if (bright) return {age: decision.age, dy: 0, dz: 0};
      const options = decision.options;
      const roll = random();
      const pick = roll < 0.46 ? 0 : 1 + Math.floor(random() * (options.length - 1));
      return {age: decision.age, dy: options[pick][0], dz: options[pick][1]};
    });
    const points: Vec3[] = [];
    for (let age = 22; age <= 80.001; age += 0.5) {
      let offsetY = 0;
      let offsetZ = 0;
      for (const choice of choices) {
        const grow = smooth((age - choice.age) / 2.5);
        offsetY += choice.dy * grow;
        offsetZ += choice.dz * grow;
      }
      const anchor = lifePoint(age);
      points.push([anchor[0], anchor[1] + offsetY, anchor[2] + offsetZ]);
    }
    paths.push({points, bright, alpha: bright ? 1 : 0.3 + random() * 0.2});
  }
  return paths;
}

export const TREE_PATHS = decisionTree();

// ------------------------------------------------------------------ 幕窗口

export type Act = {id: string; start: number; end: number};

export const ACTS: Act[] = [
  {id: 'opening', start: 0, end: 7.0},
  {id: 'city', start: 7.0, end: 16.0},
  {id: 'industry', start: 16.0, end: 27.0},
  {id: 'partner', start: 27.0, end: 35.5},
  {id: 'investment', start: 35.5, end: 44.0},
  {id: 'learning', start: 44.0, end: 52.0},
  {id: 'ending', start: 52.0, end: 60.0},
];

export function actAt(t: number): Act {
  for (const act of ACTS) if (t >= act.start && t < act.end) return act;
  return ACTS[ACTS.length - 1];
}
