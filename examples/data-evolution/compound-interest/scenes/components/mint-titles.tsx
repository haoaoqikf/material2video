import type {CSSProperties, ReactNode} from 'react';
import {comparison, MODEL, money, secondYear, UNITS_PER_DISC} from '../compoundMath';
import {MINT, growthYear} from '../capital-motion';
import type {FilmClock} from '../capital-motion';
const CORE_GAINS = secondYear();

export function MintType({x = 960, y, size, children, style, numbers = false}: {
  x?: number; y: number; size: number; children: ReactNode; style?: CSSProperties; numbers?: boolean;
}) {
  return <div data-m2v-role="body" style={{position: 'absolute', left: x, top: y,
    transform: 'translateX(-50%)', fontFamily: numbers ? MINT.numbers : MINT.chinese,
    fontWeight: numbers ? 500 : 400, fontSize: size, lineHeight: 1.1, whiteSpace: 'nowrap',
    color: MINT.ink, fontVariationSettings: numbers ? '"opsz" 144, "SOFT" 60, "WONK" 1' : undefined,
    ...style}}>{children}</div>;
}
export function MintNote() {
  return <div data-m2v-role="annotation" style={{position: 'absolute', left: '50%', top: 994,
    transform: 'translateX(-50%)', whiteSpace: 'nowrap',
    fontFamily: 'M2V Sans', fontSize: 52, fontWeight: 500, lineHeight: 1.1, color: MINT.ink, opacity: .84}}>
    固定10%为数学演示，非实际回报；无追加投入，不计税费及通胀
  </div>;
}
export function MintAmount({x, y, value, approximate = false}: {
  x: number; y: number; value: string; approximate?: boolean;
}) {
  return <MintType x={x} y={y} size={56} style={{display: 'flex', alignItems: 'baseline', gap: 12}}>
    {approximate && <span>约</span>}
    <span style={{fontFamily: MINT.numbers, fontWeight: 500, fontSize: 144,
      fontVariationSettings: '"opsz" 144, "SOFT" 60, "WONK" 1', letterSpacing: -4}}>{value}</span>枚
  </MintType>;
}
export function CoreTitles({clock}: {clock: FilmClock}) {
  const born = clock.passed('second-birth');
  return <>
    <MintType y={54} size={112}>第2年</MintType>
    <MintType y={196} size={60}>{clock.passed('second-total') ? `当年收益 ${money(CORE_GAINS.fromPrincipal + CORE_GAINS.fromGain)}元`
      : born ? '收益，也会产生收益' : '让去年的收益，成为本金'}</MintType>
    {clock.passed('rejoin-contact') && <>
      <MintType x={588} y={818} size={80}>原始本金</MintType>
      <MintType x={1320} y={818} size={80}>去年的收益</MintType>
    </>}
    {clock.passed('second-formed') && <>
      <MintType x={588} y={434} size={84} numbers>{money(CORE_GAINS.fromPrincipal)}<span style={{fontFamily: MINT.chinese, fontSize: 56}}>元</span></MintType>
      <MintType x={1320} y={434} size={84} numbers>{money(CORE_GAINS.fromGain)}<span style={{fontFamily: MINT.chinese, fontSize: 56}}>元</span></MintType>
    </>}
  </>;
}
export function GrowthTitles({clock}: {clock: FilmClock}) {
  const complete = clock.passed('result');
  const total = comparison(MODEL.years);
  return <>
    <MintType y={46} size={172}>{complete ? '复利' : `第${growthYear(clock)}年`}</MintType>
    <MintType y={240} size={60} style={{fontFamily: 'M2V XiaoWei'}}>
      {complete ? `${MODEL.years}年后的总资产` : '时间加速，收益继续生息'}
    </MintType>
    <MintType x={MINT.left} y={315} size={80}>收益取走</MintType>
    <MintType x={MINT.right} y={315} size={80}>收益再投入</MintType>
    {complete && <>
      <MintAmount x={MINT.left} y={409} value={String(Math.round(total.withdraw.total / UNITS_PER_DISC))}/>
      <MintAmount x={MINT.right} y={409} value={(total.reinvest.total / UNITS_PER_DISC).toFixed(1)} approximate/>
    </>}
    {complete && <MintNote/>}
  </>;
}
