/**
 * 画面后期与 look 参数：具名调色档、确定性颗粒与 `PostFX`。
 *
 * 后期只作用于 canvas，不影响共享字幕 DOM 层；grain 用「固定种子 + 帧号」的
 * 确定性哈希，跨机器、跨次运行一致。
 */
import {useRef, type ReactNode} from 'react';
import * as THREE from 'three';
import {useFrame, useThree} from '@react-three/fiber';
import {
  Bloom, BrightnessContrast, ChromaticAberration, DepthOfField, EffectComposer,
  HueSaturation, Vignette, wrapEffect,
} from '@react-three/postprocessing';
import {BlendFunction, Effect} from 'postprocessing';
import {
  SHOT_BLEND_FRAMES, ease, focusDistanceAt, hashSeed, useLook,
  type Look, type LutName, type PostSettings, type Shot,
} from './camera';

/** 内置调色：`lut` 是**具名档**而不是外部 .cube 文件，录制期不取外网也不读作品目录。 */
export const GRADES: Record<LutName, {hue: number; saturation: number; brightness: number; contrast: number}> = {
  'neutral': {hue: 0, saturation: 0, brightness: 0, contrast: 0},
  'deep-space': {hue: 0.01, saturation: 0.03, brightness: -0.04, contrast: 0.06},
  'teal-amber': {hue: -0.03, saturation: 0.12, brightness: 0, contrast: 0.18},
  'warm-film': {hue: 0.05, saturation: -0.05, brightness: 0.02, contrast: 0.1},
};
export const LUT_NAMES = Object.keys(GRADES) as LutName[];

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
  const {look, shot, shots, frame} = useLook();
  const camera = useThree(state => state.camera);
  const settings = resolvePost(look, shot);
  const grade = GRADES[settings.lut] ?? GRADES.neutral;
  const grain = useRef<GrainEffect>(null);
  // 焦点拉移：镜头内按进度插值，再按相机近远裁剪面归一化成 DOF 的 0–1 距离。
  const span = Math.max(1, (shot?.endFrame ?? 1) - (shot?.startFrame ?? 0));
  const progress = shot ? (frame - shot.startFrame) / span : 0;
  const index = shot ? shots.indexOf(shot) : -1;
  const previous = index > 0 ? shots[index - 1] : null;
  const blendRaw = shot ? (frame - shot.startFrame + 1) / SHOT_BLEND_FRAMES : 1;
  const blend = previous && !shot?.cut && !previous.cut
    ? ease('easeInOutSine', Math.min(1, Math.max(0, blendRaw))) : 1;
  const world = focusDistanceAt(shot, progress);
  const previousWorld = previous ? focusDistanceAt(previous, 1) : null;
  const blendedWorld = world === null ? (previousWorld ?? null)
    : previousWorld === null ? world : previousWorld + (world - previousWorld) * blend;
  const near = camera instanceof THREE.PerspectiveCamera ? camera.near : 0.1;
  const far = camera instanceof THREE.PerspectiveCamera ? camera.far : 1000;
  // postprocessing 的 focusDistance / focusRange 都以**世界单位**计。之前把焦点
  // 归一到 [0,1] 再喂进去，焦点实际落在 1 厘米处，整幅画面（包括月球）全被糊掉。
  const focusWorld = blendedWorld === null ? 30 : blendedWorld;
  const focusDistance = Math.min(far * 0.9, Math.max(near * 2, focusWorld));
  const focusRange = Math.max(0.35, focusDistance * 0.3);
  useFrame(() => {
    const effect = grain.current;
    if (effect) effect.seed = hashSeed(shot?.id ?? 'look') % 4096 + frame;
  });
  if (!enabled) return null;
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {settings.bloom > 0
        ? <Bloom intensity={settings.bloom} luminanceThreshold={0.82} luminanceSmoothing={0.12} mipmapBlur/>
        : <></>}
      {settings.dof > 0
        ? <DepthOfField focusDistance={focusDistance} focusRange={focusRange}
            bokehScale={2 + settings.dof * 4}/>
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
