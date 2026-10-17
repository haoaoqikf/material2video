/**
 * 电影级共享套件：look、镜头、确定性后期与深空元件。
 *
 * 三条硬约束（与 `cinematic-video.md` 一致）：
 *
 * 1. 一切随时间变化的东西都由 `elapsedSeconds`/帧号驱动，不用挂钟、`Math.random`
 *    或 CSS 动画；粒子与噪声用「固定种子 + 帧号」的确定性哈希。
 * 2. 后期只作用于 canvas，不影响共享字幕 DOM 层。
 * 3. 元件按需引入；standard 作品不引用它们时画面与既有一致。
 */
import {createContext, useContext, useMemo, useRef, type ReactNode} from 'react';
import * as THREE from 'three';
import {useFrame, useThree} from '@react-three/fiber';
import {
  Bloom, BrightnessContrast, ChromaticAberration, DepthOfField, EffectComposer,
  HueSaturation, Vignette, wrapEffect,
} from '@react-three/postprocessing';
import {BlendFunction, Effect} from 'postprocessing';
import {useSceneContext} from './context';

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
};
export type Look = {
  profile: string; lut?: LutName; grain?: number; bloom?: number; dof?: number;
  vignette?: number; exposure?: {ev?: number; mode?: 'look' | 'shot'};
};

/** 内置调色：`lut` 是**具名档**而不是外部 .cube 文件，录制期不取外网也不读作品目录。 */
export const GRADES: Record<LutName, {hue: number; saturation: number; brightness: number; contrast: number}> = {
  'neutral': {hue: 0, saturation: 0, brightness: 0, contrast: 0},
  'deep-space': {hue: 0.01, saturation: 0.03, brightness: -0.04, contrast: 0.06},
  'teal-amber': {hue: -0.03, saturation: 0.12, brightness: 0, contrast: 0.18},
  'warm-film': {hue: 0.05, saturation: -0.05, brightness: 0.02, contrast: 0.1},
};
export const LUT_NAMES = Object.keys(GRADES) as LutName[];

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
  const fps = config?.fps ?? 60;
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

