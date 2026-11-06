import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,progress,enter,smooth,mix,useClock} from './shared';
import {Attempt} from './attempt';
import {Contact} from './cues';
import {Backdrop} from './details';
export default function Closing(config:CodeSceneProps){
 const {f,e}=useClock(config),first=e.frame('first'),second=e.frame('second'),land=e.frame('land');
 const q=progress(f,second,land),p=smooth(q);
 return <Frame config={config}>
  <Backdrop id="closing-stage"/>
  <Text x={960} y={340} text="多上场，" size={164} alpha={enter(progress(f,first,first+12))} role="closing-first"/>
  <Text x={960} y={620} text="把每一次做好" size={146} color={GOLD} alpha={enter(progress(f,second,second+14))} role="closing-second"/>
  <Attempt x={mix(1450,1650,p)+80*Math.sin(p*Math.PI)} y={340+310*q*q-110*Math.sin(q*Math.PI)} size={92} color={f>=land?GOLD:WHITE} alpha={enter(progress(f,first,first+10))} frame={f} landAt={land} glow={f<land?.35:.18}/>
  <Contact f={f} at={land} x={1650} y={650} strength={.5} kind="touch" seed="closing-period"/>
 </Frame>;
}
