import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,GOLD,progress,enter,track,useClock} from './shared';
import {Backdrop} from './details';
export default function Closing(config:CodeSceneProps){
 const {f,e}=useClock(config),first=e.frame('first'),second=e.frame('second'),land=e.frame('land');
 const reveal=enter(progress(f,second,land));
 const glint=track(f,[[land,0],[land+2,1],[land+8,.2],[land+15,0]]);
 return <Frame config={config}>
  <Backdrop id="closing-stage"/>
  <Text x={960} y={340} text="多上场，" size={164} alpha={enter(progress(f,first,first+12))} role="closing-first"/>
  <Text x={960} y={620} text="把每一次做好" size={146} color={GOLD} alpha={enter(progress(f,second,second+14))} role="closing-second"/>
  <path d="M650 458H1270" stroke={GOLD} strokeWidth={2} opacity={.35*enter(progress(f,first,first+22))} data-m2v-role="closing-first-rule"/>
  <path d="M540 744H1380" stroke={GOLD} strokeWidth={4} opacity={.55} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-reveal} data-m2v-role="closing-second-rule"/>
  <path d="M1355 744H1410" stroke={GOLD} strokeWidth={8} opacity={glint} />
 </Frame>;
}