/** 后期参数：shot 级覆盖 look 级，两者都缺时用基线。 */
function resolvePost(look: Look, shot: Shot | null): Required<Omit<PostSettings, 'lut'>> & {lut: LutName} {
  return {
    bloom: shot?.post?.bloom ?? look.bloom ?? 0,
    dof: shot?.post?.dof ?? look.dof ?? 0,
    grain: shot?.post?.grain ?? look.grain ?? 0,
    vignette: shot?.post?.vignette ?? look.vignette ?? 0,
    chromaticAberration: shot?.post?.chromaticAberration ?? 0,
    lut: shot?.post?.lut ?? look.lut ?? 'neutral',
  };
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

// ------------------------------------------------------------------ 确定性颗粒

const GRAIN_FRAGMENT = `
uniform float strength;
uniform float seed;
float grainHash(vec2 point) {
  return fract(sin(dot(point, vec2(12.9898, 78.233))) * 43758.5453123);
}
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  float noise = grainHash(floor(uv * 1024.0) + seed) - 0.5;
  outputColor = vec4(inputColor.rgb + noise * strength, inputColor.a);
}`;

/** 帧号驱动的颗粒：种子由「镜头 id 哈希 + 帧号」决定，同帧永远同一张噪点。 */
export class GrainEffect extends Effect {
  constructor({strength = 0, seed = 0}: {strength?: number; seed?: number} = {}) {
    super('GrainEffect', GRAIN_FRAGMENT, {
      blendFunction: BlendFunction.NORMAL,
      uniforms: new Map<string, THREE.Uniform>([['strength', new THREE.Uniform(strength)],
                                               ['seed', new THREE.Uniform(seed)]]),
    });
  }
  set strength(value: number) {
    (this.uniforms.get('strength') as THREE.Uniform).value = value;
  }
  set seed(value: number) {
    (this.uniforms.get('seed') as THREE.Uniform).value = value;
  }
}
const Grain = wrapEffect(GrainEffect, {blendFunction: BlendFunction.NORMAL});

// ------------------------------------------------------------------ 后期

/**
 * 画面后期：Bloom、DOF、grain、vignette、色散与具名调色。
 *
 * `multisampling={0}` 是有意为之：MSAA 的采样模式由驱动决定，关掉它才能保证
 * 同帧在不同机器上一致。grain 用自带的确定性效果，而不是库里的 `Noise`
 * （后者的噪点纹理来自 `Math.random`，跨次运行不一致）。
 */
export function PostFX({enabled = true, children}: {enabled?: boolean; children?: ReactNode}) {
  const {look, shot, frame} = useLook();
  const camera = useThree(state => state.camera);
  const settings = resolvePost(look, shot);
  const grade = GRADES[settings.lut] ?? GRADES.neutral;
  const grain = useRef<GrainEffect>(null);
  // 焦点拉移：镜头内按进度插值，再按相机近远裁剪面归一化成 DOF 的 0–1 距离。
  const span = Math.max(1, (shot?.endFrame ?? 1) - (shot?.startFrame ?? 0));
  const progress = shot ? (frame - shot.startFrame) / span : 0;
  const world = focusDistanceAt(shot, progress);
  const near = camera instanceof THREE.PerspectiveCamera ? camera.near : 0.1;
  const far = camera instanceof THREE.PerspectiveCamera ? camera.far : 1000;
  const focusDistance = world === null
    ? Math.min(0.9, Math.max(0.01, 1 - settings.dof))
    : Math.min(0.95, Math.max(0.01, (world - near) / Math.max(1e-6, far - near)));
  useFrame(() => {
    const effect = grain.current;
    if (effect) effect.seed = hashSeed(shot?.id ?? 'look') % 4096 + frame;
  });
  if (!enabled) return null;
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {settings.bloom > 0
        ? <Bloom intensity={settings.bloom} luminanceThreshold={0.55} luminanceSmoothing={0.2} mipmapBlur/>
        : <></>}
      {settings.dof > 0
        ? <DepthOfField focusDistance={focusDistance}
            focalLength={0.02 + settings.dof * 0.06} bokehScale={2 + settings.dof * 4}/>
        : <></>}
      <HueSaturation hue={grade.hue} saturation={grade.saturation}/>
      <BrightnessContrast brightness={grade.brightness} contrast={grade.contrast}/>
      {settings.vignette > 0
        ? <Vignette offset={0.3} darkness={Math.min(1, settings.vignette)} eskil={false}/>
        : <></>}
      {settings.chromaticAberration > 0
        ? <ChromaticAberration offset={[settings.chromaticAberration * 0.004, settings.chromaticAberration * 0.004]}
            radialModulation modulationOffset={0.15}/>
        : <></>}
      {settings.grain > 0 ? <Grain ref={grain} strength={settings.grain * 0.06} seed={0}/> : <></>}
      {children}
    </EffectComposer>
  );
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

    const focusName = shot?.focus?.target;
    const resolved = focusName && targets ? targets[focusName] : undefined;
    resolvePoint(resolved, fallbackTarget, focus.current);
    camera.lookAt(focus.current);
    if (camera3?.roll) camera.rotateZ(THREE.MathUtils.degToRad(camera3.roll));

    const nextFov = camera3?.fov ?? fov;
    if (nextFov && Math.abs(camera.fov - nextFov) > 1e-6) {
      camera.fov = nextFov;
      camera.near = near;
      camera.far = far;
      camera.updateProjectionMatrix();
    }
    const ev = (shot?.exposure?.mode === 'shot' ? shot.exposure.ev : undefined)
      ?? scene.look.exposure?.ev ?? 0;
    gl.toneMappingExposure = 2 ** ev;
  });
  return null;
}

// ------------------------------------------------------------------ 深空元件

const FRESNEL_VERTEX = `
varying vec3 vNormal;
varying vec3 vView;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vNormal = normalize(mat3(modelMatrix) * normal);
  vView = normalize(cameraPosition - world.xyz);
  gl_Position = projectionMatrix * viewMatrix * world;
}`;

