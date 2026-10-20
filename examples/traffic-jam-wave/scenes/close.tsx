/**
 * 收束：把机制压成一句可带走的话，并给出唯一片尾署名。
 *
 * 环路保留在画面上方，红色低速带与蓝色后退箭头不再增加新信息，只做回看。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, useNarration, useReady} from './stage';
import {ArcPath, CarMark, LoopRoad} from './parts';
import {loopPoint, sample, slowCenter} from './traffic';

const CENTER = {x: 540, y: 780};
const SCALE = 0.76;

export default function Close(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const simStart = Number(props.props.simStart ?? 14);
  // 收束镜头放慢传播，方便在片尾再读一次方向；数据与前面的段落相同。
  const cars = sample('high', simStart + clock.elapsedSeconds * 0.62);
  const slow = slowCenter(cars);
  const tip = slow === null ? null : loopPoint(slow - 200);
  const progress = clock.progress('jam-close-0');

  return (
    <Stage props={props} title="所以，车流会自己堵起来"
      lead="一种不需要事故、却会在特定条件下被放大的扰动">
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${CENTER.x} ${CENTER.y}) scale(${SCALE}) translate(${-CENTER.x} ${-CENTER.y})`}>
          <LoopRoad cx={CENTER.x} cy={CENTER.y} width={92}/>
          {slow !== null && <ArcPath cx={CENTER.x} cy={CENTER.y} fromS={slow - 120} lengthS={240}
            stroke={COLOR.dangerSoft} width={84} opacity={0.95}/>}
          {cars.map(car => <CarMark key={car.id} x={CENTER.x + car.x} y={CENTER.y + car.y}
            heading={car.heading} braking={car.brake} label={car.id} scale={1.05}/>)}
          {slow !== null && tip !== null && <>
            <ArcPath cx={CENTER.x} cy={CENTER.y} fromS={slow + 200} lengthS={-400}
              stroke={COLOR.accent} width={6} opacity={0.9} dash="14 10" expand={1.15}/>
            <path d="M-15,-11 L15,0 L-15,11 Z" fill={COLOR.accent}
              transform={`translate(${CENTER.x + tip.x * 1.15} ${CENTER.y + tip.y * 1.15})
                rotate(${(tip.heading * 180) / Math.PI + 180})`}/>
          </>}
        </g>
      </svg>

      <div style={{position: 'absolute', left: 96, top: 1218, right: 96, fontSize: 46, fontWeight: 700,
        lineHeight: 1.4, opacity: Math.max(0.35, progress)}}>
        车辆向前，<span style={{color: COLOR.accent}}>拥堵向后</span>。
      </div>
      <div style={{position: 'absolute', left: 96, top: 1318, right: 96, fontSize: SIZE.body,
        lineHeight: 1.6, color: COLOR.muted}}>
        没有事故，也会堵车。关键是看一次扰动会不会被放大，以及它在车流里传向哪里。
      </div>
      <div style={{position: 'absolute', left: 96, top: 1468, right: 96, fontSize: SIZE.note,
        lineHeight: 1.6, color: COLOR.muted, borderTop: `2px solid ${COLOR.rule}`, paddingTop: 16}}>
        本片轨迹与图表均为示意，不是真实测量或交通预测<br/>
        机制依据：杉山等，2008
      </div>
    </Stage>
  );
}
