import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,progress,enter,mix,useClock} from './shared';
import {Backdrop} from './details';
import {Portal} from './portal';
export default function Bridge(config:CodeSceneProps){
 const {f,e}=useClock(config),enterAt=e.frame('portal-enter'),q=enter(progress(f,0,enterAt));
 const lineEnd=mix(965,1490,q),bend=enter(progress(f,enterAt-6,enterAt));
 return <Frame config={config}>
  <Backdrop id="bridge-stage"/>
  <g opacity={1-enter(progress(f,0,6))}>
   <Text x={1440} y={560} text="30" size={300} numeric weight={550} role="bridge-count"/>
   <Text x={1440} y={830} text="上场次数" size={80} role="bridge-count-label"/>
  </g>
  <path d={`M240 464 H${lineEnd} Q${lineEnd+28*bend} ${464+90*bend} ${lineEnd} ${464+146*bend}`}
    stroke={q>.5?GOLD:WHITE} strokeWidth={3} fill="none" opacity={1-q*.75} data-m2v-role="bridge-record-line"/>
  <circle cx={1490} cy={610} r={36} stroke={GOLD} strokeWidth={3} fill="none"
    pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-bend} opacity={bend*(1-q*.4)} data-m2v-role="bridge-ring-seed"/>
  <Portal frame={f-enterAt}/>
 </Frame>;
}
