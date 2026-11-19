import type {CSSProperties} from 'react';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {TracedCanvas} from './pathtrace-study';
import {annualBarDuration, annualState, beats, chartX, fade, growAnnualBars, half, halfTotals, principal, rate, yearly} from './compound-model';

const paper = '#f5f1e8';
const amber = '#ffce8f';
const backdrop = '#050b16';
const plot = annualState(beats.assemble, 'offset');
const notableYears = [0, half - 1, yearly.length - 1];
const openingBalance = Math.round(principal + halfTotals[0]).toLocaleString('zh-CN');
const position = (left: number, top: number): CSSProperties => ({position: 'absolute', left, top});
const numberStyle = (fontSize: number): CSSProperties => ({
  fontSize, lineHeight: 1.08, letterSpacing: '-.047em', fontWeight: 560, color: amber,
});
const barEntrance = [.13, .57, 1.01];

export default function CompoundAnnualGrowth(config: CodeSceneProps) {
  const {elapsedSeconds: seconds} = useSceneContext();
  const end = config.durationInFrames / config.fps;
  const balanceStart = config.segmentWindows['balance-21'].startFrame / config.fps;
  const rateStart = config.segmentWindows['same-rate'].startFrame / config.fps;
  const lateFinish = (config.eventFrames?.['last-bar'] ?? 273) / config.fps;
  const earlyFinish = Math.max(3.27, balanceStart + .43);
  const lateStart = Math.max(earlyFinish + .75, rateStart - .32);
  const lastStart = lateFinish - annualBarDuration(yearly.length - 1);
  const earlyLastStart = earlyFinish - annualBarDuration(half - 1);
  const starts = plot.blocks.map((_, index) => index < barEntrance.length ? barEntrance[index] : index < half
    ? 1.29 + (earlyLastStart - 1.29) * (index - barEntrance.length) / (half - barEntrance.length - 1)
    : lateStart + (lastStart - lateStart) * (index - half) / (half - 1));
  const {blocks, progress} = growAnnualBars(plot, starts, seconds);
  const balance = fade(earlyFinish - .02, earlyFinish + .37, seconds)
    * (1 - fade(lateStart + .15, lateStart + .65, seconds));
  const last = fade(lateFinish, lateFinish + .34, seconds);
  const handoff = 1 - fade(end - .38, end - .02, seconds);
  const dividingLine = fade(earlyFinish - .16, earlyFinish + .16, seconds)
    * (1 - fade(lateFinish + .12, lateFinish + .57, seconds));
  const shift = config.height * .0667;

  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden', background: backdrop, color: paper, fontFamily: '"M2V Inter", "M2V Sans"'}}>
    <div style={{position: 'absolute', inset: 0, top: -shift, height: config.height}}>
      <TracedCanvas width={config.width} height={config.height} samples={26} capacity={yearly.length}
        state={{blocks, floor: plot.baseline, rise: 0, isMacro: false, sculpture: 0, reveal: 0,
          motionSamples: seconds < lateFinish ? 11 : undefined}}/>
    </div>
    <div aria-hidden style={{position: 'absolute', inset: 0, background:
      'linear-gradient(transparent 78%, #050b1600 84%, #050b16 94%)'}}/>
    <div style={{...position(0, -shift), width: 1920, height: 1080, pointerEvents: 'none',
      transformOrigin: '0 0', transform: `scale(${config.width / 1920}, ${config.height / 1080})`}}>
      <div style={{...position(133, 118), ...numberStyle(48), opacity: handoff}}>年利率 {Math.round(rate * 100)}%</div>
      <div style={{...position(127, 195), fontSize: 97, fontWeight: 650, letterSpacing: '-.060em',
        opacity: handoff}}>每年赚的利息</div>
      <div style={{...position(134, 383), opacity: balance, background: '#081527ed',
        borderLeft: '3px solid #ffce8fa6', padding: '14px 30px 18px 22px'}}>
        <div style={{fontSize: 46}}>第 21 年期初余额</div>
        <div style={{...numberStyle(68), marginTop: 9}}>约 {openingBalance} 元</div>
      </div>
      <div style={{...position(132, plot.baseline), right: 142, height: 2,
        background: 'linear-gradient(90deg,#6b809fb0,#a7bad5 45%,#6b809f90)'}}/>
      <div aria-hidden style={{...position(chartX(half - 1) + 20, plot.baseline - 116), width: 1, height: 116,
        background: 'linear-gradient(transparent,#f8cf9199)', opacity: dividingLine}}/>
      {blocks.map((block, index) => progress[index] > 0 && progress[index] < 1 && block.height >= 2 &&
        <div key={index} aria-hidden style={{...position(block.x - block.width / 2, plot.baseline - block.height),
          width: block.width, height: block.height, boxSizing: 'border-box',
          opacity: Math.sin(Math.PI * progress[index]) * .78, borderTop: '3px solid #ffedc9',
          borderInline: '1px solid #ffcf8877', background: 'linear-gradient(#ffbd6244,transparent 48%)'}}/>)}
      {notableYears.map(index => <div key={index} style={{...position(chartX(index), plot.baseline), opacity: handoff}}>
        <div style={{width: 2, height: 11, background: '#9aafcb', transform: 'translateX(-50%)'}}/>
        <div style={{...position(0, 20), fontSize: 50, fontWeight: 530, whiteSpace: 'nowrap',
          transform: 'translateX(-50%)'}}>第 {index + 1} 年</div>
      </div>)}
      <div style={{...position(143, plot.baseline - 86), ...numberStyle(47),
        opacity: fade(.24, .62, seconds) * handoff}}>+{yearly[0].toLocaleString('zh-CN')} 元</div>
      <div style={{...position(1469, 221), ...numberStyle(56), opacity: last * handoff}}>
        +{(yearly.at(-1)! / 10_000).toFixed(2)} 万元
      </div>
    </div>
  </div>;
}
