/** 图片阶段共用的排版系统：中文400，Inter数字500；字阶、边距和基线保持一致。 */
import type {CSSProperties, ReactNode} from 'react';
import type {CapitalFrame} from '../capital-state';
import {comparison, money, secondYear, UNITS_PER_DISC} from '../compoundMath';

const INK = '#eee9dd';
const SECONDARY = '#b0b2b3';
const CN = 'M2V Sans, sans-serif';
const NUM = 'M2V Inter, M2V Sans, sans-serif';

function Type({x, y, size, children, secondary = false, center = false, tracking = -.8, note = false}: {
  x: number; y: number; size: number; children: ReactNode;
  secondary?: boolean; center?: boolean; tracking?: number; note?: boolean;
}) {
  const style: CSSProperties = {position: 'absolute', left: x, top: y, fontSize: size,
    fontWeight: 400, lineHeight: 1.28, letterSpacing: tracking, color: secondary ? SECONDARY : INK,
    whiteSpace: 'nowrap', transform: center ? 'translateX(-50%)' : undefined};
  return <div data-m2v-role={note ? 'annotation' : 'body'} style={style}>{children}</div>;
}

function Figure({x, y, value, unit, size, approximate = false, center = true}: {
  x: number; y: number; value: string; unit: string; size: number; approximate?: boolean; center?: boolean;
}) {
  return <div data-m2v-role="body" style={{position: 'absolute', left: x, top: y,
    transform: center ? 'translateX(-50%)' : undefined, display: 'flex', alignItems: 'baseline', gap: 14,
    whiteSpace: 'nowrap', color: INK, lineHeight: 1, fontVariantNumeric: 'tabular-nums'}}>
    {approximate && <span style={{fontSize: 34, fontWeight: 400}}>约</span>}
    <span style={{fontFamily: NUM, fontSize: size, fontWeight: 500, letterSpacing: -3}}>{value}</span>
    <span style={{fontSize: 34, fontWeight: 400}}>{unit}</span>
  </div>;
}

export default function CapitalTitles({state}: {state: CapitalFrame}) {
  const gains = secondYear();
  const totals = comparison(30);
  return <div style={{position: 'absolute', inset: 0, fontFamily: CN, pointerEvents: 'none'}}>
    {state.phase === 'opening' && <>
      <Type x={140} y={120} size={128} tracking={-4}>复利</Type>
      <Type x={148} y={360} size={58}>同样一万，</Type>
      <Type x={148} y={442} size={58}>三十年后？</Type>
      <Type x={148} y={604} size={36} secondary>两种做法</Type>
      <Type x={987} y={440} size={42} center>收益取走</Type>
      <Type x={1446} y={440} size={42} center>收益再投入</Type>
    </>}
    {state.phase === 'core' && <>
      <Type x={140} y={94} size={64}>收益，也会产生收益。</Type>
      <Type x={1780} y={112} size={32} center secondary>第 2 年</Type>
      <Figure x={685} y={302} value={money(gains.fromPrincipal)} unit="元" size={76} center={false}/>
      <Figure x={1380} y={302} value={money(gains.fromGain)} unit="元" size={76} center={false}/>
      <Type x={588} y={865} size={42} center>原来的本金</Type>
      <Type x={1320} y={865} size={42} center>去年的收益</Type>
    </>}
    {state.phase === 'result' && <>
      <Type x={140} y={94} size={64}>30 年后的总资产</Type>
      <Type x={480} y={225} size={42} center>收益取走</Type>
      <Type x={1320} y={225} size={42} center>收益再投入</Type>
      <Figure x={480} y={307} value={String(Math.round(totals.withdraw.total / UNITS_PER_DISC))} unit="枚" size={104}/>
      <Figure x={1320} y={307} value={(totals.reinvest.total / UNITS_PER_DISC).toFixed(1)} unit="枚" size={104} approximate/>
    </>}
    <Type x={140} y={954} size={38} secondary tracking={0} note>固定10%数学演示，非实际回报</Type>
    <Type x={140} y={1007} size={38} secondary tracking={0} note>无追加投入 · 不计税费及通胀</Type>
  </div>;
}
