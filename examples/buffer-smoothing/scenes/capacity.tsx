/**
 * 边界：容量有上限，等待有代价。
 *
 * 同一只水箱，入口长期大于出口：水位顶到容量线后开始溢出。第三段旁白换上一只更大的
 * 水箱轮廓——它只是把溢出推后，并没有让出口变快。溢出点上方列出真正的三种处理办法。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const TANK = {x: 620, y: 320, w: 380, h: 450};
const OUTCOMES = ['丢弃', '拒绝', '通知上游减速'];

export default function Capacity(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const waiting = clock.progress('buffer-capacity-0');
  const overload = clock.progress('buffer-capacity-1');
  const bigger = clock.progress('buffer-capacity-2');
  const full = clock.spoken('buffer-capacity-1');
  // 前两段水位一路顶到容量线；第三段出现更大的水箱轮廓，水位回落到同一相对位置。
  const level = full ? mix(0.84, 1, overload) : mix(0.42, 0.84, waiting);
  const inner = {x: TANK.x + 6, y: TANK.y + 6, w: TANK.w - 12, h: TANK.h - 12};
  const surface = inner.y + inner.h * (1 - level);
  const overflow = Math.max(0, level - 0.9) / 0.1;

  return (
    <Stage props={props} title="容量有上限，等待有代价"
      note="入口长期大于出口时，存水总会用完或溢满">
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        <rect x={TANK.x} y={TANK.y} width={TANK.w} height={TANK.h} rx={16} fill={COLOR.panel}
          stroke={COLOR.rule} strokeWidth={4}/>
        <rect x={inner.x} y={surface} width={inner.w} height={inner.y + inner.h - surface} rx={10}
          fill={overflow > 0 ? COLOR.warn : COLOR.accent} opacity={0.34}/>
        <line x1={inner.x} x2={inner.x + inner.w} y1={surface} y2={surface}
          stroke={overflow > 0 ? COLOR.warn : COLOR.accent} strokeWidth={4}/>
        <line x1={TANK.x - 26} x2={TANK.x + TANK.w + 26} y1={inner.y + inner.h * 0.1} y2={inner.y + inner.h * 0.1}
          stroke={COLOR.warn} strokeWidth={3} strokeDasharray="12 8"/>
        <text x={TANK.x + TANK.w + 36} y={inner.y + inner.h * 0.1 + 8} fill={COLOR.warn} fontSize={SIZE.note}>
          容量上限
        </text>
        {overflow > 0 && Array.from({length: 7}, (_, index) => {
          const t = (index / 7 + clock.elapsedSeconds * 0.7) % 1;
          return <circle key={index} cx={TANK.x + TANK.w - 60 - index * 26} cy={inner.y + inner.h * 0.1 + t * 150}
            r={5 + 3 * (1 - t)} fill={COLOR.warn} opacity={0.75 * (1 - t) * overflow}/>;
        })}
        <text x={TANK.x} y={TANK.y - 20} fill={COLOR.ink} fontSize={SIZE.body}>积压 {Math.round(level * 100)}%</text>
        {bigger > 0 && (
          <rect x={TANK.x - bigger * 120} y={TANK.y - bigger * 60} width={TANK.w + bigger * 240}
            height={TANK.h + bigger * 60} rx={18} fill="none" stroke={COLOR.muted} strokeWidth={3}
            strokeDasharray="16 12" opacity={bigger}/>
        )}
        {bigger > 0.4 && (
          <text x={TANK.x + TANK.w + 40} y={TANK.y + TANK.h - 20} fill={COLOR.muted} fontSize={SIZE.body}
            opacity={bigger}>更大的水箱只把这一刻推后</text>
        )}
      </svg>
      <div style={{position: 'absolute', left: 220, top: TANK.y, width: 320}}>
        <div style={{fontSize: SIZE.note, color: COLOR.muted, marginBottom: 16}}>满了以后</div>
        {OUTCOMES.map((label, index) => (
          <div key={label} style={{fontSize: SIZE.lead, padding: '14px 0',
            borderBottom: `2px solid ${COLOR.rule}`,
            color: overflow > 0 && index === 2 ? COLOR.warn : COLOR.ink}}>{label}</div>
        ))}
      </div>
      <div style={{position: 'absolute', left: 220, top: contentBottom(props) - 52, fontSize: SIZE.lead}}>
        存储换时间，但换不来更快的处理能力
      </div>
    </Stage>
  );
}
