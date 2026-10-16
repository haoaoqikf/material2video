import {THREE} from 'm2v/code-scene';
import {smooth} from './clock';

export type Placement = {radius: number; orbit: number; angle: number; parent?: string};
/** 单一稳定的压缩坐标系；轨道半径和球体半径分别压缩，不是物理比例。 */
export const LAYOUT: Record<string, Placement> = {
  sun: {radius: 3, orbit: 0, angle: 0},
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
export type Pose = {eye: THREE.Vector3; target: THREE.Vector3; overview: number};
export type Stop = {id: string; start: number; end: number};
const overviewPose = (id: string): Pose => ({
  eye: id === 'oort' ? new THREE.Vector3(400, 420, 480) :
    id === 'heliopause' ? new THREE.Vector3(165, 185, 220) : new THREE.Vector3(135, 175, 205),
  target: new THREE.Vector3(), overview: 1,
});

function closePose(id: string, phase: number): Pose {
  if (id === 'heliopause') return {eye: new THREE.Vector3(130, 95, 160), target: new THREE.Vector3(), overview: 1};
  if (id === 'oort') return {eye: new THREE.Vector3(320, 340, 390), target: new THREE.Vector3(), overview: 1};
  const place = LAYOUT[id];
  const target = positionOf(id);
  const radius = id === 'saturn' ? place.radius * 1.75 : Math.max(place.radius, 0.55);
  // 向阳侧略偏侧面观察，保留昼夜分界；旁侧轨道提供空间线索。
  const towardSun = target.length() ? target.clone().normalize().negate() : new THREE.Vector3(0.1, 0, 1);
  const tangent = new THREE.Vector3(-towardSun.z, 0, towardSun.x);
  const offset = towardSun.multiplyScalar(0.8).addScaledVector(tangent, 0.65);
  offset.y = id === 'saturn' ? 0.75 : 0.42;
  offset.normalize().multiplyScalar(radius * 5.3);
  offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), phase * 0.22);
  return {eye: target.clone().add(offset), target, overview: 0};
}

function blend(from: Pose, to: Pose, t: number): Pose {
  const u = smooth(t);
  return {eye: from.eye.clone().lerp(to.eye, u), target: from.target.clone().lerp(to.target, u),
    overview: from.overview + (to.overview - from.overview) * u};
}

/** 每段从上一段结束姿态开始；相机位置和朝向连续，天体不随旁白切换而重建。 */
export function poseAt(stops: Stop[], index: number, seconds: number): Pose {
  const stop = stops[index];
  const duration = stop.end - stop.start;
  const local = Math.max(0, seconds - stop.start);
  const incoming = Math.min(index === 0 ? 4.0 : 2.6, duration * 0.25);
  const outgoing = Math.min(2.1, duration * 0.21);
  const previousOverview = overviewPose(index === 0 ? 'sun' : stops[index - 1].id);
  if (local < incoming) return blend(previousOverview, closePose(stop.id, 0), local / incoming);
  if (local > duration - outgoing) return blend(closePose(stop.id, 1), overviewPose(stop.id),
    (local - duration + outgoing) / outgoing);
  return closePose(stop.id, (local - incoming) / Math.max(0.01, duration - incoming - outgoing));
}
