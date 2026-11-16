import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';

const question = '电报怎样传字？';
const answer = '把文字编码成电脉冲。';
const ink = '#f2e9d9';
const brass = '#e3bb83';
function CurledTape({count, settle, extent}: {count:number; settle:number; extent:number}) {
  const questionBand = 'M -150 392 C 248 312 592 295 1000 329 C 1169 344 1328 335 1518 222 C 1570 197 1616 189 1649 201 C 1641 242 1557 400 1450 462 C 1294 547 1130 556 960 524 C 635 462 198 501 -150 587 Z';
  const answerEdge = 'M -140 651 C 321 529 847 549 1284 589 C 1545 609 1673 556 1782 515 Q 1802 501 1802 531';
  const answerBand = `${answerEdge} C 1794 606 1738 706 1585 767 C 1452 826 1281 797 1106 773 C 636 709 249 755 -140 863 Z`;
  return <svg width="1920" height="1080" viewBox="0 0 1920 1080" style={{position:'absolute', inset:0}}>
    <defs>
      <linearGradient id="question-paper" x1="11%" x2="88%" y1="15%" y2="77%">
        <stop stopColor="#412616"/>
        <stop offset=".32" stopColor="#caac7c"/>
        <stop offset=".55" stopColor="#b49464"/>
        <stop offset=".76" stopColor="#634b34"/>
        <stop offset=".89" stopColor="#a78d66"/>
        <stop offset="1" stopColor="#472b18"/>
      </linearGradient>
      <linearGradient id="answer-paper" x1="0" x2="1" y1="0" y2=".32">
        <stop stopColor="#a1774b"/>
        <stop offset=".18" stopColor="#e5bc83"/>
        <stop offset=".38" stopColor="#ffe1a8"/>
        <stop offset=".74" stopColor="#e3b97e"/>
        <stop offset=".91" stopColor="#a67a47"/>
        <stop offset="1" stopColor="#61452f"/>
      </linearGradient>
      <radialGradient id="answer-light" gradientUnits="userSpaceOnUse" cx="700" cy="641" r="920">
        <stop stopColor="#fff1cd" stopOpacity=".43"/>
        <stop offset="1" stopColor="#f4d5a0" stopOpacity="0"/>
      </radialGradient>
      <radialGradient id="turn-shadow" cx="99%" cy="14%" r="40%">
        <stop stopColor="#38291e" stopOpacity=".71"/>
        <stop offset=".59" stopColor="#745639" stopOpacity=".19"/>
        <stop offset="1" stopColor="#8c6b4a" stopOpacity="0"/>
      </radialGradient>
      <filter id="paper-shadow" x="-.15" y="-.33" width="1.35" height="2.15">
        <feDropShadow dx="13" dy="32" stdDeviation="26" floodColor="#0b0c07" floodOpacity=".47"/>
      </filter>
      <path id="question-ink-line" d="M 174 456 C 400 418 690 426 1040 466"/>
      <path id="answer-ink-line" d="M 157 707 C 458 673 825 675 1110 701 C 1250 713 1330 718 1430 718"/>
      <linearGradient id="printed-ink" x1="8%" x2="91%" y1="10%" y2="87%">
        <stop stopColor="#523a22"/>
        <stop offset=".68" stopColor="#332318"/>
        <stop offset="1" stopColor="#22190f"/>
      </linearGradient>
      <filter id="paper-grain">
        <feTurbulence type="fractalNoise" baseFrequency=".56 .08" numOctaves="2" seed="19"/>
        <feColorMatrix type="saturate" values="0"/>
        <feComposite in2="SourceGraphic" operator="in"/>
      </filter>
    </defs>
    <g transform={`translate(0 ${-80*settle})`}>
      <path d={questionBand} fill="url(#question-paper)" filter="url(#paper-shadow)"/>
      <path d={questionBand} fill="#946341" filter="url(#paper-grain)" opacity=".18" style={{mixBlendMode:'multiply'}}/>
      <path d="M -110 386 C 244 315 594 295 1000 329 C 1169 344 1328 335 1518 222 C 1570 197 1616 189 1649 201" fill="none" stroke="#e1c38e" strokeOpacity=".57" strokeWidth="2"/>
      <path d={questionBand} fill="url(#turn-shadow)"/>
      <text fill="url(#printed-ink)" fontSize={103-26*settle} fontWeight="660" style={{mixBlendMode:'multiply'}}>
        <textPath href="#question-ink-line">{question}</textPath>
      </text>
    </g>
    {settle>0 && <g opacity={settle} transform={`translate(0 ${34*(1-settle)})`}>
      <g transform={`scale(${extent} 1)`}>
        <path d={answerBand} fill="url(#answer-paper)" filter="url(#paper-shadow)"/>
        <path d={answerBand} fill="url(#answer-light)"/>
        <path d={answerBand} fill="#bd9269" filter="url(#paper-grain)" opacity=".18" style={{mixBlendMode:'multiply'}}/>
        <path d={answerEdge} fill="none" stroke="#ffe8b4" strokeOpacity=".62" strokeWidth="2"/>
        <path d={answerBand} fill="url(#turn-shadow)"/>
      </g>
      <text fill="url(#printed-ink)" fontSize="113" fontWeight="680" style={{mixBlendMode:'multiply'}}>
        <textPath href="#answer-ink-line">
          {answer.slice(0,count)}
          {count<answer.length && <tspan fill="#973f23">▏</tspan>}
        </textPath>
      </text>
    </g>}
  </svg>;
}

