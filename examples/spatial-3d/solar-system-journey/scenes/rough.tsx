/** 仅用于低成本全片动态粗预演；与正式片共用实际运动求值器，不用于正式交付。 */
import {useEffect, useMemo} from 'react';
import * as THREE from 'three';
import {Canvas} from '../src/code-scene/canvas';
import {PerspectiveCamera} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import {useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import type {Shot} from '../src/code-scene/cinematic/camera';
import {LAYOUT, positionOf} from './layout';
import {createFlight} from './flight';
import {BODIES} from './bodies';

function Camera({sample, frame, ready}: {sample: ReturnType<typeof createFlight>; frame: number; ready: () => void}) {
  useEffect(ready, [ready]);
  useFrame(({camera}) => {
    const pose = sample(frame);
    camera.position.copy(pose.position); camera.quaternion.copy(pose.quaternion);
    const p = camera as THREE.PerspectiveCamera;
    p.fov = pose.fov; p.updateProjectionMatrix();
  });
  return null;
}

export default function Rough(config: CodeSceneProps) {
  const context = useSceneContext();
  const frame = context.elapsedSeconds * 60;
  const shots = config.props.shots as Shot[];
  const sample = useMemo(() => createFlight(shots, config.segmentWindows,
    Object.fromEntries(Object.keys(LAYOUT).map(id => [id, positionOf(id)]))), [shots, config.segmentWindows]);
  const shot = shots.find(s => frame >= s.startFrame && frame < s.endFrame);
  return <div style={{width: config.width, height: config.height, background: '#02050a', color: '#eee'}}>
    <Canvas><PerspectiveCamera makeDefault near={0.02} far={4000}/>
      <ambientLight intensity={0.8}/><pointLight intensity={2} decay={0}/>
      {Object.entries(LAYOUT).map(([id, item]) => <group key={id} position={positionOf(id)}>
        <mesh><sphereGeometry args={[item.radius, 24, 16]}/>
          <meshStandardMaterial color={BODIES[id]?.color ?? '#c9aa84'}/></mesh>
        {id === 'saturn' && <mesh rotation={[1.1, 0, 0]}><ringGeometry args={[item.radius*1.24,item.radius*2.27,48]}/>
          <meshBasicMaterial color="#c8b895" side={THREE.DoubleSide}/></mesh>}
      </group>)}
      <Camera sample={sample} frame={frame} ready={context.ready}/>
    </Canvas>
    <div style={{position:'absolute',top:16,left:24,fontSize:22}}>动态粗预演 · 临时材质 · 15 fps / {context.elapsedSeconds.toFixed(1)} 秒</div>
    <div style={{position:'absolute',bottom:20,left:24,fontSize:28}}>{BODIES[shot?.target ?? 'sun']?.name ?? shot?.target}</div>
  </div>;
}
