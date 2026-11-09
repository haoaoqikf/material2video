import {easeMotion} from '../../src/code-scene/motion';
import {balance, clamp, MODEL, money} from '../compoundMath';
import {filmPhase} from '../mint-film-motion';
import {MINT} from '../capital-motion';
import type {FilmClock} from '../capital-motion';
import {CoreTitles, GrowthTitles, MintNote, MintType} from './mint-titles';

export default function FilmTitles({clock}: {clock: FilmClock}) {
  const phase = filmPhase(clock);
  if (phase === 'core') return <CoreTitles clock={clock}/>;
  if (phase === 'growth' || phase === 'result') return <GrowthTitles clock={clock}/>;
  if (phase === 'closing') {
    const enter = easeMotion('easeOutCubic', clamp((clock.frame - clock.at('conclusion')) / 12));
    return <>
      <MintType y={46} size={172} style={{opacity: enter}}>复利</MintType>
      <MintType y={336} size={84} style={{opacity: enter}}>让收益，也成为本金。</MintType>
    </>;
  }
  if (phase === 'split') {
    const entered = clock.passed('compare-ready');
    return <>
      <MintType y={62} size={100}>同一轮收益，两种去向</MintType>
      {entered && <>
        <MintType x={MINT.left} y={315} size={80}>收益取走</MintType>
        <MintType x={MINT.right} y={315} size={80}>收益再投入</MintType>
        <MintType x={MINT.left} y={430} size={56}>拿走，不再生息</MintType>
        <MintType x={MINT.right} y={430} size={56}>留在里面，继续生息</MintType>
      </>}
    </>;
  }
  if (phase === 'first') return <>
    <MintType y={54} size={112}>第1年</MintType>
    {clock.passed('first-formed') && <MintType y={220} size={84} numbers>
      {`${money(MODEL.principal)} × ${MODEL.rate * 100}% = ${money(balance(1, true).gain)}`}
    </MintType>}
    <MintNote/>
  </>;
  return <>
    <MintType y={46} size={172}>复利</MintType>
    <MintType y={247} size={64}>同样一万，两种做法</MintType>
    <MintType x={MINT.left} y={355} size={72}>收益取走</MintType>
    <MintType x={MINT.right} y={355} size={72}>收益再投入</MintType>
    {[MINT.left, MINT.right].map(x => <MintType key={x} x={x} y={458} size={112} numbers>
      {money(MODEL.principal)}<span style={{fontFamily: MINT.chinese, fontSize: 56}}>元</span>
    </MintType>)}
    <MintType y={920} size={60}>三十年后，会差多少？</MintType>
  </>;
}
