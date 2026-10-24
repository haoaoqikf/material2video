export const DURATION = 65;

export const ACTS = [
  {id: 'opening', start: 0, end: 6},
  {id: 'city', start: 6, end: 16},
  {id: 'industry', start: 16, end: 27},
  {id: 'partner', start: 27, end: 38},
  {id: 'investment', start: 38, end: 48},
  {id: 'learning', start: 48, end: 57},
  {id: 'finale', start: 57, end: 65},
] as const;

export type ActId = (typeof ACTS)[number]['id'];

export function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export function smooth01(value: number): number {
  const x = clamp01(value);
  return x * x * (3 - 2 * x);
}

export function smoothstep(edge0: number, edge1: number, value: number): number {
  if (edge1 <= edge0) return value >= edge1 ? 1 : 0;
  return smooth01((value - edge0) / (edge1 - edge0));
}

export function window01(t: number, start: number, end: number): number {
  if (end <= start) return t >= end ? 1 : 0;
  return smooth01((t - start) / (end - start));
}

export function actAt(t: number): ActId {
  const time = Math.max(0, Math.min(DURATION, t));
  return ACTS.find((act) => time >= act.start && time < act.end)?.id ?? 'finale';
}

export function actProgress(t: number, id: ActId): number {
  const act = ACTS.find((item) => item.id === id);
  if (!act) return 0;
  return clamp01((t - act.start) / (act.end - act.start));
}

/** 人物沿主路径前进的归一化位置；各章交界保持一致，不回到起点。 */
const PATH_TIMES = [0, 6, 16, 27, 38, 48, 57, 65];
const PATH_US = [0, 0.09, 0.27, 0.44, 0.6, 0.76, 0.9, 1];

export function pathUAt(t: number): number {
  const time = Math.max(0, Math.min(DURATION, t));
  let index = 0;
  while (index < PATH_TIMES.length - 2 && time > PATH_TIMES[index + 1]) index += 1;
  const span = PATH_TIMES[index + 1] - PATH_TIMES[index];
  const local = span <= 0 ? 1 : (time - PATH_TIMES[index]) / span;
  return PATH_US[index] + (PATH_US[index + 1] - PATH_US[index]) * smooth01(local);
}

export type CameraKey = {
  t: number;
  pos: [number, number, number];
  look: [number, number, number];
  fov: number;
};

/** 连续镜头：局部跟随 → 拉远发现 → 侧移揭示 → 抬升 → 终幕全图。 */
export const CAMERA_KEYS: CameraKey[] = [
  {t: 0, pos: [5.5, 2.0, 7.5], look: [1.2, 1.0, 1.0], fov: 36},
  {t: 2.2, pos: [7.5, 2.8, 10], look: [3, 0.9, 2], fov: 38},
  {t: 4.6, pos: [24, 30, 20], look: [18, 0.5, 0], fov: 46},
  {t: 6.0, pos: [34, 36, 24], look: [26, 0.3, 2], fov: 48},
  {t: 8.0, pos: [46, 55, 42], look: [46, 0, 10], fov: 52},
  {t: 12.0, pos: [52, 60, 40], look: [52, 0, 8], fov: 52},
  {t: 16.0, pos: [54, 24, 46], look: [64, 8, 4], fov: 44},
  {t: 21.0, pos: [58, 16, 48], look: [68, 10, 4], fov: 42},
  {t: 27.0, pos: [100, 52, 38], look: [100, 22, -7], fov: 50},
  {t: 32.0, pos: [100, 58, 34], look: [100, 20, -7], fov: 52},
  {t: 38.0, pos: [96, 16, 44], look: [116, 24, 2], fov: 44},
  {t: 43.0, pos: [106, 16, 28], look: [128, 30, 2], fov: 40},
  {t: 48.0, pos: [142, 40, 34], look: [156, 34, 2], fov: 48},
  {t: 52.0, pos: [146, 44, 30], look: [162, 35, 2], fov: 52},
  {t: 57.0, pos: [150, 70, 60], look: [140, 25, 0], fov: 52},
  {t: 58.5, pos: [90, 120, 80], look: [65, 12, 0], fov: 58},
  {t: 61.0, pos: [60, 170, 90], look: [60, 10, 0], fov: 60},
  {t: 65.0, pos: [60, 170, 90], look: [60, 10, 0], fov: 60},
];

function componentAt(keys: CameraKey[], index: number, field: 'pos' | 'look', axis: number): number {
  return keys[index][field][axis];
}

function tangent(keys: CameraKey[], index: number, field: 'pos' | 'look', axis: number): number {
  const before = keys[Math.max(0, index - 1)];
  const after = keys[Math.min(keys.length - 1, index + 1)];
  const span = after.t - before.t;
  if (span <= 0) return 0;
  return (componentAt(keys, Math.min(keys.length - 1, index + 1), field, axis)
    - componentAt(keys, Math.max(0, index - 1), field, axis)) / span;
}

function hermite(p0: number, p1: number, m0: number, m1: number, span: number, s: number): number {
  const s2 = s * s;
  const s3 = s2 * s;
  return (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * span * m0
    + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * span * m1;
}

export function cameraAt(t: number): {pos: [number, number, number]; look: [number, number, number]; fov: number} {
  const time = Math.max(0, Math.min(DURATION, t));
  let index = 0;
  while (index < CAMERA_KEYS.length - 2 && time > CAMERA_KEYS[index + 1].t) index += 1;
  const a = CAMERA_KEYS[index];
  const b = CAMERA_KEYS[index + 1];
  const span = b.t - a.t;
  const s = span <= 0 ? 0 : (time - a.t) / span;
  const pos = [0, 1, 2].map((axis) => hermite(a.pos[axis], b.pos[axis],
    tangent(CAMERA_KEYS, index, 'pos', axis), tangent(CAMERA_KEYS, index + 1, 'pos', axis), span, s)) as [number, number, number];
  const look = [0, 1, 2].map((axis) => hermite(a.look[axis], b.look[axis],
    tangent(CAMERA_KEYS, index, 'look', axis), tangent(CAMERA_KEYS, index + 1, 'look', axis), span, s)) as [number, number, number];
  const fov = a.fov + (b.fov - a.fov) * smooth01(s);
  return {pos, look, fov};
}

/** 学习章四次解锁的先后。 */
export function unlockAt(t: number, index: number): number {
  return window01(t, 49.0 + index * 2.0, 50.4 + index * 2.0);
}

/** 终幕总拉远进度。 */
export function finaleAt(t: number): number {
  return window01(t, 57.5, 63.0);
}
