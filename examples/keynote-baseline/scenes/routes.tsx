/**
 * 三维演示：四条候选路线怎样按条件收敛到一条。
 *
 * 场景用 React Three Fiber 与 Drei 搭：一条起点、四条曲线路径、四个终点。三条旁白
 * 分别对应「全部候选」「按预算排除两条」「按时间选出当前更合适的一条，另一条留作备选」。
 * 相位在 Canvas 之外算好再传进去——录制页的上下文不跨渲染器边界。
 */
import {useMemo, useRef} from 'react';
import {Canvas, Float, PerspectiveCamera, Stars, THREE, useFrame, type CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, useNarration, useReady} from './stage';

const START = [-7.6, 0, 0] as const;
//: 候选路线本身不带颜色：金色与蓝色是**筛选结果**，一开始就上色等于提前宣布答案。
const CANDIDATE = '#6f7d8c';
const ROUTES = [
  {name: '路线一', end: [6.6, 2.9, 1.2] as const},
  {name: '路线二', end: [6.9, 0.1, -1.3] as const},
  {name: '路线三', end: [6.3, -2.6, 0.9] as const},
  {name: '路线四', end: [7.1, -4.4, -0.9] as const},
];

export default function Routes(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const all = clock.progress('choice-world-0');
  const budget = clock.progress('choice-world-1');
  const timing = clock.progress('choice-world-2');

  return (
    <Stage props={props} title="四条候选，怎样收敛到一条" note="路径不是实际测量，只展示筛选过程">
      <div style={{position: 'absolute', left: 130, top: 250, width: props.width - 260,
        height: contentBottom(props) - 270}}>
        <Canvas dpr={1} gl={{antialias: true}} style={{background: 'transparent'}}>
          <PerspectiveCamera makeDefault position={[0, 0, 12]} fov={45}/>
          <Stars radius={70} depth={40} count={420} factor={3} saturation={0} fade speed={0.4}/>
          <ambientLight intensity={0.9}/>
          <directionalLight position={[4, 6, 8]} intensity={1.2}/>
          <Float speed={1.1} rotationIntensity={0.1} floatIntensity={0.25}>
            <Grove all={all} budget={budget} timing={timing}/>
          </Float>
        </Canvas>
        <div style={{position: 'absolute', left: 24, top: 14, fontSize: SIZE.note, color: COLOR.muted}}>
          起点在左，终点在右
        </div>
        <div style={{position: 'absolute', right: 24, bottom: 18, display: 'flex', gap: 26, fontSize: SIZE.note}}>
          <Legend color={COLOR.accent} label="当前选定"/>
          <Legend color={COLOR.alt} label="保留备选"/>
          <Legend color="#5b6675" label="条件不符"/>
        </div>
      </div>
      <div style={{position: 'absolute', left: 130, top: contentBottom(props) - 56, fontSize: SIZE.lead}}>
        筛选依据是明确的需要，不是动画替你证明哪个更好
      </div>
    </Stage>
  );
}

function Legend({color, label}: {color: string; label: string}) {
  return (
    <span style={{display: 'inline-flex', alignItems: 'center', gap: 10, color: COLOR.muted}}>
      <span style={{width: 26, height: 6, borderRadius: 3, background: color}}/>{label}
    </span>
  );
}

function Grove({all, budget, timing}: {all: number; budget: number; timing: number}) {
  const group = useRef<THREE.Group>(null);
  const routes = useMemo(() => ROUTES.map(route => {
    const start = new THREE.Vector3(...START);
    const end = new THREE.Vector3(...route.end);
    const bend = new THREE.Vector3((start.x + end.x) / 2, end.y * 0.25, end.z + (end.y > 0 ? 1.6 : -1.6));
    return {...route, curve: new THREE.CatmullRomCurve3([start, bend, end])};
  }), []);
  // 缓慢摆动而不是持续自转：角度一直在变会让「哪条被选中」读不出来。
  useFrame(state => {
    if (group.current) group.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.22) * 0.16;
  });
  return (
    <group ref={group}>
      <mesh position={[...START]}>
        <sphereGeometry args={[0.3, 24, 24]}/>
        <meshBasicMaterial color={COLOR.ink}/>
      </mesh>
      {routes.map((route, index) => {
        const excluded = index > 1 ? Math.min(1, budget * 1.4) : 0;
        const chosen = index === 0 ? Math.min(1, Math.max(0, timing * 1.6 - 0.2)) : 0;
        const kept = index === 1 ? Math.min(1, Math.max(0, timing * 1.6 - 0.6)) : 0;
        const picked = chosen > 0.4 ? COLOR.accent : kept > 0.4 ? COLOR.alt : CANDIDATE;
        return (
          <group key={route.name}>
            <mesh>
              <tubeGeometry args={[route.curve, 96, chosen > 0.4 && index === 0 ? 0.1 : 0.07, 14, false]}/>
              {/* 被排除的路线压到 0.16 而不是消失：观众仍要看得见「排除了哪两条」。 */}
              <meshBasicMaterial color={picked} transparent
                opacity={Math.max(0.16, Math.min(1, all * 1.6 - index * 0.1) * (1 - excluded * 0.8))}/>
            </mesh>
            <mesh position={[...route.end]}>
              <sphereGeometry args={[chosen > 0.4 && index === 0 ? 0.42 : 0.3, 28, 28]}/>
              <meshBasicMaterial color={picked} transparent opacity={Math.max(0.2, 1 - excluded * 0.8)}/>
            </mesh>
          </group>
        );
      })}
    </group>
  );
}
