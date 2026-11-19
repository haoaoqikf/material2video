import type {CSSProperties} from 'react';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {FormalMacroGlassCanvas} from './macro-glass-formal';
import {beats, fade, halfTotals, macroState, principal, rate} from './compound-model';

const position = (left: number, top: number): CSSProperties => ({position: 'absolute', left, top});
const amber = '#ffce8f';
const labels = ['前 20 年', '后 20 年'];
const principalPose = macroState(beats.reinvest[0]);

export default function CompoundOpening(config: CodeSceneProps) {
  const {elapsedSeconds: time} = useSceneContext();
  const at = (id: string) => config.segmentWindows[id].startFrame / config.fps;
  const lands = (config.eventFrames?.['principal-lands'] ?? 20) / config.fps;
  const enter = fade(.02, lands, time);
  const line = fade(.14, .81, time);
  const camera = .63 * fade(.33, 2.24, time) + .37 * fade(at('late') - .24, at('late') + 1.18, time);
  const settle = fade(config.durationInFrames / config.fps - .78, config.durationInFrames / config.fps, time);
  const first = {...principalPose.first, height: principalPose.first.height * settle};
  const blocks = principalPose.blocks.map(block => block.glass === 'ink' ? {...block,
    x: block.x + (1 - enter) * 92, y: block.y - (1 - enter) * 88, pitch: -.17 * (1 - enter),
  } : block === principalPose.first ? first : block);
  const revealAmounts = [fade(.62, 1.03, time), fade(.91, 1.32, time)];
  const focus = [at('early'), at('late')].map(start =>
    fade(start - .14, start + .24, time) * (1 - fade(start + .59, start + 1.29, time)));

  return <div style={{width: config.width, height: config.height, position: 'relative', overflow: 'hidden',
    background: '#050b16', color: '#f5f1e8', fontFamily: '"M2V Inter", "M2V Sans"'}}>
    <div style={{position: 'absolute', inset: 0, top: -config.height * .147, height: config.height,
      transform: `translate(${3.8 - 2.9 * camera}%, 0) scale(${1 + .085 * camera})`, transformOrigin: '66% 58%'}}>
      <FormalMacroGlassCanvas width={config.width} height={config.height} look="lens"
        macro={{...principalPose, first, blocks}} light={.13 + .46 * focus[0] + .73 * focus[1] + .33 * settle}/>
    </div>
    <div aria-hidden style={{position: 'absolute', inset: 0, background:
      'linear-gradient(90deg,#050b16e0,transparent 70%),linear-gradient(0deg,#050b16 12%,#050b16e8 30%,#050b1644 53%,transparent 67%)'}}/>
    <div style={{...position(0, 0), width: 1920, height: 1080, transformOrigin: '0 0',
      transform: `scale(${config.width / 1920},${config.height / 1080})`}}>
      <div style={{...position(143, 203), fontSize: 114, fontWeight: 650, letterSpacing: '-.057em',
        opacity: fade(.03, .35, time)}}>
        <span style={{fontSize: 54, marginRight: 20, letterSpacing: 0}}>只投</span>{principal / 10_000} 万元
      </div>
      <div style={{...position(151, 359), color: '#b5c8e4', fontSize: 45, fontWeight: 520,
        opacity: fade(.22, .59, time)}}>假设年利率 {Math.round(rate * 100)}%</div>
      <div style={{...position(153, 582), width: 1614, opacity: fade(.12, .47, time)}}>
        <div aria-hidden style={{...position(0, 0), width: 1614 * line, height: 3,
          background: 'linear-gradient(90deg,#7197c9,#abc1dd 50%,#ffce8f)', boxShadow: '0 0 16px #aec6ee38'}}/>
        {[0, 807, 1614].map(mark => <div key={mark} aria-hidden style={{...position(mark - 1, -9),
          width: 2, height: 21, background: '#a7bbd7', opacity: line}}/>)}
        {labels.map((label, index) => <div key={label} style={{...position(index * 807 + 36, 31),
          color: index ? amber : '#e2ecfa', opacity: revealAmounts[index],
          transform: `translateY(${9 * (1 - revealAmounts[index]) - 5 * focus[index]}px)`,
          textShadow: `0 0 ${20 * focus[index]}px ${index ? '#ffad5f76' : '#86baff77'}`}}>
          <div style={{fontSize: 52, fontWeight: 550, letterSpacing: '-.03em'}}>{label} · 利息</div>
          <div style={{fontSize: 104, lineHeight: 1.08, fontWeight: 640, letterSpacing: '-.06em'}}>
            {(halfTotals[index] / 10_000).toFixed(1)}<span style={{fontSize: 53, marginLeft: 13}}>万元</span>
          </div>
        </div>)}
      </div>
    </div>
  </div>;
}
