import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,progress,enter,smooth,mix,useClock} from './shared';
import {Attempt} from './attempt';
import {Contact} from './cues';
import {Backdrop} from './details';
export default function Closing(config:CodeSceneProps){
 const {f,e}=useClock(config),first=e.frame('first'),second=e.frame('second'),land=e.frame('land');
 const p=smooth(progress(f,second,land));
 return <Frame config={config}>
  <Backdrop id="closing-stage"/>
  <Text x={960} y={340} text="多上场，" size={164} alpha={enter(progress(f,first,first+12))} role="closing-first"/>
  <Text x={960} y={620} text="把每一次做好" size={146} color={GOLD} alpha={enter(progress(f,second,second+14))} role="closing-second"/>
  <Attempt x={mix(1450,1650,p)+80*Math.sin(p*Math.PI)} y={mix(340,650,p)-120*Math.sin(p*Math.PI)} size={92} color={f>=land?GOLD:WHITE} alpha={enter(progress(f,first,first+10))} groundY={mix(340,650,p)} frame={f} landAt={land}/>
  <Contact f={f} at={land} x={1650} y={650} strength={.4} seed="closing-period"/>
 </Frame>;
}
