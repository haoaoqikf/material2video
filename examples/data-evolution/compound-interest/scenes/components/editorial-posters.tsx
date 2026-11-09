/** 三幅同内容静态选案。字、底纹与建筑光域均为原生DOM/SVG，币堆为真实Three几何。 */
import type {CSSProperties, ReactNode} from 'react';
import EditorialStage from './editorial-stage';
import type {EditorialVariant} from './editorial-stage';
import {comparison, MODEL, UNITS_PER_DISC} from '../compoundMath';

const totals = comparison(MODEL.years);
const values = [String(totals.withdraw.total / UNITS_PER_DISC),
  (totals.reinvest.total / UNITS_PER_DISC).toFixed(1)];
const names = ['收益取走', '收益再投入'];
const serif = 'M2V Serif';
const sans = 'M2V Sans';

function Type({x, y, size, children, style}: {
  x: number; y: number; size: number; children: ReactNode; style?: CSSProperties;
}) {
  return <div style={{position: 'absolute', left: x, top: y, fontSize: size,
    fontFamily: sans, lineHeight: 1.15, whiteSpace: 'nowrap', ...style}}>{children}</div>;
}
function Readout({i, x, y, family = sans, color, weight = 500}: {
  i: number; x: number; y: number; family?: string; color: string; weight?: number;
}) {
  return <div style={{position: 'absolute', left: x, top: y, transform: 'translateX(-50%)',
    color, fontFamily: family, whiteSpace: 'nowrap', textAlign: 'center'}}>
    <div style={{fontSize: 54, fontWeight: weight, lineHeight: 1.2}}>{names[i]}</div>
    <div style={{marginTop: 15, fontSize: 134, fontWeight: weight, lineHeight: 1.12,
      letterSpacing: '-.045em', fontVariantNumeric: 'lining-nums'}}>
      {i === 1 && <span style={{fontSize: 43, marginRight: 12, letterSpacing: 0}}>约</span>}
      {values[i]}<span style={{fontSize: 43, letterSpacing: 0, marginLeft: 12}}>枚</span>
    </div>
  </div>;
}
function Note({color}: {color: string}) {
  return <Type x={90} y={994} size={48} style={{color, fontWeight: 450}}>
    固定10%为数学演示，非实际回报；无追加投入，不计税费及通胀
  </Type>;
}
function Paper({density, ready}: {density: number; ready: () => void}) {
  const ink = '#342b22';
  return <div style={{position: 'absolute', inset: 0, background: '#ece6d8', color: ink}}>
    <svg width="1920" height="1080" style={{position: 'absolute', inset: 0}} aria-hidden="true">
      <defs>
        <linearGradient id="paper-light" x2="1" y2="1"><stop stopColor="#fffcf3"/>
          <stop offset=".65" stopColor="#eee6d6"/><stop offset="1" stopColor="#d3c8b3"/></linearGradient>
        <radialGradient id="paper-halo"><stop stopColor="#fffdf7"/><stop offset="1" stopColor="#fffdf7" stopOpacity="0"/></radialGradient>
      </defs>
      <rect width="1920" height="1080" fill="url(#paper-light)"/>
      <ellipse cx="1430" cy="530" rx="780" ry="650" fill="url(#paper-halo)"/>
      {Array.from({length: 11}, (_, i) => <ellipse key={i} cx="1440" cy="822"
        rx={390 + i * 45} ry={155 + i * 43} fill="none" stroke="#a78b65" strokeWidth="1.3" opacity=".15"/>)}
      <path d="M676 0V960M90 960H1830" stroke="#9c8b70" opacity=".48"/>
      <circle cx="562" cy="709" r="44" fill="#cf583a"/>
      <path d="M677 932L1920 813V1080H677Z" fill="#8a7554" opacity=".05"/>
    </svg>
    <Type x={79} y={87} size={242} style={{fontFamily: serif, fontWeight: 800,
      letterSpacing: '-.055em'}}>复利</Type>
    <Type x={91} y={425} size={57} style={{fontFamily: serif, lineHeight: 1.5, fontWeight: 500}}>
      让收益，<br/>成为下一次本金。
    </Type>
    <Type x={91} y={783} size={55} style={{fontFamily: serif, fontWeight: 500}}>
      30年后的总资产
    </Type>
    <EditorialStage variant={0} density={density} onReady={ready}/>
    {[920, 1500].map((x, i) => <Readout key={i} i={i} x={x} y={280} family={serif} color={ink} weight={600}/>)}
    <Note color="#746653"/>
  </div>;
}
function Blueprint({density, ready}: {density: number; ready: () => void}) {
  const white = '#fff7df';
  return <div style={{position: 'absolute', inset: 0, color: white,
    background: 'radial-gradient(ellipse at 70% 74%, #375de6 0%, #2047d0 45%, #1738a8 100%)'}}>
    <svg width="1920" height="1080" style={{position: 'absolute', inset: 0}} aria-hidden="true">
      <defs><linearGradient id="blue-halo" x2="0" y2="1"><stop stopColor="#91b1ff" stopOpacity=".3"/>
        <stop offset="1" stopColor="#91b1ff" stopOpacity="0"/></linearGradient></defs>
      <circle cx="1435" cy="693" r="565" fill="url(#blue-halo)"/>
      {[0, 1, 2, 3].map(i => <circle key={i} cx="1435" cy="693" r={565 - i * 39}
        fill="none" stroke="#a8bcff" opacity={.18 - i * .025} strokeWidth="1.5"/>)}
      <path d="M90 305H1830M90 965H1830M960 340V945" stroke="#b7c8ff" opacity=".35"/>
      {Array.from({length: 15}, (_, i) => <path key={i} d={`M${90 + i * 124} 965v-12`}
        stroke="#b7c8ff" opacity=".45" strokeWidth="2"/>)}
    </svg>
    <Type x={91} y={50} size={235} style={{fontFamily: 'M2V QingKe', letterSpacing: '.025em'}}>复利</Type>
    <Type x={820} y={107} size={62} style={{fontWeight: 600}}>让收益，继续生息。</Type>
    <Type x={822} y={202} size={48} style={{fontWeight: 400, opacity: .85}}>30年后的总资产</Type>
    <EditorialStage variant={1} density={density} onReady={ready}/>
    {[510, 1380].map((x, i) => <Readout key={i} i={i} x={x} y={330} color={white} weight={550}/>)}
    <Note color="#ced8ff"/>
  </div>;
}
function Terracotta({density, ready}: {density: number; ready: () => void}) {
  const pale = '#ffebce';
  return <div style={{position: 'absolute', inset: 0, color: pale,
    background: 'linear-gradient(130deg, #80432f, #a6563b 55%, #b96a49)'}}>
    <svg width="1920" height="1080" style={{position: 'absolute', inset: 0}} aria-hidden="true">
      <defs>
        <linearGradient id="arch-light" x2="1" y2="1"><stop stopColor="#c87954"/>
          <stop offset=".6" stopColor="#dc9b6e"/><stop offset="1" stopColor="#edbd87"/></linearGradient>
        <linearGradient id="arch-edge"><stop stopColor="#512c22" stopOpacity=".45"/>
          <stop offset="1" stopColor="#512c22" stopOpacity="0"/></linearGradient>
      </defs>
      <path d="M658 976V500C658 100 1120 85 1480 180C1780 255 1920 480 1920 700V976Z" fill="url(#arch-light)"/>
      <path d="M658 976V500C658 100 1120 85 1480 180C1070 100 686 230 686 520V976Z" fill="url(#arch-edge)"/>
      <path d="M658 922H1920V1080H658Z" fill="#f0bb82" opacity=".17"/>
      <path d="M658 922H1920" stroke="#f5d1a3" strokeWidth="2" opacity=".6"/>
      <path d="M90 915H554" stroke="#ecc9a6" opacity=".6"/>
    </svg>
    <Type x={77} y={104} size={245} style={{fontFamily: serif, fontWeight: 800,
      lineHeight: 1.08, letterSpacing: '-.08em', textShadow: '1px 3px 0 #713b2a'}}>复<br/>利</Type>
    <Type x={91} y={703} size={55} style={{fontFamily: serif, fontWeight: 500, lineHeight: 1.5}}>
      时间，<br/>让收益叠加。
    </Type>
    <Type x={823} y={94} size={54} style={{fontFamily: serif, fontWeight: 600}}>30年后的总资产</Type>
    <EditorialStage variant={2} density={density} onReady={ready}/>
    {[920, 1510].map((x, i) => <Readout key={i} i={i} x={x} y={292} family={serif} color="#48291e" weight={600}/>)}
    <Note color="#ffe1bb"/>
  </div>;
}
export default function EditorialPoster({variant, density, ready}: {
  variant: EditorialVariant; density: number; ready: () => void;
}) {
  return variant === 0 ? <Paper density={density} ready={ready}/>
    : variant === 1 ? <Blueprint density={density} ready={ready}/>
      : <Terracotta density={density} ready={ready}/>;
}
