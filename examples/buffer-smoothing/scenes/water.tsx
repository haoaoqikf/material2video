/**
 * 机制：水箱怎样把入口的忽快忽慢变成出口的稳定节奏。
 *
 * 水位完全由真实旁白时间窗推进：第一段说入口加速时水位上升，第二段说入口变慢时
 * 水位下降。Motion 负责脉冲与面板入场，水位本身是确定性的插值——动画只做强调，
 * 不替你解释。
 */
import {motion} from 'm2v/code-scene';
import type {CodeSceneProps} from 'm2v/code-scene';
import {COLOR, SIZE, Stage, contentBottom, mix, useNarration, useReady} from './stage';

const TANK = {x: 760, y: 330, w: 400, h: 430};

export default function Water(props: CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const rising = clock.progress('buffer-water-0');
  const falling = clock.progress('buffer-water-1');
  const lower = clock.spoken('buffer-water-1');
  const level = lower ? mix(0.78, 0.30, falling) : mix(0.40, 0.78, rising);
  const inflow = lower ? 1 : 8;
  const outflow = 4;
  const inner = {x: TANK.x + 6, y: TANK.y + 6, w: TANK.w - 12, h: TANK.h - 12};
  const surface = inner.y + inner.h * (1 - level);

  return (
    <Stage props={props} title="水箱怎样吸收短期波动"
      note={`入口 ${inflow} 份/秒，出口恒定 ${outflow} 份/秒；差额由存水承接`}>
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0}}>
        <line x1={560} x2={TANK.x} y1={TANK.y + 90} y2={TANK.y + 90} stroke={COLOR.rule} strokeWidth={14}/>
        <text x={560} y={TANK.y + 56} fill={COLOR.accent} fontSize={SIZE.body}>流入 {inflow}</text>
        {Array.from({length: 8}, (_, index) => {
          const t = (index / 8 + clock.elapsedSeconds * (0.4 + inflow * 0.14)) % 1;
          return <circle key={index} cx={560 + t * (TANK.x - 580)} cy={TANK.y + 90} r={5 + inflow * 0.7}
            fill={COLOR.accent} opacity={0.35 + 0.5 * t}/>;
        })}
        <line x1={TANK.x + TANK.w} x2={props.width - 420} y1={TANK.y + TANK.h - 90}
          y2={TANK.y + TANK.h - 90} stroke={COLOR.rule} strokeWidth={14}/>
        <text x={props.width - 420} y={TANK.y + TANK.h - 126} fill={COLOR.warn} fontSize={SIZE.body}
          textAnchor="end">流出 {outflow}</text>
        {Array.from({length: 10}, (_, index) => {
          const t = (index / 10 + clock.elapsedSeconds * 0.95) % 1;
          return <circle key={index} cx={TANK.x + TANK.w + t * (props.width - 440 - TANK.x - TANK.w)}
            cy={TANK.y + TANK.h - 90} r={8} fill={COLOR.warn} opacity={0.35 + 0.5 * t}/>;
        })}
        <rect x={TANK.x} y={TANK.y} width={TANK.w} height={TANK.h} rx={16} fill={COLOR.panel}
          stroke={COLOR.rule} strokeWidth={4}/>
        <rect x={inner.x} y={surface} width={inner.w} height={inner.y + inner.h - surface} rx={10}
          fill={COLOR.accent} opacity={0.35}/>
        <line x1={inner.x} x2={inner.x + inner.w} y1={surface} y2={surface} stroke={COLOR.accent} strokeWidth={4}/>
        {Array.from({length: 4}, (_, index) => {
          const scale = [1, 0.72, 0.5, 0.32][index];
          const width = inner.w * scale;
          return <line key={index} x1={inner.x} x2={inner.x + width} y1={inner.y + inner.h * (index + 1) / 5}
            y2={inner.y + inner.h * (index + 1) / 5} stroke={COLOR.rule} strokeWidth={2}/>;
        })}
        <text x={TANK.x + TANK.w / 2} y={TANK.y + TANK.h + 46} fill={COLOR.ink} fontSize={SIZE.body}
          textAnchor="middle">存水 {Math.round(level * 100)}%</text>
      </svg>
      <motion.div animate={{opacity: [0.4, 1, 0.4]}} transition={{duration: 1.8, repeat: Infinity, ease: 'easeInOut'}}
        style={{position: 'absolute', left: 200, top: 640, width: 320, padding: '20px 24px',
          border: `2px solid ${COLOR.rule}`, borderRadius: 12, fontSize: SIZE.note, lineHeight: 1.6,
          color: COLOR.muted}}>
        {lower ? '入口变慢：出口继续取用存水，水位下降' : '入口加速：多来的水先进箱子，水位上升'}
      </motion.div>
      <div style={{position: 'absolute', left: 220, top: contentBottom(props) - 52, fontSize: SIZE.lead}}>
        水没有消失，只是暂时从出口前面搬到了箱子里
      </div>
    </Stage>
  );
}
