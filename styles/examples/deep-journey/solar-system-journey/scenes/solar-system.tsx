import {memo, useMemo, useRef} from 'react';
import {
  Comet, Corona, OortCloud, ParticleBelt, Prominence, THREE, useFrame, useThree,
  type Look, type Shot,
} from 'm2v/code-scene';
import SpaceStage from 'm2v/style/components/space-stage';
import OrbitRing from 'm2v/style/components/orbit-ring';
import {BODIES} from './bodies';
import {LAYOUT, positionOf} from './layout';
import {Planet, type Textures} from './world';
import {createFlight} from './flight';


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

function World({textures, active, seconds, fps, saturnWindow}: {
  textures: Textures; active: string; seconds: number;
  fps: number; saturnWindow?: Window;
}) {
  const clock = {current: {seconds}};
  const frame = Math.round(seconds * fps);
  // 土星环的展开跟随土星旁白窗口，而不是整个 hero 镜头：过场中段环还没有张开。
  const saturnPhase = !saturnWindow || frame < saturnWindow.startFrame ? 0
    : frame >= saturnWindow.endFrame ? 1
      : (frame - saturnWindow.startFrame) / Math.max(1, saturnWindow.endFrame - saturnWindow.startFrame);
  return <>
    <group>
      <Planet id="sun" radius={LAYOUT.sun.radius} textures={textures} clock={clock}/>
      <Corona radius={LAYOUT.sun.radius} color="#ff9a3c" intensity={0.85} power={3.1}/>
      <Prominence radius={LAYOUT.sun.radius} color="#ff7a3c" count={4} height={0.32}/>
      {/* 耀斑：更短更亮的弧，与日珥同一几何，不引入新的时间源。 */}
      <Prominence radius={LAYOUT.sun.radius} color="#ffe2a8" count={3} seed="solar-flare" height={0.1}/>
    </group>
    {Object.entries(LAYOUT).filter(([id]) => id !== 'sun').map(([id, item]) => <group key={id}>
      {item.orbit > 0 && !item.parent &&
        <OrbitRing radius={item.orbit} active={id === active || BODIES[active]?.parent === id}/>}
      {item.parent && <group position={positionOf(item.parent)}>
        <OrbitRing radius={item.orbit} active={active === id}/></group>}
      <group position={positionOf(id)}>
        <Planet id={id} radius={item.radius} textures={textures} clock={clock}
          phase={id === 'saturn' ? saturnPhase : 0.5}
          faceFeature={FEATURE_BODIES.has(id)}
          detail={id === active || BODIES[active]?.parent === id}/>
      </group>
    </group>)}
    <ParticleBelt count={1400} innerRadius={26} outerRadius={33} thickness={0.5} seed="main-belt"
      color="#c5bba1" size={0.09} spin={0.02}/>
    <ParticleBelt count={2200} innerRadius={86} outerRadius={106} thickness={2.4} seed="kuiper"
      color="#9fb6cf" size={0.14} spin={0.012}/>
    <OortCloud count={2600} radius={185} thickness={55} seed="oort" color="#a8c8ff" size={1.1}
      bubble={132} bubbleColor="#5f97d8" bubbleOpacity={0.65}/>
    <Comet position={[96, 12, 150]} radius={0.5} tailLength={22} tailRadius={1.4} sunPosition={[0, 0, 0]}/>
  </>;
}

/** 所有天体一直留在同一个场景图中，只移动相机；压缩轨道作为稳定空间参照。 */
export const SolarSystem = memo(function SolarSystem({textures, shots, look, active, seconds, fps,
                                                      windows, saturnWindow, onReady}: {
  textures: Textures; shots: Shot[]; look: Look; active: string; seconds: number; fps: number;
  windows: Record<string, Window>;
  saturnWindow?: {startFrame: number; endFrame: number}; onReady: () => void;
}) {
  // 逐主体镜头使用稳定目标表，避免旧固定帧焦点切换随配音变化失效。
  return <SpaceStage look={look} shots={shots} fov={40} background="#02050a"
    starCount={900} starSeed="solar-system">
    <FlightCamera shots={shots} windows={windows} frame={seconds * fps} look={look}/>
    <World textures={textures} active={active} seconds={seconds}
      fps={fps} saturnWindow={saturnWindow}/>
    <FirstPaint textures={textures} onReady={onReady}/>
  </SpaceStage>;
});
