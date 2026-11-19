import type {CSSProperties} from 'react';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {FormalMacroGlassCanvas} from './macro-glass-formal';
import {beats, contribution, fade, macroState, principal, yearly} from './compound-model';

const white = '#f5f1e8';
const amber = '#ffce8f';
const navy = '#050b16';
const typeface = '"M2V Inter", "M2V Sans"';
const number = (value: number) => Math.round(value).toLocaleString('zh-CN');

const position = (left: number, top: number): CSSProperties => ({position: 'absolute', left, top});
const centered = (left: number, top: number): CSSProperties => ({
  ...position(left, top), transform: 'translateX(-50%)', whiteSpace: 'nowrap',
});

function labelWindow(inAt: number, outAt: number, now: number) {
  return fade(inAt, inAt + .32, now) * (1 - fade(outAt - .27, outAt, now));
}

export default function CompoundReinvestment(config: CodeSceneProps) {
  const {elapsedSeconds: seconds} = useSceneContext();
  const contact = (config.eventFrames?.contact ?? 48) / config.fps;
  const first = config.segmentWindows['first-year'].startFrame / config.fps;
  const extra = config.segmentWindows['extra-interest'].startFrame / config.fps;
  const total = config.segmentWindows['year-two'].startFrame / config.fps;
  const lift = (config.eventFrames?.['extra-lifts'] ?? 105) / config.fps;
  const shines = (config.eventFrames?.['extra-shines'] ?? 161) / config.fps;
  const end = config.durationInFrames / config.fps;
  const growth = fade(lift, lift + .72, seconds);
  const fall = fade(.18, contact, seconds);
  const clock = growth > 0
    ? beats.reveal[0] + growth * (beats.reveal[1] - beats.reveal[0])
    : beats.reinvest[0] + fall * (beats.reinvest[1] - beats.reinvest[0]);
  const geometry = macroState(clock, fade(total - .12, total + .40, seconds));
  const sum = fade(total + .05, total + .57, seconds);
  const extraPlate = {...geometry.extra, y: geometry.extra.y + 12 * sum,
    pitch: (geometry.extra.pitch ?? 0) * (1 - .27 * sum)};
  const macro = {...geometry, extra: extraPlate,
    blocks: geometry.blocks.map(block => block === geometry.extra ? extraPlate : block)};
  const handoff = fade(end - .65, end - .04, seconds);
  const camera = .055 * fade(extra + .18, lift + .65, seconds) - .040 * handoff;
  const light = .48 * fade(contact - .09, contact + .17, seconds) * (1 - fade(contact + .18, contact + .60, seconds))
    + fade(lift - .23, lift + .16, seconds) * (1 - fade(lift + .42, lift + .96, seconds))
    + .52 * fade(shines - .06, shines + .035, seconds) * (1 - fade(shines + .06, shines + .36, seconds));
  const firstLabel = labelWindow(first, lift, seconds);
  const extraLabel = labelWindow(lift + .17, total + .14, seconds);
  const totalLabel = fade(total + .14, total + .49, seconds);

  const shift = config.height * .0667;
  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden', background: navy, color: white, fontFamily: typeface}}>
    <div style={{position: 'absolute', inset: 0, top: -shift, height: config.height,
      transform: `translate(${-26 * camera}%, ${-12 * camera}%) scale(${1 + camera})`,
      transformOrigin: '62% 56%'}}>
      <FormalMacroGlassCanvas width={config.width} height={config.height} macro={macro} look="lens" light={light}/>
    </div>
    <div aria-hidden style={{position: 'absolute', inset: 0,
      background:'linear-gradient(transparent 78%, #050b1600 84%, #050b16 94%)'}}/>
    <div style={{...position(0, -shift), width: 1920, height: 1080, pointerEvents: 'none',
      transformOrigin: '0 0', transform: `scale(${config.width / 1920}, ${config.height / 1080})`}}>
      {[
        {label: '第一年赚到', value: `+${number(yearly[0])}`, opacity: firstLabel},
        {label: '留下的利息又赚了', value: `+${number(contribution)}`, opacity: extraLabel},
      ].map(({label, value, opacity}) => <div key={label} style={{...position(140, 315), opacity}}>
        <div style={{fontSize: 53, fontWeight: 530}}>{label}</div>
        <div style={{fontSize: 118, lineHeight: 1.13, color: amber, fontWeight: 560, letterSpacing: '-.05em'}}>
          {value}<span style={{fontSize: 51, marginLeft: 12}}>元</span>
        </div>
      </div>)}
      <div style={{...position(140, 315 - 8 * handoff), opacity: totalLabel}}>
        <div style={{fontSize: 53, fontWeight: 530}}>第二年赚到</div>
        <div style={{fontSize: 99, lineHeight: 1.15, color: amber, fontWeight: 600, letterSpacing: '-.05em'}}>
          {number(yearly[0])} + {number(contribution)}
        </div>
        <div style={{fontSize: 65, marginTop: 8}}>= {number(yearly[1])} 元</div>
      </div>
      <div style={{...centered(1145, 890), fontSize: 49, fontWeight: 530,
        opacity: fade(contact - .45, contact + .12, seconds)}}>本金 {number(principal)} 元</div>
    </div>
  </div>;
}
