/**
 * 对照：同一条入口脉冲，直接交接与中间暂存两条通道。
 *
 * 上行把入口的忽快忽慢原样传到出口；下行先落进水箱，出口只按稳定节奏取用，
 * 水位随旁白推进升降。两条通道由各自的旁白时间窗点亮，观众看的是「哪里被吸收掉了」。
 */
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const LANE = {left: 200, right: 1720, height: 196, gap: 48};

export default function Compare(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const direct = clock.progress('buffer-compare-0');
  const buffered = clock.progress('buffer-compare-1');
  const top = 306;
  return (
    <Stage props={props} title="直接交接，还是中间暂存" note="同一条入口脉冲，两条通道的处理方式不同">
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        <Lane region={{x: LANE.left, y: top, w: LANE.right - LANE.left, h: LANE.height}}
          label="直接交接" subtitle="入口一停，出口跟着停" active={direct} level={null}/>
        <Lane region={{x: LANE.left, y: top + LANE.height + LANE.gap, w: LANE.right - LANE.left, h: LANE.height}}
          label="中间暂存" subtitle="先存多余，再补不足" active={buffered} level={mix(0.28, 0.78, buffered)}/>
      </svg>
      <div style={{position: 'absolute', left: LANE.left, top: contentBottom(props) - 52,
        fontSize: SIZE.lead, color: COLOR.ink}}>
        缓冲不是让水流变小，而是让出口不必跟着入口抖动
      </div>
    </Stage>
  );
}

function Lane({region, label, subtitle, active, level}: {
  region: {x: number; y: number; w: number; h: number};
  label: string; subtitle: string; active: number; level: number | null;
}) {
  // 未轮到的通道保持可读但不抢眼：不靠降低对比度到看不清来表达「还没讲到」。
  const lit = mix(0.4, 1, active);
  const lane = region.y + 132;
  const tank = level === null ? null : {x: region.x + region.w * 0.46, y: region.y + 62, w: 210, h: 140};
  const inlet = {from: region.x + 300, to: tank ? tank.x - 44 : region.x + region.w - 320};
  const outlet = tank ? {from: tank.x + tank.w + 44, to: region.x + region.w - 344} : null;
  return (
    <g opacity={lit}>
      <rect x={region.x} y={region.y} width={region.w} height={region.h} rx={18} fill={COLOR.panel}
        stroke={COLOR.rule} strokeWidth={2}/>
      <text x={region.x + 32} y={region.y + 50} fill={COLOR.accent} fontSize={SIZE.body}>{label}</text>
      <text x={region.x + 32} y={region.y + 88} fill={COLOR.muted} fontSize={SIZE.note}>{subtitle}</text>
      {pulses(inlet.from, inlet.to, lane, active, true)}
      {tank && level !== null && (
        <g>
          <rect x={tank.x} y={tank.y} width={tank.w} height={tank.h} rx={12} fill="none"
            stroke={COLOR.rule} strokeWidth={3}/>
          <rect x={tank.x + 5} y={tank.y + 5 + (tank.h - 10) * (1 - level)} width={tank.w - 10}
            height={(tank.h - 10) * level} rx={8} fill={COLOR.accent} opacity={0.38}/>
          <text x={tank.x + tank.w / 2} y={tank.y + tank.h - 16} fill={COLOR.ink} fontSize={SIZE.note}
            textAnchor="middle">存水 {Math.round(level * 100)}%</text>
        </g>
      )}
      {outlet && pulses(outlet.from, outlet.to, lane, active, false)}
      <text x={region.x + region.w - 44} y={lane + 10} fill={COLOR.warn} fontSize={SIZE.note}
        textAnchor="end">出口</text>
    </g>
  );
}

/** 流动的点：`erratic` 为真时点的大小随相位抖动，否则保持稳定节奏。 */
function pulses(from: number, to: number, y: number, phase: number, erratic: boolean) {
  return Array.from({length: 9}, (_, index) => {
    const t = (index / 9 + phase * 0.55) % 1;
    const wobble = erratic ? Math.sin(t * 24 + index) * 0.5 + 0.5 : 0.5;
    return <circle key={`${from}-${index}`} cx={from + t * (to - from)} cy={y} r={5 + 6 * wobble}
      fill={erratic ? COLOR.accent : COLOR.warn} opacity={0.3 + 0.55 * wobble}/>;
  });
}