const FRESNEL_FRAGMENT = `
uniform vec3 glowColor;
uniform float intensity;
uniform float power;
uniform float bias;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  float rim = pow(clamp(bias - dot(vNormal, vView), 0.0, 1.0), power);
  gl_FragColor = vec4(glowColor * rim * intensity, rim * intensity);
}`;

function fresnelMaterial(color: string, intensity: number, power: number, bias: number, side: THREE.Side) {
  return new THREE.ShaderMaterial({
    uniforms: {
      glowColor: {value: new THREE.Color(color)},
      intensity: {value: intensity},
      power: {value: power},
      bias: {value: bias},
    },
    vertexShader: FRESNEL_VERTEX,
    fragmentShader: FRESNEL_FRAGMENT,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side,
  });
}

/** 星空：固定种子的球壳点云，不随时间变化，作为深空的静态参照。 */
export function Starfield({count = 1400, radius = 1200, seed = 'stars', color = '#ffffff',
                           size = 2.4, opacity = 0.85}: {
  count?: number; radius?: number; seed?: string; color?: string; size?: number; opacity?: number;
}) {
  const geometry = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      const distance = radius * (0.85 + random() * 0.3);
      positions[index * 3] = distance * Math.sin(phi) * Math.cos(theta);
      positions[index * 3 + 1] = distance * Math.cos(phi);
      positions[index * 3 + 2] = distance * Math.sin(phi) * Math.sin(theta);
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return buffer;
  }, [count, radius, seed]);
  return (
    <points geometry={geometry}>
      <pointsMaterial color={color} size={size} sizeAttenuation transparent opacity={opacity} depthWrite={false}/>
    </points>
  );
}

/** 粒子带：小行星带、柯伊伯带这类环形粒子；自转由帧号驱动。 */
export function ParticleBelt({count = 900, innerRadius = 8, outerRadius = 12, thickness = 0.6,
                              seed = 'belt', color = '#cbb79a', size = 0.9, spin = 0.03, opacity = 0.9}: {
  count?: number; innerRadius?: number; outerRadius?: number; thickness?: number;
  seed?: string; color?: string; size?: number; spin?: number; opacity?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const geometry = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const angle = random() * Math.PI * 2;
      const distance = innerRadius + random() * (outerRadius - innerRadius);
      positions[index * 3] = Math.cos(angle) * distance;
      positions[index * 3 + 1] = (random() - 0.5) * thickness;
      positions[index * 3 + 2] = Math.sin(angle) * distance;
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return buffer;
  }, [count, innerRadius, outerRadius, thickness, seed]);
  return (
    <points geometry={geometry} rotation={[0, elapsedSeconds * spin, 0]}>
      <pointsMaterial color={color} size={size} sizeAttenuation transparent opacity={opacity} depthWrite={false}/>
    </points>
  );
}

/** 大气：外层菲涅尔边缘光，加法混合，从背面绘制。 */
export function Atmosphere({radius, color = '#4b9dff', intensity = 1.1, power = 2.6, bias = 0.85}: {
  radius: number; color?: string; intensity?: number; power?: number; bias?: number;
}) {
  const material = useMemo(() => fresnelMaterial(color, intensity, power, bias, THREE.BackSide),
    [color, intensity, power, bias]);
  return <mesh material={material}><sphereGeometry args={[radius * 1.045, 64, 48]}/></mesh>;
}

/** 日冕：太阳外层辉光，加法混合朝外。 */
export function Corona({radius, color = '#ff9a3c', intensity = 0.9, power = 3.2, bias = 0.95}: {
  radius: number; color?: string; intensity?: number; power?: number; bias?: number;
}) {
  const material = useMemo(() => fresnelMaterial(color, intensity, power, bias, THREE.FrontSide),
    [color, intensity, power, bias]);
  return <mesh material={material}><sphereGeometry args={[radius * 1.22, 64, 48]}/></mesh>;
}

