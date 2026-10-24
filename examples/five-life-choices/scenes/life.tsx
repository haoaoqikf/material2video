import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import LearningWindow from './learningWindow';
import {ACTS, actAt, smooth01} from './lifeMath';

const PAPER = '#FFF9EE';
const GROUND = '#EAE1D3';
const INK = '#26272D';
const MID = '#C9C1B4';
const ACCENT = '#E66A3B';

type CopyItem = {id: string; text: string; from: number; to: number; size: number; tone: string; align: string;
  x: number; y: number; width: number; weight: number; spacing: number};
type LifeProps = {copy: CopyItem[]; labels: {choices: string[]}};

function figure(x: number, foot: number, scale = 1, raised = false, mirrored = false) {
  return <g transform={`translate(${x} ${foot - 150 * scale}) scale(${mirrored ? -scale : scale} ${scale})`} fill={INK} stroke={INK}
    strokeWidth="15" strokeLinecap="round" strokeLinejoin="round">
    <circle cy="0" r="24" stroke="none"/>
    <path d="M-4 30Q-18 25-27 44L-37 85Q-41 98-24 105L0 111L24 99L20 46Q17 31 4 30Z" stroke="none"/>
    <path d={raised ? 'M-8 100L-37 137M10 100L32 129M-23 49L-49 73M17 48L48 21' : 'M-8 100L-31 136M10 100L34 136M-23 49L-48 71M17 48L46 64'} fill="none"/>
    <path d="M-48 142h31M19 142h31" fill="none" strokeWidth="13"/>
  </g>;
}

