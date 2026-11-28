import {memo, useEffect, useMemo, useRef} from 'react';
import * as THREE from 'three';
import {Corona, OortCloud, ParticleBelt} from '../src/code-scene/cinematic/space';
import {useFrame, useThree} from '@react-three/fiber';
import type {Look, Shot} from '../src/code-scene/cinematic/camera';
import SpaceStage from './components/space-stage';
import OrbitRing from './components/orbit-ring';
import {BODIES} from './bodies';
import {LAYOUT, positionOf} from './layout';
import {Planet, type Textures} from './world';
import {createFlight} from './flight';
import journey from './journey-plan.json';


/** 相机焦点表：天体位置固定，因此直接给 Vector3，不需要 Object3D 引用。 */
export function focusTargets(): Record<string, THREE.Vector3> {
  const targets: Record<string, THREE.Vector3> = {sun: new THREE.Vector3(0, 0, 0)};
  // 冷开场要的是「日面边缘」而不是日面正中：给相机一个偏离球心的注视点。
  targets['sun-limb'] = new THREE.Vector3(LAYOUT.sun.radius * 0.5, LAYOUT.sun.radius * 0.78, 0);
  for (const id of Object.keys(LAYOUT)) targets[id] = positionOf(id);
  return targets;
}

/** 首帧上传纹理并渲染一次，再交出 ready()：素材就绪语义与旧链路一致。 */
function FirstPaint({textures, onReady}: {textures: Textures; onReady: () => void}) {
  const gl = useThree(state => state.gl);
  const scene = useThree(state => state.scene);
  const camera = useThree(state => state.camera);
  const done = useRef(false);
  useFrame(() => {
    if (done.current) return;
    Object.values(textures).forEach(texture => gl.initTexture(texture));
    gl.render(scene, camera);
    done.current = true;
    onReady();
  }, -1);
  return null;
}

/** 需要展示纹理地标的天体；朝向由 Planet 按当前机位逐帧求解。 */
const FEATURE_BODIES = new Set(['jupiter', 'pluto']);

type Window = {startFrame: number; endFrame: number};

function FlightCamera({shots, windows, frame, look, ceresFocus}: {
  shots: Shot[]; windows: Record<string, Window>; frame: number; look: Look; ceresFocus: number}) {
  const sample = useMemo(() => createFlight(shots, windows, focusTargets()), [shots, windows]);
  const clock = useRef(frame);
  clock.current = frame;
  useFrame(({camera, gl}) => {
    const pose = sample(clock.current);
    camera.position.copy(pose.position);
    camera.quaternion.copy(pose.quaternion);
    // 后续材质钩子会把日光转入视空间，必须用本帧矩阵，不能依赖上一帧渲染的副作用。
    camera.updateMatrixWorld(true);
    const perspective = camera as THREE.PerspectiveCamera;
    // 谷神星在名称右侧，背景土星从右缘离画，给右上角章节标签留出星空。
    const filmOffset = -9 * ceresFocus;
    if (perspective.fov !== pose.fov || perspective.filmOffset !== filmOffset) {
      perspective.fov = pose.fov;
      perspective.filmOffset = filmOffset;
      perspective.updateProjectionMatrix();
    }
    // CameraRig 被替换后仍需应用 look 的曝光；镜头级曝光仅在显式声明时覆盖。
    const current = shots.find(shot => clock.current >= shot.startFrame && clock.current < shot.endFrame);
    const shotExposure = current?.exposure?.mode === 'shot' ? current.exposure?.ev : undefined;
    gl.toneMappingExposure = 2 ** (shotExposure ?? look.exposure?.ev ?? 0);
  }, -2);
  return null;
}

/** 尾镜放大光晕的可见范围，太阳模型仍使用旅程里的同一半径。 */
function DistantSunGlow({strength}: {strength: number}) {
  const glow = useMemo(() => {
    const size = 32;
    const pixels = new Uint8Array(size * size * 4).fill(255);
    for (let y = 0; y < size; y += 1) {
      for (let x = 0; x < size; x += 1) {
        const distance = Math.hypot(x + 0.5 - size / 2, y + 0.5 - size / 2) / (size / 2);
        const alpha = Math.max(0, 1 - distance) ** 2;
        pixels[(y * size + x) * 4 + 3] = Math.round(alpha * 255);
      }
    }
    const texture = new THREE.DataTexture(pixels, size, size);
    texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    return texture;
  }, []);
  useEffect(() => () => glow.dispose(), [glow]);
  return <sprite scale={[24, 24, 1]} visible={strength > 0}>
    <spriteMaterial map={glow} color="#ffd08b" transparent opacity={strength}
      depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false}/>
  </sprite>;
}

