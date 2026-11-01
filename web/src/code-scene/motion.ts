/**
 * 共享命名缓动：把 0–1 进度映射到可插值的数值。
 *
 * 三条约束：
 * 1. 纯函数：只依赖输入，不读时间、帧号、随机源或外部状态；
 * 2. 命名表达方向与强度，不表达品牌或视觉主题；
 * 3. 相机与原语共用同一套曲线，不在作品里复制近似实现。
 *
 * `backOut` 在结束前允许超过 1，用于回弹落定；需要严格 0–1 的调用方自行截断。
 */

export type MotionCurve = (t: number) => number;

export type MotionCurveName =
  | 'linear'
  | 'easeInCubic'
  | 'easeOutCubic'
  | 'easeInOutCubic'
  | 'easeInQuint'
  | 'easeOutQuint'
  | 'easeInOutQuint'
  | 'easeInExpo'
  | 'easeOutExpo'
  | 'easeInOutExpo'
  | 'easeInOutSine'
  | 'backOut';

/** 非有限输入按 0 处理，避免 NaN 进入几何。 */
function clampProgress(progress: number): number {
  if (!Number.isFinite(progress)) return 0;
  return Math.min(1, Math.max(0, progress));
}

export const MOTION_CURVES: Record<MotionCurveName, MotionCurve> = {
  linear: t => clampProgress(t),
  easeInCubic: t => clampProgress(t) ** 3,
  easeOutCubic: t => 1 - (1 - clampProgress(t)) ** 3,
  easeInOutCubic: t => {
    const value = clampProgress(t);
    return value < 0.5 ? 4 * value ** 3 : 1 - (-2 * value + 2) ** 3 / 2;
  },
  easeInQuint: t => clampProgress(t) ** 5,
  easeOutQuint: t => 1 - (1 - clampProgress(t)) ** 5,
  easeInOutQuint: t => {
    const value = clampProgress(t);
    return value < 0.5 ? 16 * value ** 5 : 1 - (-2 * value + 2) ** 5 / 2;
  },
  easeInExpo: t => {
    const value = clampProgress(t);
    return value === 0 ? 0 : 2 ** (10 * value - 10);
  },
  easeOutExpo: t => {
    const value = clampProgress(t);
    return value === 1 ? 1 : 1 - 2 ** (-10 * value);
  },
  easeInOutExpo: t => {
    const value = clampProgress(t);
    if (value === 0 || value === 1) return value;
    return value < 0.5
      ? 2 ** (20 * value - 10) / 2
      : (2 - 2 ** (-20 * value + 10)) / 2;
  },
  easeInOutSine: t => {
    const value = clampProgress(t);
    if (value === 0 || value === 1) return value;
    return -(Math.cos(Math.PI * value) - 1) / 2;
  },
  backOut: t => {
    const value = clampProgress(t);
    if (value === 0 || value === 1) return value;
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * (value - 1) ** 3 + c1 * (value - 1) ** 2;
  },
};

/** 按名称取曲线；未提供名称时使用画面内默认的缓入缓出。 */
export function motionCurve(name: MotionCurveName | undefined): MotionCurve {
  return MOTION_CURVES[name ?? 'easeInOutCubic'];
}

/** 直接求值；相机和原语都可以用它，避免重复实现。 */
export function easeMotion(name: MotionCurveName | undefined, progress: number): number {
  return motionCurve(name)(progress);
}

/** 0→1→0 的往返进度；非有限输入按 0。 */
export function pingPong(progress: number): number {
  const value = clampProgress(progress);
  return value <= 0.5 ? value * 2 : 2 - value * 2;
}

/** 带缓动的往返波，返回 0–1；用于呼吸、环境漂移等 ambient 运动。 */
export function waveMotion(name: MotionCurveName | undefined, progress: number): number {
  return motionCurve(name)(pingPong(progress));
}

/** 带缓动的往返振荡，返回 -1–1。 */
export function oscillate(name: MotionCurveName | undefined, progress: number): number {
  return 2 * waveMotion(name, progress) - 1;
}