function Cutout({t, act}: {t: number; act: string}) {
  const p = (id: string) => {
    const item = ACTS.find((a) => a.id === id)!;
    return smooth01((t - item.start) / (item.end - item.start));
  };
  const city = p('city');
  const industry = p('industry');
  const industryFast = 1 - Math.pow(1 - industry, 3);
  const partner = p('partner');
  const investment = p('investment');
  const finale = p('finale');
  const investmentStage = investment * 7;
  const investmentStep = Math.min(6, Math.floor(investmentStage));
  const investmentPhase = investmentStage >= 7 ? 1 : investmentStage - investmentStep;
  const investmentRise = investmentStep + smooth01((investmentPhase - .72) / .28);
  const investmentX = 430 + investmentStage * 110;
  const investmentFoot = 813 - investmentRise * 40;
  if (act === 'learning') return <LearningWindow time={t - 23}/>;

  return <svg viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid meet" aria-hidden="true"
    style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
    <defs>
      <filter id="paper-shadow" x="-20%" y="-20%" width="140%" height="150%">
        <feDropShadow dx="0" dy="12" stdDeviation="10" floodColor="#3A3025" floodOpacity=".12"/>
      </filter>
    </defs>
    <rect width="1920" height="1080" fill="#F4EDDF"/>
    <path d="M0 805Q480 780 960 805T1920 798V1080H0Z" fill={GROUND}/>
    <path d="M0 805Q480 780 960 805T1920 798" fill="none" stroke="#D8CEBE" strokeWidth="5"/>
    <ellipse cx="960" cy="830" rx="680" ry="42" fill={INK} opacity=".07"/>

    {act === 'opening' && <g filter="url(#paper-shadow)">
      <path d="M-60 870H1980V1000H-60Z" fill={PAPER}/>
      <path d="M-60 870H1980" stroke={MID} strokeWidth="7"/>
      <path d="M960 870L700 530M960 870L1210 530" fill="none" stroke={MID} strokeWidth="15"/>
      <path d="M960 870L790 640" fill="none" stroke={ACCENT} strokeWidth="20" strokeLinecap="round"/>
      {figure(960 - 420 * smooth01(t / 2.5), 850, 1.15, true)}
      <circle cx="960" cy="870" r="25" fill={ACCENT}/>
    </g>}

    {act === 'city' && <g filter="url(#paper-shadow)">
      <path d="M190 805V350H550V805ZM650 805V240H1010V805ZM1110 805V405H1470V805Z" fill={PAPER} stroke={MID} strokeWidth="8"/>
      {[0,1,2,3].map((i) => <g key={i}>
        <rect x={245 + i * 82} y="430" width="46" height="68" rx="22" fill={i < 3 ? '#E6DED1' : ACCENT}/>
        <rect x={700 + i * 82} y="320" width="46" height="68" rx="22" fill={i < 2 ? '#E6DED1' : ACCENT}/>
        <rect x={1160 + i * 82} y="485" width="46" height="68" rx="22" fill="#E6DED1"/>
      </g>)}
      <path d="M0 805H1920" stroke={ACCENT} strokeWidth="18"/>
      <path d="M500 805C620 745 640 650 780 610S960 650 1040 520" fill="none" stroke={ACCENT} strokeWidth="18" strokeLinecap="round"/>
      {[500,700,860,1040].map((x, i) => <circle key={x} cx={x} cy={805 - i * 75} r="19" fill={PAPER} stroke={ACCENT} strokeWidth="10"/>)}
      {figure(520 + 520 * city, 790, 1.04, true)}
    </g>}

    {act === 'industry' && <g filter="url(#paper-shadow)">
      <path d="M120 805H1800V920H120Z" fill={PAPER} stroke={MID} strokeWidth="6"/>
      <path d="M120 805H1800V920H120Z" transform={`translate(0 ${-300 * industryFast})`} fill={PAPER} stroke={MID} strokeWidth="6"/>
      <path d="M120 805H1800" stroke={MID} strokeWidth="12"/>
      <path d={`M120 ${805 - 300 * industryFast}H1800`} stroke={ACCENT} strokeWidth="16"/>
      {/* Keep the parallel routes legible: the faster route advances farther right. */}
      {figure(370 + industry * 160, 790, 1.05, true)}
      {figure(650 + industryFast * 1000, 813 - industryFast * 300, 1.05, true)}
      <path d="M1540 805v-54m-28 28 28-28 28 28" fill="none" stroke={ACCENT} strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/>
    </g>}

    {act === 'partner' && <g filter="url(#paper-shadow)">
      <path d="M180 805H760L930 665H1050L1220 805H1740V910H180Z" fill={PAPER} stroke={MID} strokeWidth="8"/>
      <path d="M920 665H1060" stroke={ACCENT} strokeWidth="22" strokeLinecap="round"/>
      <path d="M930 655L980 605L1030 655" fill="none" stroke={ACCENT} strokeWidth="13" strokeLinejoin="round"/>
      {figure(480 + 200 * partner, 790, 1.08, true)}
      {partner > .35 && figure(1430 - 190 * partner, 790, 1.08, true, true)}
      <path d="M620 785C760 720 870 720 980 640C1080 710 1170 740 1320 785" fill="none" stroke={ACCENT} strokeWidth="12" strokeDasharray={`${650 * partner} 800`} strokeLinecap="round"/>
      <circle cx="980" cy="640" r="24" fill={ACCENT}/>
    </g>}

    {act === 'investment' && <g filter="url(#paper-shadow)">
      <path d="M180 805H1740V920H180Z" fill={PAPER} stroke={MID} strokeWidth="7"/>
      {[0,1,2,3,4,5,6].map((i) => {
        const h = (i + 1) * 40;
        const reveal = smooth01((investment * 7 - i) / .55);
        return reveal > 0 ? <g key={i} opacity={reveal}>
          <path d={`M${540 + i * 110} ${805 - h}h100v${h}h-100Z`} fill={i === 0 ? ACCENT : '#D9CEBE'} stroke={i === 0 ? ACCENT : '#B9AD9B'} strokeWidth="6"/>
          <path d={`M${540 + i * 110} ${805 - h}l28-20h100l-28 20Z`} fill={PAPER} stroke={MID} strokeWidth="5"/>
        </g> : null;
      })}
      <path d="M430 805H540V765H650V725H760V685H870V645H980V605H1090V565H1200V525H1300" fill="none" stroke={ACCENT} strokeWidth="13" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${1150 * investment} 1600`}/>
      {figure(investmentX, investmentFoot, 1.05, true)}
    </g>}

    {act === 'finale' && <>
      <g opacity={.38 + .62 * finale} filter="url(#paper-shadow)">
        {(() => {
          const settle = smooth01(finale / .55);
          const hubX = 1520 - 560 * settle;
          const hubY = 650 + 155 * settle;
          const ends = [[300,500],[650,340],[960,320],[1300,340],[1620,500]];
          return <>
            {ends.map(([x, y], i) => <path key={i} d={`M${hubX} ${hubY} C${hubX + (x - hubX) * .35} ${hubY - 30} ${hubX + (x - hubX) * .72} ${y + 25} ${x} ${y}`} fill="none" stroke={ACCENT} strokeWidth="26" strokeLinecap="round"/>)}
        <path d="M300 500l-82-70m82 70 78-80M650 340l-68-80m68 80 70-80M960 320V220M1300 340l-68-80m68 80 80-80M1620 500l-88-70m88 70 88-70" fill="none" stroke={INK} strokeWidth="16" strokeLinecap="round"/>
        {[300,650,960,1300,1620].map((x, i) => <circle key={i} cx={x} cy={[500,340,320,340,500][i]} r="34" fill={PAPER} stroke={ACCENT} strokeWidth="12"/>)}
            <circle cx={hubX} cy={hubY} r="22" fill={ACCENT}/>
            {figure(hubX, hubY, 1.18, true)}
          </>;
        })()}
      </g>
    </>}
  </svg>;
}

function CopyLayer({copy, t}: {copy: CopyItem[]; t: number}) {
  return <div style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
    {copy.map((item) => {
      const opacity = smooth01((t - item.from) / .35) * (item.to >= 29.9 ? 1 : 1 - smooth01((t - item.to) / .3));
      if (opacity < .01) return null;
      return <div key={item.id} style={{position: 'absolute', left: item.x, top: item.y, width: item.width,
        color: item.tone === 'accent' ? ACCENT : INK, fontSize: item.size, fontWeight: item.weight,
        letterSpacing: item.spacing, lineHeight: 1.12, opacity, textAlign: item.align as 'left' | 'center' | 'right',
        whiteSpace: 'pre-wrap'}}>{item.text}</div>;
    })}
  </div>;
}

export default function Life(config: CodeSceneProps) {
  const clock = useSceneContext();
  const props = config.props as unknown as LifeProps;
  if (!props || !Array.isArray(props.copy) || !props.labels?.choices) throw new Error('人生五选择缺少 copy 或 choices');
  const t = Math.max(0, Math.min(30, clock.elapsedSeconds));
  const act = actAt(t);
  useEffect(() => { clock.ready(); }, [clock.ready]);
  return <div style={{position: 'relative', width: config.width, height: config.height, overflow: 'hidden', background: '#F4EDDF'}}>
    <Cutout t={t} act={act}/>
    <CopyLayer copy={props.copy} t={t}/>
  </div>;
}
