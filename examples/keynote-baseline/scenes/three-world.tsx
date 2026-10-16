import {useMemo} from 'react';
import {Canvas, PerspectiveCamera, THREE, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

const ends = [-3,-1,1,3];
function Route({x,color,opacity}: {x: number;color: string;opacity: number}) {
  const rotation = useMemo(()=>new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0,1,0),new THREE.Vector3(x,0,-4).normalize()),[x]);
  return <group>
    <mesh position={[x/2,0,0]} quaternion={rotation}>
      <cylinderGeometry args={[0.045,0.045,Math.hypot(x,4),12]}/>
      <meshStandardMaterial color={color} transparent opacity={opacity}/>
    </mesh>
    <mesh position={[x,0,-2]}><sphereGeometry args={[0.16,20,16]}/><meshStandardMaterial color={color} transparent opacity={opacity}/></mesh>
  </group>;
}
export default function ChoiceWorld({fps,segmentWindows,theme}: CodeSceneProps) {
  const {ready,elapsedSeconds} = useSceneContext();
  const windows = Object.values(segmentWindows).sort((a,b)=>a.startFrame-b.startFrame);
  const frame = elapsedSeconds*fps;
  const phase = frame >= (windows[2]?.startFrame ?? Infinity) ? 2 : frame >= (windows[1]?.startFrame ?? Infinity) ? 1 : 0;
  const w = windows[phase];
  const progress = w ? Math.max(0,Math.min(1,(frame-w.startFrame)/Math.min(fps*3,w.endFrame-w.startFrame))) : 0;
  const background = theme === 'light' ? '#f5f7fb' : '#111720';
  const ink = theme === 'light' ? '#172434' : '#edf4fc';
  return <div style={{height: 920,color: ink,fontFamily: 'Noto Sans SC'}}>
    <div style={{fontSize: 38,padding: '25px 40px',textAlign: 'center'}}>{['四条候选，先明确需要','预算筛选，保留两条','时间匹配，选定一条'][phase]}</div>
    <div style={{height: 590}}>
      <Canvas onCreated={()=>ready()} dpr={1}>
        <PerspectiveCamera makeDefault position={[0,7,7]} rotation={[-0.9,0,0]} fov={44}/>
        <color attach="background" args={[background]}/>
        <ambientLight intensity={1.5}/><directionalLight position={[2,6,3]} intensity={2}/>
        <gridHelper args={[10,10,'#324459','#243346']} position={[0,-0.2,0]}/>
        <mesh position={[0,0,2]}><sphereGeometry args={[0.19,20,16]}/><meshStandardMaterial color="#f7c85b"/></mesh>
        {ends.map((x,i)=><Route key={x} x={x} color={phase===2 && i===2 ? '#f7c85b' : '#5aafff'}
          opacity={phase>=1 && (i===0 || i===3) ? 0.13 : phase===2 && i===1 ? 0.4 : 1}/>)}
        {phase===2 && <mesh position={[progress,0.15,2-4*progress]}><sphereGeometry args={[0.12,16,12]}/><meshStandardMaterial color="#fff0b3" emissive="#f7c85b" emissiveIntensity={0.5}/></mesh>}
      </Canvas>
    </div>
    <div style={{display: 'flex',justifyContent: 'space-around',fontSize: 28,padding: '10px 18px'}}>
      {['超预算','可行备选','时间合适','超预算'].map((label,i)=><div key={i} style={{color: phase===2 && i===2 ? '#f7c85b' : ink,opacity: phase>0 && (i===0 || i===3) ? 0.4 : 1}}>{phase===0 ? `候选 ${i+1}` : label}</div>)}
    </div>
    <div style={{textAlign: 'center',fontSize: 30,marginTop: 34}}>筛选依据：{phase===0 ? '预算与时间' : phase===1 ? '先满足预算' : '再匹配时间，保留备选'}</div>
    <div style={{textAlign: 'center',fontSize: 26,marginTop: 26,color: '#91a8be'}}>路径仅为示意，不代表实际测量</div>
  </div>;
}
