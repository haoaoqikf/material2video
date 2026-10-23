import { GENERAL_DEFAULT_FPS } from '../../video-config';
/**
 * 镜头、路径与焦点求值：`CameraRig`、镜头/look 类型、确定性工具与穿球检查。
 *
 * 与 `cinematic/index.tsx` 的三条硬约束一致：一切随时间变化的东西都由
 * `elapsedSeconds`/帧号驱动，不用挂钟、`Math.random` 或 CSS 动画。
 */
import {createContext, useContext, useMemo, useRef, type ReactNode} from 'react';
import * as THREE from 'three';
import {useFrame, useThree} from '@react-three/fiber';
import {useSceneContext} from '../context';

export type Vec3 = [number, number, number];
export type ShotTier = 'hero' | 'major' | 'minor';
export type EasingName = 'linear' | 'quintInOut' | 'quintOut' | 'sineInOut' | 'expoInOut';
export type LutName = 'neutral' | 'deep-space' | 'teal-amber' | 'warm-film';
export type PostSettings = {
  bloom?: number; dof?: number; grain?: number; vignette?: number;
  chromaticAberration?: number; lut?: LutName;
};
export type ShotCamera = {
  path?: Vec3[]; fov?: number; roll?: number; easing?: EasingName;
  keyframes?: {frame: number; position: Vec3}[];
};
export type Shot = {
  id: string; target: string; tier: ShotTier; segment?: string;
  startFrame: number; endFrame: number;
  camera?: ShotCamera;
  focus?: {target?: string; distance?: number; from?: number; to?: number; aperture?: number};
  exposure?: {ev?: number; mode?: 'look' | 'shot'};
  post?: PostSettings;
  note?: string;
  /** 显式硬切：不参与镜头边界的朝向/焦段/曝光混合。 */
  cut?: boolean;
};

/** 镜头边界混合帧数：0.5 秒内把朝向、FOV、滚转与曝光过渡到下一镜头。 */
export const SHOT_BLEND_FRAMES = 30;
export type Look = {
  profile: string; lut?: LutName; grain?: number; bloom?: number; dof?: number;
  vignette?: number; exposure?: {ev?: number; mode?: 'look' | 'shot'};
};

// ------------------------------------------------------------------ 确定性工具

