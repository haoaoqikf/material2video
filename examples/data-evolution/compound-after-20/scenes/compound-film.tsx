import type {CSSProperties} from 'react';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {TracedCanvas} from './pathtrace-study';
import {annualState, beats, fade, halfTotals, ratio, towerCenters, towerScale, yearly} from './compound-model';

const paper = '#f5f1e8';
const amber = '#ffce8f';
const navy = '#050b16';
const layout = 'offset';
const centers = towerCenters(layout);
const labels = ['前 20 年', '后 20 年'];
const wan = (value: number) => (value / 10_000).toFixed(2);
const position = (left: number, top: number): CSSProperties => ({position: 'absolute', left, top});
const centered = (left: number, top: number): CSSProperties => ({
  ...position(left, top), transform: 'translateX(-50%)', whiteSpace: 'nowrap',
});

export default function CompoundTowers(config: CodeSceneProps) {
  const {elapsedSeconds: time} = useSceneContext();
  const lands = (config.eventFrames?.['towers-settled'] ?? 116) / config.fps;
  const multipleAt = config.segmentWindows.multiple.startFrame / config.fps;
  const stageClock = beats.assemble + 2.65 * Math.max(0, Math.min(1, (time - .14) / (lands - .14)));
  const {blocks, baseline, groupCenters} = annualState(stageClock, layout, true);
  const sculpture = fade(beats.assemble + .9, beats.assemble + 2.45, stageClock);
  const tilt = .22 * fade(beats.assemble + .18, beats.assemble + 1.54, stageClock);
  const groups = fade(.35, .86, time);
  const amounts = [fade(lands + .08, lands + .40, time), fade(lands + .39, lands + .74, time)];
  const comparisonAt = Math.max(lands + .76, multipleAt + .60);
  const multiple = fade(comparisonAt + .43, comparisonAt + .87, time);
  const afterglow = fade(lands - .04, lands + .12, time) * (1 - fade(lands + .15, lands + .83, time));
  const measure = fade(comparisonAt, comparisonAt + .68, time);
  const shift = config.height * .0667;

  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden', background: navy, color: paper, fontFamily: '"M2V Inter", "M2V Sans"'}}>
    <div style={{position: 'absolute', inset: 0, top: -shift, height: config.height}}>
      <TracedCanvas width={config.width} height={config.height} samples={26} capacity={yearly.length}
        state={{blocks, floor: baseline, rise: tilt, isMacro: false, sculpture, reveal: 0,
          motionSamples: time > .14 && time < lands ? 11 : undefined}}/>
    </div>
    <div aria-hidden style={{position: 'absolute', inset: 0, background:
      'linear-gradient(transparent 78%, #050b1600 84%, #050b16 94%)'}}/>
    <div style={{...position(0, -shift), width: 1920, height: 1080, pointerEvents: 'none',
      transformOrigin: '0 0', transform: `scale(${config.width / 1920}, ${config.height / 1080})`}}>
      {centers.map((x, index) => <div key={x} aria-hidden style={{...centered(x, baseline - 17),
        width: 250 + 114 * afterglow, height: 35, opacity: afterglow * (index ? .76 : .31),
        background: 'radial-gradient(ellipse, #ffb346a0, #e58a342d 47%, transparent 73%)'}}/>)}
      <div style={{...position(135, 243), opacity: groups}}>
        <div style={{fontSize: 74, fontWeight: 620, letterSpacing: '-.049em'}}>同样是 20 年</div>
        <div style={{fontSize: 168, marginTop: 20, marginLeft: -6, opacity: multiple,
          lineHeight: 1.08, color: amber, fontWeight: 570, letterSpacing: '-.06em'}}>
          {ratio.toFixed(2)}<span style={{fontSize: 76, marginLeft: 15}}>倍</span>
        </div>
        <div style={{fontSize: 47, marginTop: 26, fontWeight: 530, opacity: multiple}}>利息也能赚利息</div>
      </div>
      <div style={{...position(133 + 413 * sculpture, baseline), right: 142, height: 2,
        background: 'linear-gradient(90deg,#6b809fb0,#a7bad5 45%,#6b809f90)'}}/>
      {centers.map((x, index) => {
        const height = halfTotals[index] * towerScale;
        return <div key={x}>
          <div style={{...centered(groupCenters[index], baseline + 19), fontSize: 50, fontWeight: 540,
            opacity: groups}}>{labels[index]}</div>
          <div style={{...centered(x, baseline - height - (index ? 108 : 90)), color: index ? paper : amber,
            fontSize: index ? 71 : 63, lineHeight: 1.08, fontWeight: 590, opacity: amounts[index]}}>
            +{wan(halfTotals[index])}<span style={{fontSize: 41, marginLeft: 10}}>万元</span>
          </div>
          <div aria-hidden style={{...position(x + 119, baseline - height * measure), height: height * measure, width: 19,
            opacity: measure * .77, borderBlock: '1px solid #e8d7b6', borderRight: '1px solid #e8d7b6'}}/>
        </div>;
      })}
    </div>
  </div>;
}