/** 日面：临边昏暗 + 帧驱动的颗粒噪声，不需要贴图也能有表面细节。 */
const SUN_VERTEX = `
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  vUv = uv;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vNormal = normalize(mat3(modelMatrix) * normal);
  vView = normalize(cameraPosition - world.xyz);
  gl_Position = projectionMatrix * viewMatrix * world;
}`;

const SUN_FRAGMENT = `
uniform vec3 baseColor;
uniform vec3 hotColor;
uniform float time;
uniform float granulation;
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vView;
float noise(vec2 point) {
  return fract(sin(dot(point, vec2(41.13, 289.7))) * 43758.5453123);
}
void main() {
  vec2 cell = floor(vUv * 220.0);
  float grain = noise(cell + floor(time * 6.0));
  float limb = pow(clamp(dot(vNormal, vView), 0.0, 1.0), 0.55);
  vec3 color = mix(baseColor, hotColor, grain * granulation);
  gl_FragColor = vec4(color * (0.55 + 0.45 * limb), 1.0);
}`;

export function SunSurface({radius, color = '#ffb44d', hotColor = '#fff1c2', granulation = 0.6, speed = 0.35}: {
  radius: number; color?: string; hotColor?: string; granulation?: number; speed?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const material = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      baseColor: {value: new THREE.Color(color)},
      hotColor: {value: new THREE.Color(hotColor)},
      time: {value: 0},
      granulation: {value: granulation},
    },
    vertexShader: SUN_VERTEX, fragmentShader: SUN_FRAGMENT,
  }), [color, hotColor, granulation]);
  material.uniforms.time.value = elapsedSeconds * speed;
  return <mesh material={material}><sphereGeometry args={[radius, 96, 64]}/></mesh>;
}

/** 日珥：从日面升起的热等离子弧，数量与形状由种子决定，涨落由帧号驱动。 */
export function Prominence({radius, color = '#ff7a3c', count = 5, seed = 'prominence',
                            height = 0.9, speed = 0.25}: {
  radius: number; color?: string; count?: number; seed?: string; height?: number; speed?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const arcs = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    return Array.from({length: count}, () => {
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1) * 0.7;
      const arc = 0.35 + random() * 0.5;
      const scale = radius * (0.18 + random() * height);
      return {
        position: [Math.sin(phi) * Math.cos(theta) * radius * 0.98,
                   Math.cos(phi) * radius * 0.98,
                   Math.sin(phi) * Math.sin(theta) * radius * 0.98] as Vec3,
        rotation: [phi, theta, 0] as Vec3,
        arc, scale, phase: random() * Math.PI * 2,
      };
    });
  }, [count, seed, radius, height]);
  return (
    <group>
      {arcs.map((item, index) => {
        const pulse = 0.75 + 0.25 * Math.sin(elapsedSeconds * speed * Math.PI * 2 + item.phase);
        return (
          <mesh key={index} position={item.position} rotation={item.rotation}>
            <torusGeometry args={[item.scale, radius * 0.016 * pulse, 24, 64, item.arc]}/>
            <meshBasicMaterial color={color} transparent opacity={0.45} blending={THREE.AdditiveBlending}/>
          </mesh>
        );
      })}
    </group>
  );
}

/** 行星环：确定性径向条纹生成 alpha，展开时不糊；也可换成已登记素材。 */
export function Rings({innerRadius, outerRadius, color = '#d9c19a', opacity = 0.92,
                       seed = 'rings', tilt = 0}: {
  innerRadius: number; outerRadius: number; color?: string; opacity?: number; seed?: string; tilt?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const texture = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const width = 1024;
    const data = new Uint8Array(width * 4);
    let band = 0.6 + random() * 0.4;
    for (let index = 0; index < width; index += 1) {
      if (index % Math.max(2, Math.floor(6 + random() * 40)) === 0) band = 0.25 + random() * 0.75;
      const cassini = Math.abs(index / width - 0.62) < 0.012 ? 0.08 : 1;
      const alpha = Math.max(0, Math.min(1, band * cassini));
      data[index * 4] = 255; data[index * 4 + 1] = 255; data[index * 4 + 2] = 255;
      data[index * 4 + 3] = Math.round(alpha * 255);
    }
    const map = new THREE.DataTexture(data, width, 1, THREE.RGBAFormat);
    map.wrapS = map.wrapT = THREE.RepeatWrapping;
    map.needsUpdate = true;
    return map;
  }, [seed]);
  return (
    <mesh rotation={[Math.PI / 2 + THREE.MathUtils.degToRad(tilt), elapsedSeconds * 0.01, 0]}>
      <ringGeometry args={[innerRadius, outerRadius, 160, 1]}/>
      <meshStandardMaterial map={texture} color={color} transparent opacity={opacity}
        alphaMap={texture} side={THREE.DoubleSide} depthWrite={false}/>
    </mesh>
  );
}