export default function Language({props}: CodeSceneProps) {
  const {elapsedSeconds, ready} = useSceneContext();
  const conversation = props.layout === 'conversation';
  const count = Math.min(answer.length, Math.max(0, Math.floor((elapsedSeconds - .54) * 7.5)));
  const shift = Math.max(0, Math.min(1, (elapsedSeconds - .28) / .38));
  const settle = shift * shift * (3 - 2 * shift);
  const advance = Math.max(0, Math.min(1, (elapsedSeconds - .39) / 1.79));
  const extent = .19 + .81*(1-(1-advance)**1.4);
  useEffect(ready, [ready]);

  return <div style={{
    position:'absolute', inset:0, color:ink, overflow:'hidden',
    background:'radial-gradient(ellipse at 21% 43%, #3a3323 0%, #20231b 47%, #0a100d 100%)',
  }}>
    <div style={{position:'absolute', left:132, right:132, top:105, display:'flex', alignItems:'baseline', gap:43}}>
      <div style={{fontSize:65, fontWeight:650, letterSpacing:3}}>大语言模型</div>
      <div style={{fontSize:41, color:brass, fontVariantNumeric:'tabular-nums'}}>2020—2022</div>
    </div>
    {conversation
      ? <div style={{position:'absolute', top:321, left:246, right:246, padding:'46px 66px', background:'#242921', border:'1px solid #91856a66', borderRadius:22}}>
          <div style={{fontSize:50, color:'#e0cda9', textAlign:'right'}}>{question}</div>
          <div style={{marginTop:38, height:150, fontSize:82, fontWeight:600, letterSpacing:3, whiteSpace:'nowrap'}}>
            {answer.slice(0, count)}
            {count < answer.length && <span style={{display:'inline-block', width:6, height:73, marginLeft:10, background:brass, verticalAlign:'-.05em'}}/>}
          </div>
        </div>
      : <CurledTape count={count} settle={settle} extent={extent}/>}

    <div style={{position:'absolute', left:132, right:132, bottom:110, display:'flex', alignItems:'center', justifyContent:'space-between'}}>
      <div style={{fontSize:52, color:'#e9dbc5'}}>全球研究积累推动语言生成</div>
      <div style={{fontSize:32, color:'#d9c7ab'}}>生成示意</div>
    </div>
  </div>;
}
