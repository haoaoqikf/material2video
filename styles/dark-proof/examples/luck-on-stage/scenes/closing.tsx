import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,progress,enter,smooth,mix,useClock} from './shared';
import {Backdrop} from './details';
export default function Closing(config:CodeSceneProps){
 const {f,e}=useClock(config),one=e.frame('factor-one'),two=e.frame('factor-two'),lock=e.frame('lock');
 const first=enter(progress(f,one,one+16)),second=enter(progress(f,two,lock));
 const formulaAlpha=1-smooth(progress(f,0,18)),marksAlpha=(1-first)*enter(progress(f,one,one+4));
 return <Frame config={config}>
  <Backdrop id="closing-stage"/>
  <g opacity={formulaAlpha}>
   <Text x={960} y={130} text="预期成功次数" size={116}/>
   <Text x={420} y={450} text="30" size={220} numeric weight={500}/>
   <Text x={700} y={450} text="×" size={100} numeric/>
   <Text x={1000} y={450} text="30%" size={220} numeric weight={500}/>
   <Text x={1320} y={450} text="=" size={100} numeric/>
   <Text x={1580} y={450} text="9" size={250} numeric weight={550} color={GOLD}/>
   <Text x={420} y={730} text="尝试次数" size={74}/>
   <Text x={1000} y={730} text="单次成功概率" size={74}/>
   <Text x={1580} y={730} text="预期次数" size={74} color={GOLD}/>
  </g>
  <g opacity={marksAlpha} data-m2v-effect="trial-marks">
   {Array.from({length:15},(_,i)=><path key={i}
     d={`M${mix(385+i*5,640+i*28,first)} ${mix(530,360+(i%3-1)*22,first)}v${16-i%3*4}`}
     stroke={WHITE} strokeWidth={5} strokeLinecap="round"/>)}
  </g>
  <circle cx={1000} cy={450} r={70+60*second} fill="none" stroke={GOLD} strokeWidth={4}
    pathLength={1} strokeDasharray=".3 .7" strokeDashoffset={.3*(1-second)} opacity={second*(1-second)*2.4} data-m2v-effect="probability-arc"/>
  <defs>
   <clipPath id="closing-more-reveal"><rect x={280} y={240} width={780*first} height={260}/></clipPath>
   <clipPath id="closing-better-reveal"><rect x={1680-1120*second} y={500} width={1120*second} height={260}/></clipPath>
  </defs>
  <g clipPath="url(#closing-more-reveal)"><Text x={300} y={370} text="多尝试，" size={164} align="start" role="closing-first"/></g>
  <g clipPath="url(#closing-better-reveal)"><Text x={1660} y={630} text="提高成功概率" size={146} align="end" color={GOLD} role="closing-second"/></g>
 </Frame>;
}
