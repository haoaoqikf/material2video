/**
 * 拉远：把开场的局部路段放回一条完整环路。
 *
 * 环路没有红绿灯、出口和事故点。镜头从顶部连续拉远，车辆位置直接取自轨迹数据；
 * 拉远只是观察尺度的变化，不改变任何车辆身份。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, mix, useNarration, useReady} from './stage';
import {CarMark, LoopRoad} from './parts';
import {TRAFFIC, loopPoint, sample} from './traffic';

const CENTER = {x: 540, y: 890};
const REST = 0.92;

export default function Loop(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const simStart = Number(props.props.simStart ?? 0.5);
  const cars = sample('high', simStart + clock.elapsedSeconds);
  const pull = clock.progress('loop-overview-0');
  // 开场是顶部路段的特写，所以拉远的锚点也放在环路顶部。
  const scale = mix(2.1, REST, Math.min(1, pull / 0.38));
  const anchor = {x: CENTER.x, y: CENTER.y - TRAFFIC.loop.ry * REST};
  const chevrons = [0.12, 0.37, 0.62, 0.87].map(share => loopPoint(TRAFFIC.loop.perimeter * share));

  return (
    <Stage props={props} title="把镜头拉远：一条闭合的环路"
      lead="这里没有红绿灯、没有出口，也没有事故点">
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${anchor.x} ${anchor.y}) scale(${scale}) translate(${-anchor.x} ${-anchor.y})`}>
          <LoopRoad cx={CENTER.x} cy={CENTER.y}/>
          {chevrons.map((point, index) => {
            const x = CENTER.x + point.x;
            const y = CENTER.y + point.y;
            return <path key={index} d="M-9,-10 L12,0 L-9,10 Z" fill={COLOR.edge}
              transform={`translate(${x} ${y}) rotate(${(point.heading * 180) / Math.PI})`} opacity={0.5}/>;
          })}
          {cars.map(car => <CarMark key={car.id} x={CENTER.x + car.x} y={CENTER.y + car.y}
            heading={car.heading} braking={car.brake} label={car.id} scale={0.95}/>)}
        </g>
        <g opacity={Math.min(1, pull * 1.6)}>
          <line x1={80} x2={150} y1={690} y2={760} stroke={COLOR.edge} strokeWidth={2}/>
          <text x={80} y={678} fontSize={SIZE.note + 2} fill={COLOR.muted}>没有红绿灯</text>
          <line x1={1000} x2={930} y1={690} y2={760} stroke={COLOR.edge} strokeWidth={2}/>
          <text x={1000} y={678} fontSize={SIZE.note + 2} fill={COLOR.muted} textAnchor="end">没有出口</text>
          <text x={540} y={1512} fontSize={SIZE.note + 2} fill={COLOR.muted} textAnchor="middle">没有事故点</text>
        </g>
      </svg>
      <div style={{position: 'absolute', left: 96, top: 1450, right: 96, fontSize: SIZE.note,
        color: COLOR.muted, textAlign: 'center'}}>
        单向环路 · {TRAFFIC.groups.high.cars} 辆车 · 都在沿同一方向行驶
      </div>
    </Stage>
  );
}
