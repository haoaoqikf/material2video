import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,progress,enter,smooth,mix,useClock} from './shared';
import {Attempt} from './attempt';
import {Contact} from './cues';
import {Backdrop} from './details';
export default function Bridge(config:CodeSceneProps){
 const {f,e}=useClock(config),more=e.frame('more'),better=e.frame('better'),join=e.frame('join');
 const p=smooth(progress(f,better,join));
 return <Frame config={config}>
  <Backdrop id="bridge-stage"/>
  <Text x={960} y={350} text="多上场" size={160} alpha={enter(progress(f,more,more+10))} role="bridge-first"/>
  <Text x={960} y={665} text="把每次做好" size={146} alpha={enter(progress(f,better,better+12))} color={GOLD} role="bridge-second"/>
  <path d="M720 465H1200" stroke={WHITE} strokeWidth={3} opacity={.4} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-enter(progress(f,more,more+16))}/>
  <path d="M595 780H1325" stroke={GOLD} strokeWidth={3} opacity={.6} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-enter(progress(f,better,join))}/>
  <Attempt x={mix(1370,1490,p)+150*Math.sin(p*Math.PI)} y={mix(330,650,p)-110*Math.sin(p*Math.PI)} size={82} color={f>=join?GOLD:WHITE} alpha={enter(progress(f,more,more+8))} groundY={mix(330,650,p)} frame={f} landAt={join}/>
  <Contact f={f} at={join} x={1490} y={650} strength={.35} seed="bridge-better"/>
 </Frame>;
}
