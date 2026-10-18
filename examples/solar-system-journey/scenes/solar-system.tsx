import {memo, useMemo, useRef} from 'react';
import {
  CameraRig, Canvas, Comet, Corona, LookProvider, OortCloud, ParticleBelt,
  PerspectiveCamera, PostFX, Prominence, Starfield, THREE, activeShot, useFrame, useThree,
  type Look, type Shot,
} from 'm2v/code-scene';
import {BODIES} from './bodies';
import {LAYOUT, positionOf} from './layout';
import {Planet, type Textures} from './world';

type FocusTarget = THREE.Vector3 | (() => THREE.Vector3);

/** 相机焦点表：天体位置固定，因此直接给 Vector3，不需要 Object3D 引用。 */
export function focusTargets(): Record<string, THREE.Vector3> {
  const targets: Record<string, THREE.Vector3> = {sun: new THREE.Vector3(0, 0, 0)};
  // 冷开场要的是「日面边缘」而不是日面正中：给相机一个偏离球心的注视点。
  targets['sun-limb'] = new THREE.Vector3(LAYOUT.sun.radius * 0.5, LAYOUT.sun.radius * 0.78, 0);
  for (const id of Object.keys(LAYOUT)) targets[id] = positionOf(id);
  return targets;
}

function Orbit({radius, active = false, faint = false}: {radius: number; active?: boolean; faint?: boolean}) {
  const geometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(
    Array.from({length: 257}, (_, i) => new THREE.Vector3(
      Math.cos(i / 256 * Math.PI * 2) * radius, 0, Math.sin(i / 256 * Math.PI * 2) * radius))), [radius]);
  const material = useMemo(() => new THREE.LineBasicMaterial({color: active ? '#ddbd7c' : '#496b82',
    transparent: true, opacity: active ? 0.72 : faint ? 0.035 : 0.3}), [active, faint]);
  const line = useMemo(() => new THREE.LineLoop(geometry, material), [geometry, material]);
  return <primitive object={line}/>;
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
const SATURN_SHOT = 'saturn-hero';

function World({textures, targets, active, seconds, shots, fps}: {
  textures: Textures; targets: Record<string, FocusTarget>; active: string; seconds: number;
  shots: Shot[]; fps: number;
}) {
  const clock = {current: {seconds}};
  const frame = Math.round(seconds * fps);
  const shot = activeShot(shots, frame);
  const saturnShot = shots.find(item => item.id === SATURN_SHOT);
  const saturnPhase = !saturnShot || frame < saturnShot.startFrame ? 0
    : frame >= saturnShot.endFrame ? 1
      : (frame - saturnShot.startFrame) / Math.max(1, saturnShot.endFrame - saturnShot.startFrame);
  return <>
    <ambientLight intensity={0.40}/>
    {/* 点光不再把远处天体照成白盘：降低强度后月球与卫星才留得住纹理。 */}
    <pointLight position={[0, 0, 0]} intensity={1.9} decay={0} color="#fff0d7"/>
    {/* 星点收小收暗：之前 2200 颗 1.6px 被 Bloom 糊成星云，深空变成了蓝雾。 */}
    <Starfield count={900} radius={900} seed="solar-system" size={0.9} opacity={0.28}/>
    <group>
      <Planet id="sun" radius={LAYOUT.sun.radius} textures={textures} clock={clock}/>
      <Corona radius={LAYOUT.sun.radius} color="#ff9a3c" intensity={0.85} power={3.1}/>
      <Prominence radius={LAYOUT.sun.radius} color="#ff7a3c" count={4} height={0.32}/>
      {/* 耀斑：更短更亮的弧，与日珥同一几何，不引入新的时间源。 */}
      <Prominence radius={LAYOUT.sun.radius} color="#ffe2a8" count={3} seed="solar-flare" height={0.1}/>
    </group>
    {Object.entries(LAYOUT).filter(([id]) => id !== 'sun').map(([id, item]) => <group key={id}>
      {item.orbit > 0 && !item.parent &&
        <Orbit radius={item.orbit} active={id === active || BODIES[active]?.parent === id}/>}
      {item.parent && <group position={positionOf(item.parent)}>
        <Orbit radius={item.orbit} active={active === id}/></group>}
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
    <CameraRig targets={targets} target={[0, 0, 0]} near={0.02} far={4000}/>
    <PostFX/>
  </>;
}

/** 所有天体一直留在同一个场景图中，只移动相机；压缩轨道作为稳定空间参照。 */
export const SolarSystem = memo(function SolarSystem({textures, shots, look, active, seconds, fps, onReady}: {
  textures: Textures; shots: Shot[]; look: Look; active: string; seconds: number; fps: number;
  onReady: () => void;
}) {
  // 冰巨星段先讲天王星、再讲海王星；同一连续镜头内按旁白时间把焦点从前者拉到后者。
  const secondsRef = useRef(seconds);
  secondsRef.current = seconds;
  const targets = useMemo<Record<string, FocusTarget>>(() => {
    const table: Record<string, FocusTarget> = focusTargets();
    // 每一段先让旁白提到的内/外行星进入画面，再在同一连续镜头内拉焦到下一颗。
    const pull = (first: string, second: string, start: number, frames: number) => () => {
      const blend = Math.min(1, Math.max(0, (secondsRef.current * fps - start) / frames));
      return new THREE.Vector3().lerpVectors(positionOf(first), positionOf(second), blend);
    };
    table['inner-focus'] = pull('mercury', 'venus', 635, 24);
    table['ice-focus'] = pull('uranus', 'neptune', 2550, 24);
    return table;
  }, [fps]);
  return <Canvas dpr={1} gl={{antialias: false, alpha: false, powerPreference: 'high-performance'}}>
    <color attach="background" args={['#02050a']}/>
    <PerspectiveCamera makeDefault fov={40} near={0.02} far={4000} position={[3.4, 0.35, 1.0]}/>
    <LookProvider look={look} shots={shots}>
      <World textures={textures} targets={targets} active={active} seconds={seconds}
        shots={shots} fps={fps}/>
      <FirstPaint textures={textures} onReady={onReady}/>
    </LookProvider>
  </Canvas>;
});
