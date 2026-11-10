import * as THREE from 'three';

export type Placement = {radius: number; orbit: number; angle: number; parent?: string;
  /** 可选轨道倾角高度；用于把前景卫星放进土星 hero 的画面。 */ height?: number};
/** 单一稳定的压缩坐标系；轨道半径和球体半径分别压缩，不是物理比例。
 *
 * 一镜到底版本把主序天体的方位角排成随轨道半径单调递增的螺旋（0.30→6.30），
 * 相机因此可以一路向外飞行而不反复横穿太阳系。卫星的角度是世界方向角，
 * `positionOf` 直接把它当作相对母星的偏移方向。 */
export const LAYOUT: Record<string, Placement> = {
  sun: {radius: 2.2, orbit: 0, angle: 0},
  mercury: {radius: 0.42, orbit: 8, angle: 0.3},
  venus: {radius: 0.78, orbit: 12, angle: 0.9},
  earth: {radius: 0.85, orbit: 17, angle: 1.55},
  moon: {radius: 0.23, orbit: 2.5, angle: 1.9, parent: 'earth'},
  mars: {radius: 0.61, orbit: 23, angle: 2.8},
  ceres: {radius: 0.3, orbit: 33, angle: 3.2},
  jupiter: {radius: 2.2, orbit: 48, angle: 3.8},
  europa: {radius: 0.27, orbit: 5, angle: 1.8, parent: 'jupiter'},
  saturn: {radius: 1.85, orbit: 70, angle: 4.5},
  titan: {radius: 0.36, orbit: 6.3, angle: 1.36, parent: 'saturn', height: 4.0},
  uranus: {radius: 1.05, orbit: 92, angle: 5.1},
  neptune: {radius: 1.04, orbit: 115, angle: 5.7},
  pluto: {radius: 0.32, orbit: 138, angle: 6.3},
};
export function positionOf(id: string): THREE.Vector3 {
  const item = LAYOUT[id];
  if (!item) return new THREE.Vector3();
  const p = new THREE.Vector3(Math.cos(item.angle) * item.orbit, item.height ?? 0,
    Math.sin(item.angle) * item.orbit);
  return item.parent ? p.add(positionOf(item.parent)) : p;
}
