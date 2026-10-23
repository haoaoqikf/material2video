/**
 * 人生五选择的确定性世界：连续路径、相机、五类事件与结尾树。
 *
 * 世界坐标：x 为年龄（年龄 × AGE_SCALE），y 为高度，z 为纵深。
 * 所有随时间变化的值只由 elapsedSeconds 推导；随机形状使用固定种子。
 * 路径先离散采样再建立累计弧长表，运动按“世界距离”取样，而不是按数组下标。
 */

export const DURATION_SECONDS = 60;
export const AGE_SCALE = 96;
export const NEAR = 42;
export const AGE_MARKS = [0, 18, 22, 25, 30, 38, 47, 60] as const;
export const DECISION_AGES = [22, 25, 31, 35, 47] as const;

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

/** 一条按累计弧长取样的路径；零长度与端点都有明确处理。 */
export type PathTable = {
  points: Vec3[];
  cumulative: number[];
  length: number;
  atDistance(distance: number): Vec3;
  atU(u: number): Vec3;
  cut(distance: number): Vec3[];
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

/** 三次贝塞尔，用于支路、桥与结尾树。 */
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

/** Catmull-Rom，用于连续路径与相机位置，避免关键帧折角。 */
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

export function catmullPath(keys: Vec3[], steps = 24): Vec3[] {
  if (keys.length === 0) return [];
  if (keys.length === 1) return [keys[0]];
  const points: Vec3[] = [];
  for (let i = 0; i < keys.length - 1; i += 1) {
    const p0 = keys[Math.max(0, i - 1)];
    const p1 = keys[i];
    const p2 = keys[i + 1];
    const p3 = keys[Math.min(keys.length - 1, i + 2)];
    for (let s = 0; s < steps; s += 1) points.push(catmull(p0, p1, p2, p3, s / steps));
  }
  points.push(keys[keys.length - 1]);
  return points;
}

/** 去掉重合点后建立累计弧长表；相邻两点距离为 0 时不会污染取样。 */
export function makePath(raw: Vec3[]): PathTable {
  const points: Vec3[] = [];
  for (const point of raw) {
    const last = points[points.length - 1];
    if (!last || length(sub(point, last)) > 1e-6) points.push(point);
  }
  if (points.length === 0) points.push([0, 0, 0]);
  if (points.length === 1) {
    return {
      points,
      cumulative: [0],
      length: 0,
      atDistance: () => points[0],
      atU: () => points[0],
      cut: () => [points[0], points[0]],
    };
  }
  const cumulative = [0];
  for (let i = 1; i < points.length; i += 1) {
    cumulative.push(cumulative[i - 1] + length(sub(points[i], points[i - 1])));
  }
  const total = cumulative[cumulative.length - 1];

  const atDistance = (distance: number): Vec3 => {
    if (total <= 0) return points[0];
    const d = clamp(distance, 0, total);
    let low = 0;
    let high = cumulative.length - 1;
    while (low + 1 < high) {
      const mid = (low + high) >> 1;
      if (cumulative[mid] <= d) low = mid;
      else high = mid;
    }
    const segment = cumulative[high] - cumulative[low];
    if (segment <= 1e-9) return points[high];
    return lerp3(points[low], points[high], (d - cumulative[low]) / segment);
  };

  const atU = (u: number) => atDistance(clamp(u) * total);

  const cut = (distance: number): Vec3[] => {
    if (total <= 0) return [points[0], points[0]];
    const d = clamp(distance, 0, total);
    const cutPoints: Vec3[] = [points[0]];
    for (let i = 1; i < points.length; i += 1) {
      if (cumulative[i] < d) cutPoints.push(points[i]);
      else break;
    }
    const tail = atDistance(d);
    const last = cutPoints[cutPoints.length - 1];
    if (length(sub(tail, last)) > 1e-6) cutPoints.push(tail);
    if (cutPoints.length === 1) cutPoints.push(cutPoints[0]);
    return cutPoints;
  };

  return {points, cumulative, length: total, atDistance, atU, cut};
}

// ------------------------------------------------------------------ 时间与年龄

const AGE_KEYS: {t: number; age: number}[] = [
  {t: 0, age: 0},
  {t: 2, age: 7},
  {t: 4, age: 14},
  {t: 6.5, age: 22},
  {t: 10, age: 23.4},
  {t: 15.5, age: 25},
  {t: 20, age: 27.8},
  {t: 27, age: 31},
  {t: 31, age: 34},
  {t: 35.5, age: 38},
  {t: 39, age: 41},
  {t: 43.2, age: 45},
  {t: 46.2, age: 47},
  {t: 48.4, age: 50},
  {t: 52, age: 53},
  {t: 56, age: 57},
  {t: 60, age: 60},
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

// ------------------------------------------------------------------ 主路与事件路径

type RouteKey = {age: number; y: number; z: number};

const MAIN_KEYS: RouteKey[] = [
  {age: 0, y: 20, z: 0},
  {age: 8, y: 45, z: 26},
  {age: 16, y: 76, z: 16},
  {age: 22, y: 66, z: 0},
  {age: 23.2, y: 92, z: -230},
  {age: 24.1, y: 108, z: -170},
  {age: 25, y: 118, z: -40},
  {age: 27, y: 142, z: -40},
  {age: 31, y: 184, z: -18},
  {age: 35, y: 238, z: 6},
  {age: 38, y: 296, z: 24},
  {age: 43, y: 378, z: 44},
  {age: 45, y: 418, z: 54},
  {age: 47, y: 438, z: 62},
];

const routeToPoints = (keys: RouteKey[]): Vec3[] =>
  keys.map((key) => [ageX(key.age), key.y, key.z]);

/** 主路：0–47 岁，包含城市绕行与行业爬升。 */
const MAIN_BEFORE_RAW = catmullPath(routeToPoints(MAIN_KEYS), 30);
export const MAIN_BEFORE = makePath(MAIN_BEFORE_RAW);

/** 按年龄在主路 x 上取样；用于决策节点与分支起点。 */
export function mainPoint(age: number): Vec3 {
  const x = ageX(age);
  const points = MAIN_BEFORE.points;
  if (x <= points[0][0]) return points[0];
  if (x >= points[points.length - 1][0]) return points[points.length - 1];
  let low = 0;
  let high = points.length - 1;
  while (low + 1 < high) {
    const mid = (low + high) >> 1;
    if (points[mid][0] <= x) low = mid;
    else high = mid;
  }
  const a = points[low];
  const b = points[high];
  const dx = b[0] - a[0];
  const u = dx <= 1e-9 ? 0 : (x - a[0]) / dx;
  return lerp3(a, b, u);
}

export const pointAt = (t: number): Vec3 => mainPoint(ageAt(t));

/** 开场的小岔口：让前两秒就出现“选择”这一动作，而不是只移动一个点。 */
export type YouthBranch = {path: PathTable; bright: boolean};

function youthBranch(offset: {dy: number; dz: number}, bright: boolean): YouthBranch {
  if (bright) {
    const points = MAIN_BEFORE.points.filter((item) => {
      const age = item[0] / AGE_SCALE;
      return age >= 11.98 && age <= 20.02;
    });
    return {path: makePath(points), bright};
  }
  const start = mainPoint(12);
  const end = mainPoint(20);
  const keys: Vec3[] = [
    start,
    add(lerp3(start, end, 0.34), [0, offset.dy * 0.5, offset.dz * 0.6]),
    add(lerp3(start, end, 0.72), [0, offset.dy * 0.85, offset.dz * 1.0]),
    add(end, [0, offset.dy, offset.dz]),
  ];
  return {path: makePath(catmullPath(keys, 24)), bright};
}

export const YOUTH_BRANCHES: YouthBranch[] = [
  youthBranch({dy: 0, dz: 0}, true),
  youthBranch({dy: 120, dz: -180}, false),
  youthBranch({dy: -90, dz: 150}, false),
  youthBranch({dy: 40, dz: 260}, false),
];

// ---------------------------------------------------------------- 城市

export type CityLane = {
  nameIndex: number;
  chosen: boolean;
  path: PathTable;
  anchor: Vec3;
  opening: Vec3;
};

const CITY_OFFSETS: {dy: number; dz: number}[] = [
  {dy: 150, dz: -330},
  {dy: 70, dz: -150},
  {dy: 0, dz: 0},
  {dy: -55, dz: 160},
  {dy: -125, dz: 320},
];

function cityLane(offset: {dy: number; dz: number}, chosen: boolean, index: number): CityLane {
  const start = mainPoint(22);
  const end = mainPoint(25);
  if (chosen) {
    // 选中城市保留主路的城市绕行；网络入口从绕行中段长出来。
    const points = MAIN_BEFORE.points.filter((point) => {
      const age = point[0] / AGE_SCALE;
      return age >= 21.98 && age <= 25.02;
    });
    const path = makePath(points.length > 2 ? points : [start, end]);
    const anchor = mainPoint(23.2);
    return {nameIndex: index, chosen, path, anchor, opening: add(anchor, [0, 70, -150])};
  }
  const keys: Vec3[] = [
    start,
    add(lerp3(start, end, 0.34), [0, offset.dy * 0.5, offset.dz * 0.7]),
    add(lerp3(start, end, 0.72), [0, offset.dy * 0.9, offset.dz * 1.1]),
    add(end, [0, offset.dy, offset.dz]),
  ];
  const path = makePath(catmullPath(keys, 22));
  return {nameIndex: index, chosen, path, anchor: path.atU(0.78), opening: add(end, [0, offset.dy, offset.dz])};
}

export const CITY_LANES: CityLane[] = CITY_OFFSETS.map((offset, index) =>
  cityLane(offset, index === 2, index));

export type Building = {base: Vec3; height: number; width: number; phase: number};

export function cityBuildings(): Building[] {
  const random = seeded(0x1f2e3d4c);
  const buildings: Building[] = [];
  for (let i = 0; i < 30; i += 1) {
    const age = 22.5 + (i / 30) * 2.2 + random() * 0.2;
    const anchor = mainPoint(age);
    const spread = 170 + random() * 360;
    const base: Vec3 = [anchor[0], anchor[1] - 165, anchor[2] - 210 + spread];
    buildings.push({
      base,
      height: 55 + random() * 180,
      width: 12 + random() * 22,
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
    const age = 23.3 + i * 0.22;
    const anchor = mainPoint(age);
    nodes.push({
      at: [anchor[0] + 30 + random() * 70, anchor[1] + 60 + random() * 200, anchor[2] - 210 - random() * 220],
      reveal: 9.4 + i * 0.34,
    });
  }
  const edges: NetworkEdge[] = [];
  for (let i = 1; i < nodes.length; i += 1) {
    edges.push({a: i, b: i - 1, reveal: nodes[i].reveal});
    if (i > 1) edges.push({a: i, b: i - 2, reveal: nodes[i].reveal + 0.1});
  }
  return {nodes, edges};
}

export const CITY_NETWORK = cityNetwork();

// ---------------------------------------------------------------- 行业

export type IndustryLane = {
  nameIndex: number;
  chosen: boolean;
  path: PathTable;
};

const INDUSTRY_OFFSETS: {dy: number; dz: number}[] = [
  {dy: 180, dz: -200},
  {dy: -260, dz: 160},
  {dy: 0, dz: 0},
  {dy: 520, dz: -300},
  {dy: -520, dz: 340},
];

function industryLane(offset: {dy: number; dz: number}, chosen: boolean, index: number): IndustryLane {
  if (chosen) {
    const points = MAIN_BEFORE.points.filter((point) => {
      const age = point[0] / AGE_SCALE;
      return age >= 24.98 && age <= 45.02;
    });
    return {nameIndex: index, chosen, path: makePath(points)};
  }
  const start = mainPoint(25);
  const keys: Vec3[] = [
    start,
    add(mainPoint(28), [0, offset.dy * 0.03, offset.dz * 0.03]),
    add(mainPoint(32), [0, offset.dy * 0.1, offset.dz * 0.1]),
    add(mainPoint(38), [0, offset.dy * 0.38, offset.dz * 0.38]),
    add(mainPoint(45), [0, offset.dy, offset.dz]),
  ];
  return {nameIndex: index, chosen, path: makePath(catmullPath(keys, 26))};
}

export const INDUSTRY_LANES: IndustryLane[] = INDUSTRY_OFFSETS.map((offset, index) =>
  industryLane(offset, index === 2, index));

export const INDUSTRY_MIN_LENGTH = Math.min(...INDUSTRY_LANES.map((lane) => lane.path.length));
export const INDUSTRY_SPEED = 190;

/** 五条跑道共用同一世界距离；不是同一 u，也不是同一数组下标。 */
export function industryDistance(t: number): number {
  return clamp((t - 15.8) * INDUSTRY_SPEED, 0, INDUSTRY_MIN_LENGTH);
}

export function industryCenter(t: number): Vec3 {
  const distance = industryDistance(t);
  const points = INDUSTRY_LANES.map((lane) => lane.path.atDistance(distance));
  const sum = points.reduce((acc, point) => add(acc, point), [0, 0, 0] as Vec3);
  return mul(sum, 1 / points.length);
}

// ---------------------------------------------------------------- 伴侣

export type PartnerTrack = {
  self: PathTable;
  partner: PathTable;
  support: boolean;
  side: Vec3;
};

function partnerTracks(): PartnerTrack[] {
  const start = mainPoint(31);
  const end = mainPoint(38);
  const build = (support: boolean, dy: number, dz: number, wobble: number): PartnerTrack => {
    const selfKeys: Vec3[] = [
      add(start, [0, support ? 12 : -8, support ? 58 : -72]),
      add(lerp3(start, end, 0.34), [0, dy * 0.45, dz * 0.45]),
      add(lerp3(start, end, 0.72), [0, dy * 0.8, dz * 0.8]),
      add(end, [0, dy, dz]),
    ];
    const partnerKeys = selfKeys.map((point, index) => {
      const u = index / (selfKeys.length - 1);
      return [
        point[0] + wobble * Math.sin(u * 7.4 + 0.6) * 0.12,
        point[1] + (support ? 54 : -48) + wobble * Math.sin(u * 9.1) * 0.1,
        point[2] + (support ? 52 : -58) + wobble * Math.cos(u * 8.3) * 0.1,
      ] as Vec3;
    });
    return {
      self: makePath(catmullPath(selfKeys, 24)),
      partner: makePath(catmullPath(partnerKeys, 24)),
      support,
      side: [0, dy, dz],
    };
  };
  return [build(true, 76, 84, 18), build(false, -96, -124, 62)];
}

export const PARTNER_TRACKS = partnerTracks();

/** 伴侣关系留下的抬升：38 岁之后主路旁的持续性增亮带。 */
export const PARTNER_LIFT = makePath(catmullPath([
  add(mainPoint(38), [0, 58, 58]),
  add(mainPoint(41), [0, 72, 64]),
  add(mainPoint(45), [0, 86, 70]),
  add(mainPoint(49), [0, 98, 76]),
], 24));

// ---------------------------------------------------------------- 投资

export const CHART_AGE_START = 25;
export const CHART_AGE_END = 47;
export const CHART_Z = -600;
export const CHART_Y0 = -340;
export const CHART_VALUE_SCALE = 3.1;

export const chartY = (value: number) => CHART_Y0 + (value - 100) * CHART_VALUE_SCALE;

export type CurvePoint = {age: number; value: number; at: Vec3};

function investmentCurve(kind: "flat" | "steady"): CurvePoint[] {
  const points: CurvePoint[] = [];
  for (let age = CHART_AGE_START; age <= CHART_AGE_END + 0.001; age += 0.25) {
    const years = age - CHART_AGE_START;
    // 只表达“持续小额投入”的方向性差异；不出现收益数字、金额或增长公式。
    const value = kind === "flat"
      ? 100 + 1.15 * years
      : 100 + 1.9 * years + 0.155 * years * years;
    points.push({age, value, at: [ageX(age), chartY(value), CHART_Z]});
  }
  return points;
}

export const INVEST_FLAT = investmentCurve("flat");
export const INVEST_STEADY = investmentCurve("steady");

export function chartAgeAt(t: number): number {
  return CHART_AGE_START + (CHART_AGE_END - CHART_AGE_START) * span(t, 36.0, 42.6);
}

export function curvePointAt(points: CurvePoint[], age: number): CurvePoint {
  const index = Math.round((age - CHART_AGE_START) / 0.25);
  return points[Math.max(0, Math.min(points.length - 1, index))];
}

// ---------------------------------------------------------------- 学习

export const DEAD_END = mainPoint(47);

/** 换路后的新起点：与断头路拉开足够距离，让“进入—经过—离开”在画面中成立。 */
export const NEW_START: Vec3 = [ageX(50), 560, -200];

/** 先前积累的学习线：从 25 岁一直延伸到换路后的新起点。 */
export const LEARNING_THREAD = makePath(catmullPath([
  add(mainPoint(25), [0, 170, -120]),
  add(mainPoint(30), [0, 205, -150]),
  add(mainPoint(35), [0, 245, -175]),
  add(mainPoint(41), [0, 315, -200]),
  add(mainPoint(45), [0, 390, -215]),
  add(lerp3(DEAD_END, NEW_START, 0.5), [0, 170, -70]),
  NEW_START,
], 34));

export const LEARNING_NODES = [29, 33, 37, 41, 45, 48, 50].map((_age, index) => ({
  at: add(LEARNING_THREAD.atU(0.06 + index * 0.145), [0, 34 + (index % 2) * 26, 0]),
  reveal: 43.6 + index * 0.38,
}));

/** 从断头路到新起点的实际连接；主体会沿它走。 */
export const LEARNING_BRIDGE = makePath(catmullPath([
  DEAD_END,
  add(lerp3(DEAD_END, NEW_START, 0.32), [0, 120, -30]),
  add(lerp3(DEAD_END, NEW_START, 0.66), [0, 74, -8]),
  NEW_START,
], 36));

export const NEW_PATH = makePath(catmullPath([
  NEW_START,
  [ageX(53), 600, -230],
  [ageX(56), 648, -258],
  [ageX(60), 706, -286],
  [ageX(64), 766, -310],
  [ageX(68), 828, -332],
  [ageX(72), 892, -352],
], 34));

/** 已走过的主路：主路 0–47 + 连接 + 新路 50–72。 */
export const REALIZED = makePath([
  ...MAIN_BEFORE.points,
  ...LEARNING_BRIDGE.points,
  ...NEW_PATH.points.slice(1),
]);

function distanceAtAge(path: PathTable, age: number): number {
  const x = ageX(age);
  let low = 0;
  let high = path.points.length - 1;
  if (x <= path.points[0][0]) return 0;
  if (x >= path.points[high][0]) return path.length;
  while (low + 1 < high) {
    const mid = (low + high) >> 1;
    if (path.points[mid][0] <= x) low = mid;
    else high = mid;
  }
  const a = path.points[low];
  const b = path.points[high];
  const dx = b[0] - a[0];
  const u = dx <= 1e-9 ? 0 : (x - a[0]) / dx;
  const segment = path.cumulative[high] - path.cumulative[low];
  return path.cumulative[low] + segment * u;
}

export const MAIN_DISTANCES = {
  age22: distanceAtAge(MAIN_BEFORE, 22),
  age25: distanceAtAge(MAIN_BEFORE, 25),
  age31: distanceAtAge(MAIN_BEFORE, 31),
  age38: distanceAtAge(MAIN_BEFORE, 38),
  age45: distanceAtAge(MAIN_BEFORE, 45),
  age47: MAIN_BEFORE.length,
};

export const NEW_DISTANCES = {
  age50: 0,
  age53: distanceAtAge(NEW_PATH, 53),
  age60: distanceAtAge(NEW_PATH, 60),
  length: NEW_PATH.length,
};

/** 47 岁以后年龄刻度落在新路上，而不是被主路端点钳到断头处。 */
export function lifeMarkPoint(age: number): Vec3 {
  if (age <= 47) return mainPoint(age);
  return NEW_PATH.atDistance(distanceAtAge(NEW_PATH, age));
}

/** 叙事年龄只负责意义定位；主体在路径上的距离单独由时间窗口控制。 */
export type SubjectState = {point: Vec3; age: number; mode: "main" | "bridge" | "new" | "chart"};

/** 主体在主路上的世界距离；与叙事年龄分开，年龄平台期不会冻结事件。 */
export function mainSubjectDistance(t: number): number {
  if (t <= 6.5) return MAIN_DISTANCES.age22 * span(t, 0, 6.5);
  if (t <= 15.5) return MAIN_DISTANCES.age22
    + (MAIN_DISTANCES.age25 - MAIN_DISTANCES.age22) * span(t, 6.5, 15.5);
  if (t <= 27) return MAIN_DISTANCES.age25
    + (MAIN_DISTANCES.age31 - MAIN_DISTANCES.age25) * span(t, 15.5, 27);
  if (t <= 35.5) return MAIN_DISTANCES.age31
    + (MAIN_DISTANCES.age38 - MAIN_DISTANCES.age31) * span(t, 27, 35.5);
  if (t <= 43.2) return MAIN_DISTANCES.age38
    + (MAIN_DISTANCES.age45 - MAIN_DISTANCES.age38) * span(t, 35.5, 43.2);
  return MAIN_DISTANCES.age45
    + (MAIN_DISTANCES.age47 - MAIN_DISTANCES.age45) * span(t, 43.2, 46.2);
}

/** 主体在整条已走路径上的距离，用于点亮轨迹。 */
export function subjectDistance(t: number): number {
  if (t < 46.2) return mainSubjectDistance(t);
  if (t < 48.4) {
    return MAIN_BEFORE.length + LEARNING_BRIDGE.length * span(t, 46.2, 48.4);
  }
  const newDistance = NEW_DISTANCES.age50
    + (NEW_DISTANCES.age60 - NEW_DISTANCES.age50) * span(t, 48.4, 60);
  return MAIN_BEFORE.length + LEARNING_BRIDGE.length + newDistance;
}

export function subjectAt(t: number): SubjectState {
  const age = ageAt(t);
  if (t < 46.2) {
    return {point: MAIN_BEFORE.atDistance(mainSubjectDistance(t)), age, mode: "main"};
  }
  if (t < 48.4) {
    return {point: LEARNING_BRIDGE.atU(span(t, 46.2, 48.4)), age, mode: "bridge"};
  }
  const distance = NEW_DISTANCES.age50
    + (NEW_DISTANCES.age60 - NEW_DISTANCES.age50) * span(t, 48.4, 60);
  return {point: NEW_PATH.atDistance(distance), age, mode: "new"};
}

/** 投资段让同一主体沿“持续投入”的台地边缘走，保持身份连续。 */
export function chartSubjectAt(t: number): Vec3 {
  const point = curvePointAt(INVEST_STEADY, Math.min(60, chartAgeAt(t)));
  return add(point.at, [0, 16, 12]);
}

// ---------------------------------------------------------------- 结尾树

export type TreePath = {
  id: string;
  level: 0 | 1 | 2;
  points: Vec3[];
  parent: string | null;
  origin: Vec3;
  bright: boolean;
  alpha: number;
};

type Decision = {age: number; options: [number, number][]};

const DECISIONS: Decision[] = [
  {age: 22, options: [[0, 0], [330, -540], [190, 470], [-270, 370]]},
  {age: 25, options: [[0, 0], [-430, 640], [410, -390], [530, 270]]},
  {age: 31, options: [[0, 0], [390, 430], [-390, -350]]},
  {age: 35, options: [[0, 0], [450, 350], [-430, -390]]},
  {age: 47, options: [[0, 0], [430, 410], [-410, -430]]},
];

export const TREE_NODES = DECISIONS.map((decision) => mainPoint(decision.age));

function treeBranch(
  id: string,
  level: 1 | 2,
  origin: Vec3,
  endAge: number,
  dy: number,
  dz: number,
  parent: string | null,
  alpha: number,
): TreePath {
  const keys: Vec3[] = [
    origin,
    add(origin, [AGE_SCALE * 1.3, dy * 0.58, dz * 0.58]),
    add(origin, [AGE_SCALE * 4.8, dy * 0.98 + 40, dz * 0.98]),
    [ageX(endAge), origin[1] + dy * 1.25 + 20, origin[2] + dz * 1.25],
  ];
  return {
    id,
    level,
    points: catmullPath(keys, level === 1 ? 30 : 24),
    parent,
    origin,
    bright: false,
    alpha,
  };
}

export function decisionTree(): TreePath[] {
  const paths: TreePath[] = [{
    id: "realized",
    level: 0,
    points: REALIZED.points,
    parent: null,
    origin: REALIZED.points[0],
    bright: true,
    alpha: 1,
  }];
  DECISIONS.forEach((decision, decisionIndex) => {
    const origin = mainPoint(decision.age);
    decision.options.slice(1).forEach(([dy, dz], optionIndex) => {
      const id = `d${decisionIndex}-${optionIndex}`;
      const first = treeBranch(id, 1, origin, decision.age + 13 + optionIndex * 2.5,
        dy, dz, "realized", 0.5 + optionIndex * 0.03);
      paths.push(first);
      for (let sub = 0; sub < 2; sub += 1) {
        const origin2 = first.points[Math.floor(first.points.length * 0.52)];
        const sign = sub === 0 ? 1 : -1;
        paths.push(treeBranch(
          `${id}-${sub}`,
          2,
          origin2,
          decision.age + 25 + optionIndex * 2 + sub * 3,
          dy * 0.8 + sign * (250 + optionIndex * 40),
          dz * 0.8 + sign * (290 + sub * 50),
          id,
          0.3 + sub * 0.03,
        ));
      }
    });
  });
  return paths;
}

export const TREE_PATHS = decisionTree();

// ---------------------------------------------------------------- 相机

const point = (t: number) => subjectAt(t).point;
const camKey = (
  t: number,
  posOffset: Vec3,
  targetOffset: Vec3,
  fov: number,
  roll = 0,
): CameraKey => ({t, pos: add(point(t), posOffset), target: add(point(t), targetOffset), fov, roll});

const TREE_CENTER: Vec3 = [ageX(46), 650, -80];
const LEARNING_MID: Vec3 = lerp3(DEAD_END, NEW_START, 0.5);

export const CAMERA_KEYS: CameraKey[] = [
  camKey(0, [-420, 280, 700], [260, 0, 0], 48, -0.4),
  camKey(2.2, [-370, 260, 640], [270, 0, 0], 48, -0.3),
  camKey(4.6, [-330, 240, 600], [280, -10, -20], 47, -0.2),
  camKey(6.5, [-400, 360, 800], [320, -20, -90], 48, 0),
  camKey(9.2, [-540, 440, 1020], [340, -30, -150], 48, 0.25),
  camKey(12.5, [-480, 400, 960], [360, -50, -170], 48, 0.18),
  camKey(15.5, [-200, 140, 460], [190, 10, 0], 44, 0.1),
  camKey(19.0, [-130, 120, 430], [160, 10, 0], 44, 0.05),
  camKey(22.5, [-190, 210, 600], [150, 30, 0], 45, 0.1),
  {t: 24.6, pos: [ageX(37), 520, 2050], target: [ageX(37), 180, -100], fov: 48, roll: 0.03},
  {t: 27.0, pos: [ageX(38.5), 560, 2100], target: [ageX(38.5), 190, -100], fov: 48, roll: 0},
  camKey(28.4, [-440, 440, 1000], [170, -40, 0], 48, 0),
  camKey(31.0, [-320, 400, 920], [90, -60, 0], 48, -0.05),
  camKey(33.5, [-280, 380, 900], [110, -50, 0], 48, -0.05),
  camKey(35.5, [-310, 390, 920], [120, -40, 0], 47, 0),
  {t: 36.4, pos: [ageX(34), 220, 1750], target: [ageX(42), -120, CHART_Z], fov: 48, roll: 0},
  {t: 39.5, pos: [ageX(40), 250, 1700], target: [ageX(43), -120, CHART_Z], fov: 48, roll: 0},
  {t: 42.6, pos: [ageX(48), 270, 1700], target: [ageX(46), -120, CHART_Z], fov: 48, roll: 0},
  camKey(43.2, [-320, 300, 760], [230, 10, 0], 45, 0),
  camKey(45.2, [-280, 260, 720], [250, 20, 0], 45, 0),
  {t: 46.2, pos: add(LEARNING_MID, [-430, 330, 930]),
    target: add(LEARNING_MID, [40, 0, 0]), fov: 47, roll: 0.04},
  {t: 47.4, pos: add(LEARNING_MID, [-300, 250, 780]),
    target: add(LEARNING_MID, [60, 10, 0]), fov: 46, roll: 0.03},
  {t: 48.6, pos: add(NEW_START, [-360, 280, 800]),
    target: add(NEW_START, [180, 40, 0]), fov: 46, roll: 0},
  camKey(50.5, [-380, 320, 860], [200, 30, 0], 46, 0),
  camKey(52.0, [-460, 380, 1000], [220, 40, 0], 47, 0),
  {t: 54.2, pos: add(TREE_CENTER, [-1320, 1450, 2700]), target: add(TREE_CENTER, [120, 0, 0]), fov: 49, roll: 0.06},
  {t: 56.4, pos: add(TREE_CENTER, [-1600, 1750, 3100]), target: add(TREE_CENTER, [0, 20, 0]), fov: 50, roll: 0.03},
  {t: 60.0, pos: add(TREE_CENTER, [-1900, 2050, 3500]), target: add(TREE_CENTER, [0, 30, 0]), fov: 50, roll: 0},
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

export function viewOf(frame: CameraFrame, point3: Vec3): ViewPoint {
  const d = sub(point3, frame.pos);
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

export function projectPoint(frame: CameraFrame, point3: Vec3): Projected {
  return projectView(frame, viewOf(frame, point3));
}

/** 近远雾化：近处淡入，远处留一点轮廓。 */
export const fogAlpha = (z: number) =>
  clamp((z - 70) / 180) * (0.14 + 0.86 * clamp(1 - (z - 620) / 5400));

/** 幕窗口淡入淡出的通用包络。 */
export const actAlpha = (t: number, from: number, to: number, fade = 0.55) =>
  span(t, from, from + fade) * (1 - span(t, to - fade, to));

// ---------------------------------------------------------------- 幕窗口

export type Act = {id: string; start: number; end: number};

export const ACTS: Act[] = [
  {id: "opening", start: 0, end: 6.5},
  {id: "city", start: 6.5, end: 15.5},
  {id: "industry", start: 15.5, end: 27.0},
  {id: "partner", start: 27.0, end: 35.5},
  {id: "investment", start: 35.5, end: 43.2},
  {id: "learning", start: 43.2, end: 52.0},
  {id: "ending", start: 52.0, end: 60.0},
];

export function actAt(t: number): Act {
  for (const act of ACTS) if (t >= act.start && t < act.end) return act;
  return ACTS[ACTS.length - 1];
}
