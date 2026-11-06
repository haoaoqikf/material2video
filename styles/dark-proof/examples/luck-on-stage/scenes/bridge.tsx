import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,progress,enter,smooth,useClock} from './shared';
import {Backdrop} from './details';
import {Portal} from './portal';
export default function Bridge(config:CodeSceneProps){
 const {f,e}=useClock(config),more=e.frame('more'),better=e.frame('better'),join=e.frame('join');
 const passage=f-e.frame('portal-enter'),contentAlpha=1-smooth(progress(passage,0,12));
 return <Frame config={config}>
  <Backdrop id="bridge-stage"/>
  <g opacity={contentAlpha}>
  <Text x={960} y={350} text="多上场" size={160} alpha={enter(progress(f,more,more+10))} role="bridge-first"/>
  <Text x={960} y={665} text="把每次做好" size={146} alpha={enter(progress(f,better,better+12))} color={GOLD} role="bridge-second"/>
  <path d="M720 465H1200" stroke={WHITE} strokeWidth={3} opacity={.4} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-enter(progress(f,more,more+16))} data-m2v-role="bridge-first-rule"/>
  <path d="M595 780H1325" stroke={GOLD} strokeWidth={5} opacity={.8} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-enter(progress(f,better,join))} data-m2v-role="bridge-second-rule"/>
  <path d="M1325 780 Q1450 780 1490 610" fill="none" stroke={GOLD} strokeWidth={3} opacity={.75} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-enter(progress(f,join,join+9))}/>
  <circle cx={1490} cy={610} r={24+16*enter(progress(f,join+6,e.frame('portal-enter')))} fill="none" stroke={GOLD} strokeWidth={2.5} opacity={enter(progress(f,join+6,e.frame('portal-enter')))} />
  </g>
  <Portal frame={passage}/>
 </Frame>;
}
