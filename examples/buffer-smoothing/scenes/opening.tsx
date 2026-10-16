/**
 * 开场：把「平均相同、瞬间不同」画成一张脉冲读数。
 *
 * 十二根竖条是每秒钟的瞬时流量，虚线是它们的平均。平均值一直没变，柱子却高低不一——
 * 缓冲要解决的正是这件事。柱子按真实旁白时间窗依次升起。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

//: 每秒流量示意值，刻意不做成规整波形：缓冲关心的是「不整齐」本身。
const FLOW = [3, 7, 2, 8, 3, 6, 2, 7, 4, 6, 3, 7];
const AVERAGE = FLOW.reduce((sum, value) => sum + value, 0) / FLOW.length;

export default function Opening(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const unit = typeof props.props.unit === 'string' ? props.props.unit : '份/秒';
  const plot = {left: 220, right: props.width - 220, top: 320, axisY: contentBottom(props) - 46};
  const step = (plot.right - plot.left) / FLOW.length;
  const barWidth = step * 0.52;
  const height = plot.axisY - plot.top;
  const scale = (value: number) => height * (value / 10);
  const averageY = plot.axisY - scale(AVERAGE);
  const revealed = mix(0, FLOW.length, clock.progress('buffer-point-0'));

  return (
    <Stage props={props} title="平均相同，瞬间也会不同"
      note={`每根柱子是一秒的瞬时流量，虚线是 ${AVERAGE.toFixed(2)} ${unit} 的平均值`}>
      <div style={{position: 'absolute', left: 220, top: 218, fontSize: SIZE.lead, color: COLOR.ink}}>
        同样的平均，不一样的每一秒
      </div>
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        {FLOW.map((value, index) => {
          const grown = Math.max(0, Math.min(1, revealed - index));
          const barHeight = scale(value) * grown;
          return (
            <g key={index}>
              <rect x={plot.left + index * step + (step - barWidth) / 2} y={plot.axisY - barHeight}
                width={barWidth} height={barHeight} rx={4}
                fill={value > AVERAGE ? COLOR.accent : COLOR.rule} opacity={value > AVERAGE ? 1 : 0.85}/>
              <text x={plot.left + index * step + step / 2} y={plot.axisY + 34} fill={COLOR.muted}
                fontSize={SIZE.note} textAnchor="middle">{index + 1}s</text>
            </g>
          );
        })}
        <line x1={plot.left} x2={plot.right} y1={plot.axisY} y2={plot.axisY} stroke={COLOR.muted} strokeWidth={2}/>
        <line x1={plot.left} x2={plot.right} y1={averageY} y2={averageY} stroke={COLOR.warn} strokeWidth={3}
          strokeDasharray="14 10" opacity={Math.min(1, revealed / FLOW.length * 2)}/>
        <text x={plot.right} y={averageY - 16} fill={COLOR.warn} fontSize={SIZE.note} textAnchor="end">
          平均 {AVERAGE.toFixed(2)} {unit}
        </text>
      </svg>
    </Stage>
  );
}