/** 奥尔特云：极稀疏的远距离点云，可选日球层顶气泡边界。 */
export function OortCloud({count = 2000, radius = 1800, thickness = 420, seed = 'oort',
                           color = '#8fb6ff', size = 1.8, bubble, bubbleColor = '#6fa8ff',
                           bubbleOpacity = 0.12}: {
  count?: number; radius?: number; thickness?: number; seed?: string; color?: string;
  size?: number; bubble?: number; bubbleColor?: string; bubbleOpacity?: number;
}) {
  const geometry = useMemo(() => {
    const random = seededRandom(hashSeed(seed));
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      const distance = radius + (random() - 0.5) * thickness;
      positions[index * 3] = distance * Math.sin(phi) * Math.cos(theta);
      positions[index * 3 + 1] = distance * Math.cos(phi) * 0.6;
      positions[index * 3 + 2] = distance * Math.sin(phi) * Math.sin(theta);
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return buffer;
  }, [count, radius, thickness, seed]);
  return (
    <group>
      <points geometry={geometry}>
        <pointsMaterial color={color} size={size} sizeAttenuation transparent opacity={0.7} depthWrite={false}/>
      </points>
      {bubble
        ? <mesh>
            <sphereGeometry args={[bubble, 64, 48]}/>
            <meshBasicMaterial color={bubbleColor} transparent opacity={bubbleOpacity}
              side={THREE.BackSide} depthWrite={false} blending={THREE.AdditiveBlending}/>
          </mesh>
        : null}
    </group>
  );
}

/** 彗星：核 + 尾迹；尾巴始终背向 `sunPosition`，长度随帧号呼吸。 */
export function Comet({position = [0, 0, 0] as Vec3, radius = 0.5, tailLength = 14, tailRadius = 0.9,
                       color = '#bfe6ff', sunPosition = [0, 0, 0] as Vec3, seed = 'comet', speed = 0.4}: {
  position?: Vec3; radius?: number; tailLength?: number; tailRadius?: number;
  color?: string; sunPosition?: Vec3; seed?: string; speed?: number;
}) {
  const {elapsedSeconds} = useSceneContext();
  const random = useMemo(() => seededRandom(hashSeed(seed)), [seed]);
  const jitter = useMemo(() => [(random() - 0.5) * 0.2, (random() - 0.5) * 0.2], [random]);
  const nucleus = useMemo(() => new THREE.Vector3(...position), [position]);
  const sun = useMemo(() => new THREE.Vector3(...sunPosition), [sunPosition]);
  const direction = useMemo(() => nucleus.clone().sub(sun).normalize(), [nucleus, sun]);
  const quaternion = useMemo(() => new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0), direction), [direction]);
  const breathe = 0.85 + 0.15 * Math.sin(elapsedSeconds * speed * Math.PI * 2);
  return (
    <group>
      <mesh position={position}>
        <sphereGeometry args={[radius, 24, 16]}/>
        <meshBasicMaterial color={color}/>
      </mesh>
      <mesh position={[position[0] + jitter[0], position[1] + jitter[1], position[2]]}
        quaternion={quaternion}>
        <coneGeometry args={[tailRadius * breathe, tailLength * breathe, 24, 1, true]}/>
        <meshBasicMaterial color={color} transparent opacity={0.28} side={THREE.DoubleSide}
          depthWrite={false} blending={THREE.AdditiveBlending}/>
      </mesh>
    </group>
  );
}
