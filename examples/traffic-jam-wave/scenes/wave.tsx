/**
 * 方向分离：车辆继续向前，低速区域却沿车队向后移动。
 *
 * 红色区域是当前的低速带，蓝色箭头只表示低速带的移动方向；两者方向不同是本幕的论点。
 * 箭头与静止的车道线分开摆放，避免被读成车辆在倒车。
 */
import {useLayoutEffect, useRef} from 'react';
import {gsap, type CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, useNarration, useReady} from './stage';
import {ArcPath, CarMark, LoopRoad} from './parts';
import {loopPoint, sample, slowCenter} from './traffic';

const CENTER = {x: 540, y: 880};
const FOCUS = 7;

export default function Wave(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const simStart = Number(props.props.simStart ?? 9);
  // 传播过程放慢到 0.62 倍，让「向后退」在手机上看得清；采样仍走同一份数据。
  const sim = simStart + clock.elapsedSeconds * 0.62;
  const cars = sample('high', sim);
  const slow = slowCenter(cars);
  const revealed = clock.spoken('wave-back-1');
  const arrow = useRef<SVGGElement>(null);

  useLayoutEffect(() => {
    if (!revealed || !arrow.current) return;
    gsap.fromTo(arrow.current, {opacity: 0, scale: 0.86}, {opacity: 1, scale: 1, duration: 0.6,
      ease: 'power2.out', transformOrigin: '50% 50%'});
  }, [revealed]);

  const ghost = [3, 2.2, 1.4].map(back => {
    const value = slowCenter(sample('high', Math.max(0, sim - back)));
    return value === null ? null : {back, point: loopPoint(value)};
  }).filter(Boolean) as {back: number; point: {x: number; y: number}}[];
  const focusCar = cars[FOCUS - 1];
  const slowPoint = slow === null ? null : loopPoint(slow);
  const OUT = 1.13;
  const tip = slow === null ? null : loopPoint(slow - 210);
  // 文字放进取景框内侧的空地，避免压住红带上的车辆。
  const midPoint = slowPoint === null ? null
    : {x: CENTER.x + slowPoint.x * 0.82, y: CENTER.y + slowPoint.y * 0.82 + 8};

  return (
    <Stage props={props} title="车辆向前，拥堵向后"
      lead="所有车都在沿环路前进，变化的是低速区域的位置">
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        <LoopRoad cx={CENTER.x} cy={CENTER.y}/>
        {slow !== null && <ArcPath cx={CENTER.x} cy={CENTER.y} fromS={slow - 115} lengthS={230}
          stroke={COLOR.dangerSoft} width={78} opacity={0.9}/>}
        {ghost.map(item => (
          <circle key={item.back} cx={CENTER.x + item.point.x} cy={CENTER.y + item.point.y}
            r={7} fill={COLOR.accent} opacity={0.16 + 0.16 * (1 - item.back / 3.6)}/>
        ))}
        {cars.map(car => <CarMark key={car.id} x={CENTER.x + car.x} y={CENTER.y + car.y}
          heading={car.heading} braking={car.brake} focus={car.id === FOCUS} label={car.id} scale={0.95}/>)}
        {focusCar && <g>
          <text x={CENTER.x + focusCar.x} y={CENTER.y + focusCar.y - 34} textAnchor="middle"
            fontSize={SIZE.note} fontWeight={700} fill={COLOR.accent}>{`${FOCUS} 号车`}</text>
        </g>}
        {revealed && slow !== null && tip !== null && midPoint !== null && <g ref={arrow}>
          <ArcPath cx={CENTER.x} cy={CENTER.y} fromS={slow + 210} lengthS={-420}
            stroke={COLOR.accent} width={7} opacity={0.9} dash="16 12" expand={OUT}/>
          <path d="M-18,-13 L18,0 L-18,13 Z" fill={COLOR.accent}
            transform={`translate(${CENTER.x + tip.x * OUT} ${CENTER.y + tip.y * OUT})
              rotate(${(tip.heading * 180) / Math.PI + 180})`}/>
          <text x={midPoint.x} y={midPoint.y} textAnchor="middle" fontSize={SIZE.note + 2}
            fontWeight={700} fill={COLOR.accent}>拥堵传播</text>
        </g>}
      </svg>

      <div style={{position: 'absolute', left: 96, top: 1432, right: 96, display: 'flex',
        justifyContent: 'space-between', alignItems: 'center'}}>
        <div style={{fontSize: SIZE.body, color: COLOR.ink}}>
          <span style={{fontWeight: 700}}>车辆前进</span>
          <span style={{color: COLOR.muted, marginLeft: 12}}>沿环路 →</span>
        </div>
        <div style={{fontSize: SIZE.body, color: COLOR.accent, opacity: revealed ? 1 : 0.3}}>
          <span style={{fontWeight: 700}}>低速区域</span>
          <span style={{marginLeft: 12}}>向后移动 ←</span>
        </div>
      </div>
      <div style={{position: 'absolute', left: 96, top: contentBottom(props) - 22, right: 96,
        fontSize: SIZE.note, color: COLOR.muted, display: 'flex', justifyContent: 'space-between'}}>
        <span>{`${cars.filter(car => car.brake).length} 辆车亮着制动灯`}</span>
        <span>{slow === null ? '低速区域正在恢复' : '红带只标出当前的低速区域'}</span>
      </div>
    </Stage>
  );
}
