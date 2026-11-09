/** 同内容的三种字体与背景选案，均为实际文字与三维场景，非整张图片包装。 */
import type {CSSProperties, ReactNode} from 'react';
import {useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import CapitalStage from './components/capital-stage';
import {DIRECTIONS, directionFrame} from './typography-themes';
import {comparison, UNITS_PER_DISC} from './compoundMath';

type TypeProps = {x: number; y: number; size: number; children: ReactNode; center?: boolean;
  family?: string; color?: string; style?: CSSProperties};
function Type({x, y, size, children, center = false, family, color, style}: TypeProps) {
  return <div data-m2v-role="body" style={{position: 'absolute', left: x, top: y, fontSize: size,
    fontFamily: family, fontWeight: 400, lineHeight: 1.1, whiteSpace: 'nowrap', color,
    transform: center ? 'translateX(-50%)' : undefined, ...style}}>{children}</div>;
}

function Amount({x, y, value, unitSize, size, index, approximate = false}: {
  x: number; y: number; value: string; unitSize: number; size: number; index: number; approximate?: boolean;
}) {
  const direction = DIRECTIONS[index];
  return <div data-m2v-role="body" style={{position: 'absolute', left: x, top: y,
    transform: 'translateX(-50%)', display: 'flex', alignItems: 'baseline', gap: 12,
    lineHeight: 1, whiteSpace: 'nowrap', fontFamily: direction.chinese, color: direction.ink}}>
    {approximate && <span style={{fontSize: unitSize}}>约</span>}
    <span style={{fontFamily: direction.numbers, fontSize: size, fontWeight: index === 2 ? 500 : 400,
      letterSpacing: index === 1 ? 0 : -4, fontVariantNumeric: 'lining-nums',
      fontVariationSettings: index === 2 ? '"opsz" 144, "SOFT" 60, "WONK" 1' : undefined}}>{value}</span>
    <span style={{fontSize: unitSize}}>枚</span>
  </div>;
}

export default function TypographyDirections(config: CodeSceneProps) {
  const clock = useSceneContext();
  const index = Math.min(2, Math.floor((clock.elapsedSeconds * config.fps + .001) / 3));
  const direction = DIRECTIONS[index];
  const state = directionFrame(index);
  const totals = comparison(30);
  const left = String(Math.round(totals.withdraw.total / UNITS_PER_DISC));
  const right = (totals.reinvest.total / UNITS_PER_DISC).toFixed(1);
  return <div style={{position: 'relative', width: config.width, height: config.height,
    background: direction.background, overflow: 'hidden', color: direction.ink, fontFamily: direction.chinese}}>
    <CapitalStage state={state} width={config.width} height={config.height}
      density={config.captureScale ?? 1} onReady={clock.ready}/>
    {index === 0 && <>
      <Type x={132} y={62} size={164} style={{letterSpacing: 6}}>复利</Type>
      <Type x={1780} y={133} size={42} style={{transform: 'translateX(-100%)'}}>30年后的总资产</Type>
      <div style={{position: 'absolute', left: 940, top: 298, height: 618, width: 1, background: '#b8a89a'}}/>
      <Type x={direction.left} y={292} size={48} center>收益取走</Type>
      <Type x={direction.right} y={292} size={48} center>收益再投入</Type>
      <Amount x={direction.left} y={355} value={left} size={148} unitSize={46} index={index}/>
      <Amount x={direction.right} y={355} value={right} size={148} unitSize={46} index={index} approximate/>
    </>}
    {index === 1 && <>
      <Type x={120} y={84} size={280} style={{lineHeight: .94}}>复<br/>利</Type>
      <Type x={666} y={113} size={54}>30年后的总资产</Type>
      <Type x={direction.left} y={280} size={50} center>收益取走</Type>
      <Type x={direction.right} y={280} size={50} center>收益再投入</Type>
      <Amount x={direction.left} y={354} value={left} size={190} unitSize={48} index={index}/>
      <Amount x={direction.right} y={354} value={right} size={190} unitSize={48} index={index} approximate/>
    </>}
    {index === 2 && <>
      <Type x={960} y={46} size={172} center style={{letterSpacing: 12}}>复利</Type>
      <Type x={960} y={247} size={40} center family="M2V XiaoWei">30年后的总资产</Type>
      <Type x={direction.left} y={337} size={54} center>收益取走</Type>
      <Type x={direction.right} y={337} size={54} center>收益再投入</Type>
      <Amount x={direction.left} y={409} value={left} size={144} unitSize={48} index={index}/>
      <Amount x={direction.right} y={409} value={right} size={144} unitSize={48} index={index} approximate/>
    </>}
    <div data-m2v-role="annotation" style={{position: 'absolute', left: 140, top: 994,
      fontFamily: 'M2V Sans, sans-serif', fontSize: 44, fontWeight: 500, lineHeight: 1.1,
      whiteSpace: 'nowrap', color: direction.ink, opacity: .78}}>
      固定10%仅作数学演示，非实际回报；无追加投入，不计税费及通胀
    </div>
  </div>;
}
