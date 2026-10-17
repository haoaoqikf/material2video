import {memo, useMemo, useRef} from 'react';
import {
  Atmosphere, CameraRig, Canvas, Comet, Corona, LookProvider, OortCloud, ParticleBelt,
  PerspectiveCamera, PostFX, Prominence, Rings, Starfield, SunSurface, THREE, useFrame, useThree,
  type Look, type Shot,
} from 'm2v/code-scene';
import {BODIES} from './bodies';
import {LAYOUT, positionOf} from './layout';
import {Planet, type Textures} from './world';

/** 相机焦点表：天体位置固定，因此直接给 Vector3，不需要 Object3D 引用。 */
export function focusTargets(): Record<string, THREE.Vector3> {
  const targets: Record<string, THREE.Vector3> = {sun: new THREE.Vector3(0, 0, 0)};
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

function World({textures, targets, active, seconds}: {
  textures: Textures; targets: Record<string, THREE.Vector3>; active: string; seconds: number;
}) {
  const clock = {current: {seconds}};
  return <>
    <ambientLight intensity={0.2}/>
    <pointLight position={[0, 0, 0]} intensity={4.2} decay={0} color="#fff0d7"/>
    <Starfield count={2200} radius={900} seed="solar-system" size={1.6} opacity={0.6}/>
    <group>
      <SunSurface radius={LAYOUT.sun.radius} color="#ffb44d" hotColor="#fff1c2" granulation={0.65}/>
      <Corona radius={LAYOUT.sun.radius} color="#ff9a3c" intensity={0.85} power={3.1}/>
      <Prominence radius={LAYOUT.sun.radius} color="#ff7a3c" count={6} height={1.1}/>
    </group>
    {Object.entries(LAYOUT).filter(([id]) => id !== 'sun').map(([id, item]) => <group key={id}>
      {item.orbit > 0 && !item.parent &&
        <Orbit radius={item.orbit} active={id === active || BODIES[active]?.parent === id}/>}
      {item.parent && <group position={positionOf(item.parent)}>
        <Orbit radius={item.orbit} active={active === id}/></group>}
      <group position={positionOf(id)}>
        <Planet id={id} radius={item.radius} textures={textures} clock={clock} phase={0.5}
          detail={id === active || BODIES[active]?.parent === id}/>
        {id === 'earth' && <Atmosphere radius={item.radius} color="#4b9dff" intensity={1.05}/>}
        {id === 'saturn' && <Rings innerRadius={item.radius * 1.25} outerRadius={item.radius * 1.75}
          color="#d9c19a" opacity={0.92} seed="saturn-rings" tilt={26.7}/>}
      </group>
    </group>)}
    <ParticleBelt count={1400} innerRadius={26} outerRadius={33} thickness={0.5} seed="main-belt"
      color="#c5bba1" size={0.16} spin={0.02}/>
    <ParticleBelt count={2200} innerRadius={86} outerRadius={106} thickness={2.4} seed="kuiper"
      color="#9fb6cf" size={0.22} spin={0.012}/>
    <OortCloud count={2600} radius={185} thickness={55} seed="oort" color="#8fb6ff" size={0.5}
      bubble={132} bubbleColor="#6fa8ff" bubbleOpacity={0.1}/>
    <Comet position={[96, 12, 150]} radius={0.5} tailLength={22} tailRadius={1.4} sunPosition={[0, 0, 0]}/>
    <CameraRig targets={targets} target={[0, 0, 0]} near={0.02} far={4000}/>
    <PostFX/>
  </>;
}

/** 所有天体一直留在同一个场景图中，只移动相机；压缩轨道作为稳定空间参照。 */
export const SolarSystem = memo(function SolarSystem({textures, shots, look, active, seconds, onReady}: {
  textures: Textures; shots: Shot[]; look: Look; active: string; seconds: number; onReady: () => void;
}) {
  const targets = useMemo(() => focusTargets(), []);
  return <Canvas dpr={1} gl={{antialias: false, alpha: false, powerPreference: 'high-performance'}}>
    <color attach="background" args={['#02050a']}/>
    <PerspectiveCamera makeDefault fov={40} near={0.02} far={4000} position={[3.4, 0.35, 1.0]}/>
    <LookProvider look={look} shots={shots}>
      <World textures={textures} targets={targets} active={active} seconds={seconds}/>
      <FirstPaint textures={textures} onReady={onReady}/>
    </LookProvider>
  </Canvas>;
});
