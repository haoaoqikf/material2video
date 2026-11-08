/**
 * 二维绘制层的相机求值：把关键帧表与进度求成一次推拉的位置与尺度。
 *
 * 与 `primitives.ts` 的三条硬约束一致：
 *
 * 1. `progress` 是唯一时间输入。不读挂钟、帧号或上一帧状态，相同进度与关键帧
 *    每次求值都相同，因此逐帧录制、跳帧采样与重录结果一致。
 * 2. 不内置视觉主题：只返回数值，不决定颜色、缓动曲线以外的任何外观。
 * 3. 不做变换。产物是 `{scale, focusX, focusY}`，由调用方决定如何施加到绘制上。
 *
 * 缩放走**对数空间**：视觉上等速的推拉对应几何级数，线性插值会让近景端突进。
 * 焦点按缩放反比加权：推近时焦点更快贴到目标对象上，而不是平均滑过去。
 */

/** 缓动曲线：把 0–1 进度映射到 0–1。调用方传入，缺省为恒等（线性）。 */
export type CameraEasing = (t: number) => number;

export type CameraKey = {
  /** 关键帧在时间轴上的位置，按升序排列；单位由调用方决定（帧、秒均可）。 */
  at: number;
  /** 缩放；必须为正有限数。 */
  scale: number;
  /** 焦点在世界坐标中的位置。 */
  focusX: number;
  focusY: number;
};

export type CameraState = {
  /** 当前缩放；等于世界坐标到屏幕坐标的倍数。 */
  scale: number;
  /** 当前焦点，世界坐标。 */
  focusX: number;
  focusY: number;
};

function finite(value: number, name: string): number {
  if (!Number.isFinite(value)) throw new RangeError(`${name} 必须是有限数值`);
  return value;
}

/**
 * 求某一时刻的相机状态。
 *
 * `progress` 与关键帧的 `at` 在同一坐标轴上；落在两个关键帧之间时按缓动插值，
 * 早于首帧或晚于末帧时返回端点值（不做外推）。关键帧少于两个时直接返回唯一值。
 */
export function cameraAt(keys: readonly CameraKey[], progress: number, easing?: CameraEasing): CameraState {
  if (!keys.length) throw new RangeError('相机至少需要一个关键帧');
  const sorted = keys;
  sorted.forEach((key, index) => {
    finite(key.at, `keys[${index}].at`);
    finite(key.focusX, `keys[${index}].focusX`);
    finite(key.focusY, `keys[${index}].focusY`);
    if (finite(key.scale, `keys[${index}].scale`) <= 0) throw new RangeError(`keys[${index}].scale 必须大于 0`);
    if (index > 0 && key.at < sorted[index - 1].at) {
      throw new RangeError(`keys[${index}].at 必须按升序排列`);
    }
  });
  finite(progress, 'progress');
  const first = sorted[0];
  if (sorted.length === 1 || progress <= first.at) return pick(first);
  const last = sorted[sorted.length - 1];
  if (progress >= last.at) return pick(last);

  let index = 0;
  while (index < sorted.length - 2 && progress >= sorted[index + 1].at) index += 1;
  const from = sorted[index];
  const to = sorted[index + 1];
  const span = to.at - from.at;
  // 相邻关键帧同时刻时没有可插值的区间，直接取后一帧，避免除零。
  if (span <= 0) return pick(to);
  const raw = (progress - from.at) / span;
  const t = Math.min(1, Math.max(0, easing ? easing(raw) : raw));

  // 缩放：几何级数插值，等距进度对应等倍率变化。
  const scale = Math.exp(Math.log(from.scale) + (Math.log(to.scale) - Math.log(from.scale)) * t);
  // 焦点：按缩放反比加权。视觉上「推近多少」由 1/scale 的变化量决定，因此焦点
  // 跟着这个比例走，推近时更快贴到目标对象上，而不是平均滑过去。
  const inverseFrom = 1 / from.scale;
  const inverseTo = 1 / to.scale;
  const inverse = 1 / scale;
  const focusWeight = Math.abs(inverseTo - inverseFrom) < 1e-12
    ? t
    : Math.min(1, Math.max(0, (inverse - inverseFrom) / (inverseTo - inverseFrom)));
  const focusX = from.focusX + (to.focusX - from.focusX) * focusWeight;
  const focusY = from.focusY + (to.focusY - from.focusY) * focusWeight;
  return {scale, focusX, focusY};
}

function pick(key: CameraKey): CameraState {
  return {scale: key.scale, focusX: key.focusX, focusY: key.focusY};
}

/**
 * 世界坐标 → 屏幕坐标的换算，供绘制前定位用。
 *
 * 只做一次减法与乘法：屏幕中心落在 `(centerX, centerY)`，焦点平移到中心。
 * 相机本身不施加变换，需要旋转变形时仍由调用方的 `group` 负责。
 */
export function project(
  state: CameraState, point: readonly [number, number], centerX: number, centerY: number,
): [number, number] {
  return [
    centerX + (point[0] - state.focusX) * state.scale,
    centerY + (point[1] - state.focusY) * state.scale,
  ];
}
