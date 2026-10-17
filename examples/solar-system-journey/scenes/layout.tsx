import {THREE} from 'm2v/code-scene';

export type Placement = {radius: number; orbit: number; angle: number; parent?: string};
/** 单一稳定的压缩坐标系；轨道半径和球体半径分别压缩，不是物理比例。 */
export const LAYOUT: Record<string, Placement> = {
  sun: {radius: 2.2, orbit: 0, angle: 0},
  mercury: {radius: 0.42, orbit: 8, angle: 0.3},
  venus: {radius: 0.78, orbit: 12, angle: 2.2},
  earth: {radius: 0.85, orbit: 17, angle: 5.7},
  moon: {radius: 0.23, orbit: 2.5, angle: 0.8, parent: 'earth'},
  mars: {radius: 0.61, orbit: 23, angle: 3.8},
  ceres: {radius: 0.3, orbit: 29, angle: 4.6},
  jupiter: {radius: 2.2, orbit: 38, angle: 0.9},
  europa: {radius: 0.27, orbit: 5, angle: 2.6, parent: 'jupiter'},
  saturn: {radius: 1.85, orbit: 51, angle: 4.9},
  titan: {radius: 0.36, orbit: 6.3, angle: 0.4, parent: 'saturn'},
  uranus: {radius: 1.05, orbit: 66, angle: 2.9},
  neptune: {radius: 1.04, orbit: 80, angle: 4.35},
  pluto: {radius: 0.32, orbit: 94, angle: 1.4},
};
export function positionOf(id: string): THREE.Vector3 {
  const item = LAYOUT[id];
  if (!item) return new THREE.Vector3();
  const p = new THREE.Vector3(Math.cos(item.angle) * item.orbit, 0, Math.sin(item.angle) * item.orbit);
  return item.parent ? p.add(positionOf(item.parent)) : p;
}
