/** 世界坐标相机：位置线性插值、缩放对数插值；镜头只改变观看范围。 */
export type Cam = {x: number; y: number; s: number};
export type CameraKey = {t: number; cam: Cam};

export function ease(value: number): number {
  const t = Math.min(1, Math.max(0, value));
  return t * t * (3 - 2 * t);
}

/** 在相邻关键帧之间插值；时间超出首尾时取端点。 */
export function between(seconds: number, keys: CameraKey[]): Cam {
  if (keys.length === 0) return {x: 960, y: 540, s: 1};
  if (seconds <= keys[0].t) return {...keys[0].cam};
  let index = 0;
  while (index < keys.length - 2 && seconds > keys[index + 1].t) index++;
  const from = keys[index];
  const to = keys[index + 1];
  const p = ease((seconds - from.t) / Math.max(1e-6, to.t - from.t));
  return {
    x: from.cam.x + (to.cam.x - from.cam.x) * p,
    y: from.cam.y + (to.cam.y - from.cam.y) * p,
    s: Math.exp(Math.log(from.cam.s) + (Math.log(to.cam.s) - Math.log(from.cam.s)) * p),
  };
}

/** 世界坐标 → 屏幕坐标；用于把世界对象放进当前相机视口。 */
export function project(cam: Cam, x: number, y: number): {x: number; y: number} {
  return {x: 960 - cam.s * (cam.x - x), y: 540 - cam.s * (cam.y - y)};
}
