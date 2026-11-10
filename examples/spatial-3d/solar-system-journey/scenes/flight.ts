import * as THREE from 'three';
import type {Shot} from '../src/code-scene/cinematic/camera';

type Window = {startFrame: number; endFrame: number};
type Targets = Record<string, THREE.Vector3>;
const clamp = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => {const t = clamp(x); return t ** 3 * (10 - 15 * t + 6 * t * t);};

/** 本作品的运动参数；不是所有视频的通用速度阈值。跨镜头对称滤波不依赖历史帧。 */
export const POSITION_FILTER_FRAMES = 24;
const FILTER = Array.from({length: 9}, (_, i) => ({offset: (i - 4) / 4,
  weight: Math.exp(-(((i - 4) / 2) ** 2) / 2)}));
const WEIGHT = FILTER.reduce((sum, item) => sum + item.weight, 0);

/** 生成器诊断、粗预演和最终相机共用的无状态求值器。曲线只在创建时构建一次。 */
export function createFlight(shots: Shot[], windows: Record<string, Window>, targets: Targets) {
  const curves = shots.map(shot => new THREE.CatmullRomCurve3(
    (shot.camera?.path ?? [[0, 0, 10], [0, 0, 10]]).map(p => new THREE.Vector3(...p)),
    false, 'catmullrom', 0.5));
  const stations = shots.filter(shot => shot.segment && windows[shot.segment]);
  const transitions = stations.slice(1).map((next, i) => ({
    // 缩短跨站后把转向摊在上一段讲述尾部、完整移动与下一站接近中，
    // 而不是只把原来三秒以上的方向变化塞进一秒过场。
    start: Math.max(stations[i].startFrame + 60, stations[i].tier === 'hero'
      ? stations[i].endFrame - 90 : windows[stations[i].segment!].endFrame - 72),
    end: windows[next.segment!].startFrame + 30,
    from: stations[i].focus?.target ?? stations[i].target,
    to: next.focus?.target ?? next.target,
  }));
  const indexAt = (frame: number) => {
    let lo = 0, hi = shots.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (frame >= shots[mid].endFrame) lo = mid + 1; else hi = mid;
    }
    return lo;
  };
  const rawPosition = (frame: number) => {
    const i = indexAt(frame), shot = shots[i];
    return curves[i].getPoint(clamp((frame - shot.startFrame) / (shot.endFrame - shot.startFrame)));
  };
  const up = new THREE.Vector3(0, 1, 0);
  const origin = new THREE.Vector3();
  const orient = (position: THREE.Vector3, target: string) => new THREE.Quaternion()
    .setFromRotationMatrix(new THREE.Matrix4().lookAt(position, targets[target] ?? origin, up));
  const filteredPosition = (frame: number) => {
    const position = new THREE.Vector3();
    for (const tap of FILTER) position.addScaledVector(
      rawPosition(frame + tap.offset * POSITION_FILTER_FRAMES), tap.weight / WEIGHT);
    return position;
  };
  const turns = transitions.map(transition => ({...transition,
    fromPose: orient(filteredPosition(transition.start), transition.from),
    toPose: orient(filteredPosition(transition.end), transition.to)}));
  return (frame: number) => {
    const position = filteredPosition(frame);
    let focus = stations[0]?.focus?.target ?? shots[indexAt(frame)].focus?.target ?? shots[indexAt(frame)].target;
    let quaternion: THREE.Quaternion | null = null;
    for (const transition of turns) {
      if (frame < transition.start) break;
      focus = transition.to;
      if (frame < transition.end) {
        // 混合相机朝向而非两颗天体的世界坐标，避免焦点穿过相机造成甩头。
        quaternion = transition.fromPose.clone().slerp(transition.toPose,
          smooth((frame - transition.start) / (transition.end - transition.start)));
        break;
      }
    }
    const opening = shots[0];
    const fov = 44 + ((opening.camera?.fov ?? 44) - 44)
      * (1 - smooth((frame - (opening.endFrame - 120)) / 120));
    return {position, quaternion: quaternion ?? orient(position, focus), fov};
  };
}

