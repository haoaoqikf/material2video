import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,progress,enter,smooth,mix,useClock} from './shared';
import {Attempt} from './attempt';
import {Contact} from './cues';
import {Backdrop} from './details';
import {Portal} from './portal';
export default function Bridge(config:CodeSceneProps){
 const {f,e}=useClock(config),more=e.frame('more'),better=e.frame('better'),join=e.frame('join');
 const q=progress(f,better,join),p=smooth(q);
 const passage=f-e.frame('portal-enter'),contentAlpha=1-smooth(progress(passage,0,12));
 return <Frame config={config}>
  <Backdrop id="bridge-stage"/>
  <g opacity={contentAlpha}>
  <Text x={960} y={350} text="多上场" size={160} alpha={enter(progress(f,more,more+10))} role="bridge-first"/>
  <Text x={960} y={665} text="把每次做好" size={146} alpha={enter(progress(f,better,better+12))} color={GOLD} role="bridge-second"/>
  <path d="M720 465H1200" stroke={WHITE} strokeWidth={3} opacity={.4} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-enter(progress(f,more,more+16))}/>
  <path d="M595 780H1325" stroke={GOLD} strokeWidth={3} opacity={.6} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1-enter(progress(f,better,join))}/>
  <Attempt x={mix(1370,1490,p)+150*Math.sin(p*Math.PI)} y={330+320*q*q-90*Math.sin(q*Math.PI)} size={82*(1-.7*enter(progress(passage,0,6)))} color={f>=join?GOLD:WHITE} alpha={enter(progress(f,more,more+8))*(1-enter(progress(passage,2,7)))} frame={f} landAt={join} glow={.3}/>
  <Contact f={f} at={join} x={1490} y={650} strength={.35} kind="touch" seed="bridge-better"/>
  </g>
  <Portal frame={passage}/>
 </Frame>;
}