function World({textures, active, seconds, outerView, edgeApproach, ceresFocus}: {
  textures: Textures; active: string; seconds: number; outerView: number; edgeApproach: number;
  ceresFocus: number;
}) {
  const clock = {current: {seconds}};
  const structures = journey.structures;
  return <>
    <group>
      <Planet id="sun" radius={LAYOUT.sun.radius} textures={textures} clock={clock}/>
      <Corona radius={LAYOUT.sun.radius} color="#ff9a3c" intensity={0.85} power={3.1}/>
      <DistantSunGlow strength={outerView}/>
    </group>
    {Object.entries(LAYOUT).filter(([id]) => id !== 'sun').map(([id, item]) => <group key={id}>
      {item.orbit > 0 && !item.parent &&
        <OrbitRing radius={item.orbit} active={id === active || BODIES[active]?.parent === id}/>}
      {item.parent && <group position={positionOf(item.parent)}>
        <OrbitRing radius={item.orbit} active={active === id}/></group>}
      <group position={positionOf(id)}>
        <Planet id={id} radius={item.radius} textures={textures} clock={clock} ceresFocus={ceresFocus}
          faceFeature={FEATURE_BODIES.has(id)}
          detail={id === active || BODIES[active]?.parent === id}/>
      </group>
    </group>)}
    <ParticleBelt count={1000} {...structures.mainBelt} seed="main-belt"
      color="#c5bba1" size={0.065} spin={0.002} opacity={0.65}/>
    <ParticleBelt count={1800} {...structures.kuiper} seed="kuiper"
      color={outerView === 0 ? '#9fb6cf' : new THREE.Color('#9fb6cf').lerp(new THREE.Color('#f1d5ab'), outerView).getStyle()}
      size={THREE.MathUtils.lerp(0.11, 5.1, outerView) + 2.2 * edgeApproach} spin={0.001}
      opacity={THREE.MathUtils.lerp(0.6, 0.92, outerView)}/>
    <OortCloud count={7200} {...structures.oort} seed="oort" color={BODIES.oort.color} size={6.6}
      bubble={structures.heliopause.radius} bubbleColor={BODIES.heliopause.color}
      bubbleOpacity={structures.heliopause.opacity}/>
  </>;
}

/** 所有天体一直留在同一个场景图中，只移动相机；压缩轨道作为稳定空间参照。 */
export const SolarSystem = memo(function SolarSystem({textures, shots, look, active, seconds, fps,
                                                      windows, onReady}: {
  textures: Textures; shots: Shot[]; look: Look; active: string; seconds: number; fps: number;
  windows: Record<string, Window>;
  onReady: () => void;
}) {
  // 逐主体镜头使用稳定目标表，避免旧固定帧焦点切换随配音变化失效。
  const frame = seconds * fps;
  // 两层各自讲完后，尾镜才点亮同一组扁带粒子，让观众读出完整的空间关系。
  const tailStart = shots.at(-1)?.startFrame ?? windows['oort-line'].endFrame;
  const outerView = THREE.MathUtils.smoothstep(frame, tailStart, tailStart + 120);
  // 壳缘入画前以冷色柯伊伯带维持方向感。它退入背景后，蓝壳名称才出现。
  const edgeStart = windows['heliopause-line'].startFrame;
  const edgeApproach = THREE.MathUtils.smoothstep(frame, edgeStart - 75, edgeStart + 24)
    * (1 - THREE.MathUtils.smoothstep(frame, edgeStart + 90, edgeStart + 138));
  const {startFrame, endFrame} = windows['ceres-line'];
  const ceresFocus = THREE.MathUtils.smoothstep(frame, startFrame - 30, startFrame + 15)
    * (1 - THREE.MathUtils.smoothstep(frame, endFrame + 6, endFrame + 38));
  return <SpaceStage look={look} shots={shots} fov={40} background="#02050a"
    starCount={650} starSeed="solar-system">
    <FlightCamera shots={shots} windows={windows} frame={frame} look={look} ceresFocus={ceresFocus}/>
    <World textures={textures} active={active} seconds={seconds} outerView={outerView}
      edgeApproach={edgeApproach} ceresFocus={ceresFocus}/>
    <FirstPaint textures={textures} onReady={onReady}/>
  </SpaceStage>;
});
