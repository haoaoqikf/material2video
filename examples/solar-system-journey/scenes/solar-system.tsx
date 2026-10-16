import {memo, useEffect, useMemo, useRef, type RefObject} from 'react';
import {Canvas, PerspectiveCamera, THREE, useFrame, useThree} from 'm2v/code-scene';
import {BODIES} from './bodies';
import {LAYOUT, positionOf, type Pose} from './layout';
import {Planet, type Textures} from './world';

export type LiveScene = {seconds: number; pose: Pose};

function Orbit({radius, active = false, faint = false}: {radius: number; active?: boolean; faint?: boolean}) {
  const geometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(
    Array.from({length: 257}, (_, i) => new THREE.Vector3(
      Math.cos(i / 256 * Math.PI * 2) * radius, 0, Math.sin(i / 256 * Math.PI * 2) * radius))), [radius]);
  const material = useMemo(() => new THREE.LineBasicMaterial({color: active ? '#ddbd7c' : '#496b82',
    transparent: true, opacity: active ? 0.72 : faint ? 0.035 : 0.34}), [active, faint]);
  const line = useMemo(() => new THREE.LineLoop(geometry, material), [geometry, material]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => material.dispose(), [material]);
  return <primitive object={line}/>;
}

function Belt({inner, outer, spherical = false, active = false}: {
  inner: number; outer: number; spherical?: boolean; active?: boolean;
}) {
  const positions = useMemo(() => {
    const count = spherical ? 2200 : 1100;
    const p = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = inner + ((i * 73) % count) / count * (outer - inner);
      const a = i * 2.399963;
      const y = spherical ? 1 - 2 * (i + 0.5) / count : Math.sin(i * 11.7) * 0.018;
      const s = Math.sqrt(1 - y * y);
      p.set([r * s * Math.cos(a), r * y, r * s * Math.sin(a)], i * 3);
    }
    return p;
  }, [inner, outer, spherical]);
  return <points>
    <bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]}/></bufferGeometry>
    <pointsMaterial color={spherical ? '#8db1ce' : '#c5bba1'} size={spherical ? 0.5 : 0.12}
      onBeforeCompile={roundPoints}
      transparent opacity={active ? 0.7 : 0.2} depthWrite={false}/>
  </points>;
}

function roundPoints(shader: Parameters<THREE.PointsMaterial['onBeforeCompile']>[0]) {
  shader.fragmentShader = shader.fragmentShader.replace('#include <alphatest_fragment>',
    'diffuseColor.a *= 1.0 - smoothstep(0.15, 0.5, length(gl_PointCoord - vec2(0.5)));\n#include <alphatest_fragment>');
}

function Starfield() {
  const points = useMemo(() => {
    const p = new Float32Array(1700 * 3);
    for (let i = 0; i < 1700; i++) {
      const y = 1 - 2 * (i + 0.5) / 1700, a = i * 2.399963;
      const s = Math.sqrt(1 - y * y);
      p.set([800 * s * Math.cos(a), 800 * y, 800 * s * Math.sin(a)], i * 3);
    }
    return p;
  }, []);
  return <points><bufferGeometry><bufferAttribute attach="attributes-position" args={[points, 3]}/></bufferGeometry>
    <pointsMaterial color="#9caec4" size={1.2} transparent opacity={0.55} onBeforeCompile={roundPoints}/></points>;
}

function Rig({live, textures, onReady}: {live: RefObject<LiveScene>; textures: Textures; onReady: () => void}) {
  const {gl, scene, camera} = useThree();
  const ready = useRef(false);
  useFrame(() => {
    const pose = live.current.pose;
    camera.position.copy(pose.eye);
    camera.lookAt(pose.target);
    camera.updateMatrixWorld();
    if (!ready.current) {
      Object.values(textures).forEach(texture => gl.initTexture(texture));
      gl.render(scene, camera);
      ready.current = true;
      onReady();
    }
  }, -1);
  return null;
}

/** 所有天体一直留在同一个场景图中，只移动相机；压缩轨道作为稳定空间参照。 */
export const SolarSystem = memo(function SolarSystem({textures, target, live, onReady}: {
  textures: Textures; target: string; live: RefObject<LiveScene>; onReady: () => void;
}) {
  return <Canvas dpr={1} gl={{antialias: true, alpha: false, powerPreference: 'high-performance'}}>
    <color attach="background" args={['#02050a']}/>
    <PerspectiveCamera makeDefault fov={40} near={0.02} far={2000} position={[135, 175, 205]}/>
    <ambientLight intensity={0.22}/>
    <pointLight position={[0, 0, 0]} intensity={3.5} decay={0} color="#fff0d7"/>
    <Starfield/>
    {Object.entries(LAYOUT).map(([id, item]) => <group key={id}>
      {item.orbit > 0 && !item.parent && <Orbit radius={item.orbit} active={id === target || BODIES[target]?.parent === id}/>}
      {item.parent && <group position={positionOf(item.parent)}><Orbit radius={item.orbit} active={target === id}/></group>}
      <group position={positionOf(id)}>
        <Planet id={id} radius={item.radius} textures={textures} clock={live} phase={0.5}
          detail={id === target || BODIES[target]?.parent === id}/>

      </group>
    </group>)}
    <Belt inner={26} outer={32} active={target === 'ceres'}/>
    <Belt inner={86} outer={105} active={target === 'pluto'}/>
    <group rotation={[0.15, 0.2, 0.1]} scale={[1, 0.82, 1.18]}>
      {[0, Math.PI / 3, Math.PI * 2 / 3].map(angle => <group key={angle} rotation={[angle, 0, 0]}>
        <Orbit radius={132} active={target === 'heliopause'} faint/>
      </group>)}
    </group>
    <Belt inner={165} outer={210} spherical active={target === 'oort'}/>
    {[0, Math.PI / 2].map(angle => <group key={angle} rotation={[angle, 0, 0]}>
      <Orbit radius={210} active={target === 'oort'} faint/>
    </group>)}
    <Rig live={live} textures={textures} onReady={onReady}/>
  </Canvas>;
});
