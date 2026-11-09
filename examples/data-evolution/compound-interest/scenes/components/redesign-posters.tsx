import type {CSSProperties, ReactNode} from 'react';
import RedesignStage from './redesign-stage';
import type {RedesignVariant} from './redesign-stage';
import {comparison, MODEL, UNITS_PER_DISC} from '../compoundMath';

const result = comparison(MODEL.years);
const values = [String(result.withdraw.total / UNITS_PER_DISC),
  (result.reinvest.total / UNITS_PER_DISC).toFixed(1)];
const labels = ['收益取走', '收益再投入'];
const sans = '"M2V Sans"';
const inter = '"M2V Inter", "M2V Sans"';
const serif = '"M2V Serif"';
function Text({x, y, size, children, style = {}}: {
  x: number; y: number; size: number; children: ReactNode; style?: CSSProperties;
}) {
  return <div style={{position: 'absolute', left: x, top: y, fontFamily: sans,
    fontSize: size, fontWeight: 500, lineHeight: 1.1, whiteSpace: 'nowrap', ...style}}>{children}</div>;
}
function Note({color, x = 88, narrow = false}: {color: string; x?: number; narrow?: boolean}) {
  return <Text x={x} y={narrow ? 938 : 991} size={50} style={{color, fontWeight: 500, lineHeight: 1.2}}>
    固定10%为数学演示，非实际回报；{narrow && <br/>}无追加投入，不计税费及通胀
  </Text>;
}
function Amount({x, y, i, size = 144, font = inter, color, weight = 600}: {
  x: number; y: number; i: number; size?: number; font?: string; color?: string; weight?: number;
}) {
  return <Text x={x} y={y} size={size} style={{fontFamily: font, color,
    fontWeight: weight, letterSpacing: '-.065em', fontVariantNumeric: 'lining-nums'}}>
    {i === 1 && <span style={{fontFamily: font === serif ? serif : sans,
      fontSize: 40, letterSpacing: 0, marginRight: 14}}>约</span>}
    {values[i]}<span style={{fontFamily: font === serif ? serif : sans,
      fontSize: 42, letterSpacing: 0, marginLeft: 16, fontWeight: 500}}>枚</span>
  </Text>;
}

