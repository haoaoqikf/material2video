import {memo, useMemo, useRef} from 'react';
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

function FlightCamera({shots, windows, frame, look}: {
  shots: Shot[]; windows: Record<string, Window>; frame: number; look: Look}) {
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
    if (perspective.fov !== pose.fov) {
      perspective.fov = pose.fov;
      perspective.updateProjectionMatrix();
    }
    // CameraRig 被替换后仍需应用 look 的曝光；镜头级曝光仅在显式声明时覆盖。
    const current = shots.find(shot => clock.current >= shot.startFrame && clock.current < shot.endFrame);
    const shotExposure = current?.exposure?.mode === 'shot' ? current.exposure?.ev : undefined;
    gl.toneMappingExposure = 2 ** (shotExposure ?? look.exposure?.ev ?? 0);
  }, -2);
  return null;
}

function World({textures, active, seconds}: {
  textures: Textures; active: string; seconds: number;
}) {
  const clock = {current: {seconds}};
  const structures = journey.structures;
  return <>
    <group>
      <Planet id="sun" radius={LAYOUT.sun.radius} textures={textures} clock={clock}/>
      <Corona radius={LAYOUT.sun.radius} color="#ff9a3c" intensity={0.85} power={3.1}/>
    </group>
    {Object.entries(LAYOUT).filter(([id]) => id !== 'sun').map(([id, item]) => <group key={id}>
      {item.orbit > 0 && !item.parent &&
        <OrbitRing radius={item.orbit} active={id === active || BODIES[active]?.parent === id}/>}
      {item.parent && <group position={positionOf(item.parent)}>
        <OrbitRing radius={item.orbit} active={active === id}/></group>}
      <group position={positionOf(id)}>
        <Planet id={id} radius={item.radius} textures={textures} clock={clock}
          faceFeature={FEATURE_BODIES.has(id)}
          detail={id === active || BODIES[active]?.parent === id}/>
      </group>
    </group>)}
    <ParticleBelt count={1000} {...structures.mainBelt} seed="main-belt"
      color="#c5bba1" size={0.065} spin={0.002} opacity={0.65}/>
    <ParticleBelt count={1800} {...structures.kuiper} seed="kuiper"
      color="#9fb6cf" size={0.11} spin={0.001} opacity={0.6}/>
    <OortCloud count={7200} {...structures.oort} seed="oort" color="#c9d6df" size={5.2}
      bubble={structures.heliopause.radius} bubbleColor="#5f97d8" bubbleOpacity={structures.heliopause.opacity}/>
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
  return <SpaceStage look={look} shots={shots} fov={40} background="#02050a"
    starCount={650} starSeed="solar-system">
    <FlightCamera shots={shots} windows={windows} frame={seconds * fps} look={look}/>
    <World textures={textures} active={active} seconds={seconds}/>
    <FirstPaint textures={textures} onReady={onReady}/>
  </SpaceStage>;
});