/** 32 位字符串哈希：把 shot id 之类的文本变成稳定种子。 */
export function hashSeed(text: string): number {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/** 确定性伪随机序列；同一种子在任何机器、任何次运行都给出同一串数。 */
export function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function ease(name: EasingName | undefined, t: number): number {
  const value = Math.min(1, Math.max(0, t));
  switch (name ?? 'quintInOut') {
    case 'linear': return value;
    case 'quintOut': return 1 - (1 - value) ** 5;
    case 'sineInOut': return -(Math.cos(Math.PI * value) - 1) / 2;
    case 'expoInOut': return value === 0 ? 0 : value === 1 ? 1 : value < .5
      ? 2 ** (20 * value - 10) / 2 : (2 - 2 ** (-20 * value + 10)) / 2;
    default: return value < .5 ? 16 * value ** 5 : 1 - (-2 * value + 2) ** 5 / 2;
  }
}

/** 当前帧落在哪个镜头里；`endFrame` 为开区间上界。 */
export function activeShot(shots: Shot[], frame: number): Shot | null {
  for (const shot of shots) {
    if (frame >= shot.startFrame && frame < shot.endFrame) return shot;
  }
  return null;
}

// ------------------------------------------------------------------ 路径风险检查

export type Obstacle = {name: string; center: Vec3; radius: number};

/** 点到线段的最短距离。 */
export function pointSegmentDistance(point: THREE.Vector3, start: THREE.Vector3, end: THREE.Vector3): number {
  const direction = end.clone().sub(start);
  const lengthSquared = direction.lengthSq();
  if (lengthSquared === 0) return point.distanceTo(start);
  const t = Math.min(1, Math.max(0, point.clone().sub(start).dot(direction) / lengthSquared));
  return point.distanceTo(start.clone().addScaledVector(direction, t));
}

/** 相机路径是否穿过某个天体（含 `clearance` 余量）。 */
export function pathIntersectsSphere(path: Vec3[], center: Vec3, radius: number, clearance = 0): boolean {
  const target = new THREE.Vector3(...center);
  for (let index = 0; index < path.length - 1; index += 1) {
    const distance = pointSegmentDistance(target, new THREE.Vector3(...path[index]),
      new THREE.Vector3(...path[index + 1]));
    if (distance < radius + clearance) return true;
  }
  return false;
}

/** 逐个体检路径与障碍球的距离；返回余量不足的障碍（按最近距离排序）。 */
export function cameraPathRisk(path: Vec3[], obstacles: Obstacle[], clearance = 0): {name: string; distance: number}[] {
  const risks: {name: string; distance: number}[] = [];
  for (const obstacle of obstacles) {
    const target = new THREE.Vector3(...obstacle.center);
    let nearest = Number.POSITIVE_INFINITY;
    for (let index = 0; index < path.length - 1; index += 1) {
      nearest = Math.min(nearest, pointSegmentDistance(target, new THREE.Vector3(...path[index]),
        new THREE.Vector3(...path[index + 1])));
    }
    const margin = nearest - obstacle.radius - clearance;
    if (margin < 0) risks.push({name: obstacle.name, distance: margin});
  }
  return risks.sort((left, right) => left.distance - right.distance);
}

/** 背景裁切风险：相机跑到星空壳外、或超出远裁剪面时，背景会突然消失。 */
export function backgroundRisk(path: Vec3[], backgroundRadius: number, far: number): string[] {
  const problems: string[] = [];
  for (const point of path) {
    const distance = new THREE.Vector3(...point).length();
    if (distance > backgroundRadius) problems.push(`相机位于星空壳之外（${distance.toFixed(2)} > ${backgroundRadius}）`);
    if (distance > far) problems.push(`相机超出远裁剪面（${distance.toFixed(2)} > ${far}）`);
  }
  return [...new Set(problems)];
}

// ------------------------------------------------------------------ look 上下文

type LookValue = {look: Look; shots: Shot[]; shot: Shot | null; frame: number; fps: number};
const LookContext = createContext<{look?: Look; shots?: Shot[]} | null>(null);

/** 覆盖作品级的 `props.look` / `props.shots`；不套也能用，组件会读录制配置。 */
export function LookProvider({look, shots, children}: {look?: Look; shots?: Shot[]; children: ReactNode}) {
  const value = useMemo(() => ({look, shots}), [look, shots]);
  return <LookContext.Provider value={value}>{children}</LookContext.Provider>;
}

/** 读取 look、镜头清单与当前镜头。没有 provider 时回落到录制配置里的 `props`。 */
export function useLook(): LookValue {
  const override = useContext(LookContext);
  const {elapsedSeconds} = useSceneContext();
  const config = window.__M2V_CODE_CONFIG__;
  const fps = config?.fps ?? GENERAL_DEFAULT_FPS;
  const frame = Math.round(elapsedSeconds * fps);
  const props = (config?.props ?? {}) as {look?: Look; shots?: Shot[]};
  const look = override?.look ?? props.look ?? {profile: 'neutral'};
  const shots = override?.shots ?? props.shots ?? [];
  const shot = useMemo(() => activeShot(shots, frame), [shots, frame]);
  return {look, shots, shot, frame, fps};
}

/** 当前镜头；没有镜头清单时返回 `null`。 */
export function useShot(): Shot | null {
  return useLook().shot;
}

/**
 * 镜头内的对焦距离（世界单位）。声明 `from`/`to` 时按镜头进度线性拉移，
 * 否则用固定的 `distance`；都没有时返回 `null`（交给后端的默认值）。
 */
export function focusDistanceAt(shot: Shot | null, progress: number): number | null {
  const focus = shot?.focus;
  if (!focus) return null;
  if (focus.from !== undefined && focus.to !== undefined) {
    const t = Math.min(1, Math.max(0, progress));
    return focus.from + (focus.to - focus.from) * t;
  }
  return focus.distance ?? null;
}

// ------------------------------------------------------------------ 镜头

export type CameraRigProps = {
  shots?: Shot[];
  /** 焦点目标：镜头 `focus.target` 按名字在这里查；缺省用 `target`。 */
  targets?: Record<string, THREE.Object3D | THREE.Vector3 | (() => THREE.Vector3)>;
  target?: Vec3;
  fov?: number;
  near?: number;
  far?: number;
  makeDefault?: boolean;
};

function resolvePoint(
  value: THREE.Object3D | THREE.Vector3 | (() => THREE.Vector3) | undefined,
  fallback: THREE.Vector3, into: THREE.Vector3,
): THREE.Vector3 {
  if (!value) return into.copy(fallback);
  if (value instanceof THREE.Vector3) return into.copy(value);
  if (value instanceof THREE.Object3D) return into.copy(value.getWorldPosition(into));
  if (typeof value === 'function') return into.copy(value());
  throw new Error('镜头焦点必须是 Object3D、Vector3 或无参函数');
}

/**
 * 镜头路径与缓动：CatmullRom 或关键帧位置、每镜头 FOV/滚转/曝光、焦点拉移。
 *
 * 位置与朝向都由帧号算出，因此同一帧在任何一次录制里都落在同一点上。
 */
export function CameraRig({shots, targets, target, fov, near = 0.05, far = 6000, makeDefault = true}: CameraRigProps) {
  const camera = useThree(state => state.camera);
  const gl = useThree(state => state.gl);
  const scene = useLook();
  const list = shots ?? scene.shots;
  const focus = useRef(new THREE.Vector3());
  const previousFocus = useRef(new THREE.Vector3());
  const fallbackTarget = useMemo(() => new THREE.Vector3(...(target ?? [0, 0, 0])), [target]);
  const curve = useRef<{key: string; curve: THREE.CatmullRomCurve3} | null>(null);
  if (makeDefault) gl.domElement.dataset.m2vRig = '1';

  useFrame(() => {
    if (!(camera instanceof THREE.PerspectiveCamera)) return;
    const shot = activeShot(list, scene.frame);
    const camera3 = shot?.camera;
    const span = Math.max(1, (shot?.endFrame ?? 1) - (shot?.startFrame ?? 0));
    const raw = shot ? (scene.frame - shot.startFrame) / span : 0;
    const progress = ease(camera3?.easing, raw);

    const keyframes = camera3?.keyframes;
    if (keyframes && keyframes.length >= 2) {
      const position = new THREE.Vector3();
      const scaled = progress * (keyframes.length - 1);
      const index = Math.min(keyframes.length - 2, Math.floor(scaled));
      const local = scaled - index;
      position.lerpVectors(new THREE.Vector3(...keyframes[index].position),
        new THREE.Vector3(...keyframes[index + 1].position), local);
      camera.position.copy(position);
    } else if (camera3?.path && camera3.path.length >= 2) {
      const key = `${shot?.id}:${camera3.path.length}`;
      if (!curve.current || curve.current.key !== key) {
        curve.current = {key, curve: new THREE.CatmullRomCurve3(
          camera3.path.map(point => new THREE.Vector3(...point)), false, 'catmullrom', 0.5)};
      }
      curve.current.curve.getPoint(progress, camera.position);
    }

    // 一镜到底：位置路径连续，镜头边界再把朝向、FOV、滚转与曝光混合到下一镜头。
    const index = shot ? list.indexOf(shot) : -1;
    const previous = index > 0 ? list[index - 1] : null;
    const blendRaw = shot ? (scene.frame - shot.startFrame + 1) / SHOT_BLEND_FRAMES : 1;
    const blend = previous && !shot?.cut && !previous.cut
      ? ease('sineInOut', Math.min(1, Math.max(0, blendRaw))) : 1;

    const focusName = shot?.focus?.target;
    const resolved = focusName && targets ? targets[focusName] : undefined;
    resolvePoint(resolved, fallbackTarget, focus.current);
    if (previous && blend < 1) {
      const prevName = previous.focus?.target;
      const prevResolved = prevName && targets ? targets[prevName] : undefined;
      resolvePoint(prevResolved, fallbackTarget, previousFocus.current);
      focus.current.lerp(previousFocus.current, 1 - blend);
    }
    camera.lookAt(focus.current);
    const previousRoll = previous?.camera?.roll ?? 0;
    const roll = previousRoll + ((camera3?.roll ?? 0) - previousRoll) * blend;
    if (roll) camera.rotateZ(THREE.MathUtils.degToRad(roll));

    const previousFov = previous?.camera?.fov ?? fov ?? 40;
    const nextFov = previousFov + ((camera3?.fov ?? fov ?? 40) - previousFov) * blend;
    if (nextFov && Math.abs(camera.fov - nextFov) > 1e-6) {
      camera.fov = nextFov;
      camera.near = near;
      camera.far = far;
      camera.updateProjectionMatrix();
    }
    const exposureOf = (item: Shot | null) => (item?.exposure?.mode === 'shot'
      ? item.exposure.ev : undefined) ?? scene.look.exposure?.ev ?? 0;
    const ev = previous
      ? exposureOf(previous) + (exposureOf(shot) - exposureOf(previous)) * blend
      : exposureOf(shot);
    gl.toneMappingExposure = 2 ** ev;
  });
  return null;
}