function Paper({density, ready}: {density: number; ready: () => void}) {
  const ink = '#252723';
  return <div style={{position: 'absolute', inset: 0, background: '#eeeae0', color: ink}}>
    <div style={{position: 'absolute', inset: 0, background:
      'linear-gradient(116deg, #fffdf7 0%, #f6f2e9 45%, #d7d4c9 100%)'}}/>
    <svg width="1920" height="1080" style={{position: 'absolute', inset: 0}} aria-hidden="true">
      <defs><linearGradient id="arch-shadow"><stop stopColor="#485047" stopOpacity=".13"/>
        <stop offset="1" stopColor="#485047" stopOpacity="0"/></linearGradient></defs>
      <path d="M1020 -90 L1920 370 L1920 455 L890 -75Z" fill="url(#arch-shadow)"/>
      <path d="M1450 -100 L1980 170 L1980 255 L1320 -90Z" fill="url(#arch-shadow)"/>
      <path d="M710 898 L1920 898 L1920 1080 L710 1080Z" fill="#ddd9ce"/>
      <path d="M710 898 L1920 898 L1920 914 L710 914Z" fill="#fbf8f1"/>
    </svg>
    <Text x={88} y={112} size={246} style={{fontWeight: 900, letterSpacing: '-.09em',
      transform: 'scaleX(.94)', transformOrigin: 'left top'}}>复利</Text>
    <div style={{position: 'absolute', left: 92, top: 414, width: 78, height: 9, background: '#bc4e30'}}/>
    <Text x={88} y={465} size={60} style={{fontWeight: 450, lineHeight: 1.38}}>让收益，<br/>继续生长。</Text>
    <Text x={91} y={714} size={48} style={{color: '#64675e'}}>30年后的总资产</Text>
    <RedesignStage variant={0} density={density} onReady={ready}/>
    {labels.map((label, i) => <Text key={label} x={i ? 1278 : 767} y={282} size={56}
      style={{fontWeight: 500}}>{label}</Text>)}
    <Amount x={776} y={360} i={0}/><Amount x={1224} y={360} i={1}/>
    <Note color="#686a61"/>
  </div>;
}
function Night({density, ready}: {density: number; ready: () => void}) {
  const white = '#f0f0e6';
  return <div style={{position: 'absolute', inset: 0, color: white, background:
    'radial-gradient(ellipse at 74% 75%, #24344b 0%, #111c2b 39%, #090f18 80%)'}}>
    <svg width="1920" height="1080" style={{position: 'absolute', inset: 0}} aria-hidden="true">
      <defs><linearGradient id="night-light" x2="0" y2="1"><stop stopColor="#7ca1cc" stopOpacity="0"/>
        <stop offset=".7" stopColor="#7ca1cc" stopOpacity=".12"/><stop offset="1" stopColor="#7ca1cc" stopOpacity="0"/>
      </linearGradient></defs>
      <path d="M1240 0 L1460 0 L1850 985 L730 985Z" fill="url(#night-light)"/>
      <ellipse cx="1300" cy="920" rx="620" ry="48" fill="#d3e0ea" opacity=".06"/>
      <path d="M98 975 L1822 975" stroke="#b0c5dd" strokeOpacity=".25"/>
      <path d="M98 980 L1822 980" stroke="#000" strokeOpacity=".5"/>
    </svg>
    <Text x={92} y={62} size={190} style={{fontWeight: 650, letterSpacing: '.04em',
      transform: 'scaleX(.73)', transformOrigin: 'left top'}}>复利</Text>
    <Text x={1140} y={108} size={48} style={{fontWeight: 300}}>让收益，也成为本金。</Text>
    <Text x={1143} y={185} size={42} style={{color: '#aab6c4'}}>30年后的总资产</Text>
    <RedesignStage variant={1} density={density} onReady={ready}/>
    {labels.map((label, i) => <Text key={label} x={i ? 1198 : 350} y={294} size={58}
      style={{fontWeight: 350, letterSpacing: '.05em'}}>{label}</Text>)}
    <Amount x={371} y={360} i={0} size={140} weight={350}/>
    <Amount x={1120} y={360} i={1} size={140} weight={350}/>
    <Note color="#9daabc"/>
  </div>;
}
function Red({density, ready}: {density: number; ready: () => void}) {
  const ink = '#b72d27';
  return <div style={{position: 'absolute', inset: 0, background: '#f2eee3', color: ink}}>
    <div style={{position: 'absolute', inset: '0 auto 0 0', width: 768, background: '#b72d27'}}/>
    <div style={{position: 'absolute', left: 799, right: 0, top: 0, height: 1080,
      background: 'linear-gradient(154deg, #f8f5eb 0%, #e9e3d6 100%)'}}/>
    <Text x={73} y={82} size={276} style={{fontFamily: serif, fontWeight: 800, color: '#f2eee3',
      letterSpacing: '-.085em'}}>复利</Text>
    <Text x={89} y={458} size={65} style={{fontFamily: serif, fontWeight: 450, color: '#f2eee3',
      lineHeight: 1.45}}>让收益，<br/>也成为本金。</Text>
    <Text x={91} y={820} size={59} style={{fontFamily: serif, color: '#f2eee3', fontWeight: 500}}>30年后的总资产</Text>
    <svg width="1920" height="1080" style={{position: 'absolute', inset: 0}} aria-hidden="true">
      <path d="M850 895 L1920 895" stroke="#c8bdab" strokeWidth="2"/>
      <path d="M850 900 L1920 900" stroke="#fff" strokeWidth="2"/>
    </svg>
    <RedesignStage variant={2} density={density} onReady={ready}/>
    {labels.map((label, i) => <Text key={label} x={i ? 1455 : 1000} y={285} size={56}
      style={{fontFamily: serif, fontWeight: 550}}>{label}</Text>)}
    <Amount x={1030} y={375} i={0} size={142} font={serif} weight={600}/>
    <Amount x={1380} y={375} i={1} size={142} font={serif} weight={600}/>
    <Note color="#716b62" x={850} narrow/>
  </div>;
}

export default function RedesignPoster({variant, density, ready}: {
  variant: RedesignVariant; density: number; ready: () => void;
}) {
  return variant === 0 ? <Paper density={density} ready={ready}/>
    : variant === 1 ? <Night density={density} ready={ready}/>
      : <Red density={density} ready={ready}/>;
}
