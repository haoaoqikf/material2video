import {arcPath,type CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,RED,MUTED,progress,enter,smooth,mix,pop,useClock} from './shared';
import {Backdrop} from './details';
import {Contact} from './cues';
import {Attempt} from './attempt';

export default function Probability(config:CodeSceneProps){
 const {f,e}=useClock(config),rise=e.frame('rise'),lock=e.frame('lock');
 const p=.1+.2*smooth(progress(f,rise,lock));
 const cx=610,cy=530,r=246,theta=p*Math.PI*2;
 const tip={x:cx+Math.sin(theta)*302,y:cy-Math.cos(theta)*302};
 const drop={x:tip.x,y:tip.y+44};
 return <Frame config={config}>
  <Backdrop id="probability-stage"/>
  <Text x={960} y={130} text="单次成功概率" size={116} role="probability-title"/>
  {Array.from({length:10},(_,i)=>{
   const a=i*36+1.5,b=(i+1)*36-1.5,fill=Math.min(b,p*360);
   return <g key={i}>
    <path d={arcPath(cx,cy,r,a,b)} fill="none" stroke={RED} strokeWidth={110} opacity={.26}/>
    {fill>a?<path d={arcPath(cx,cy,r,a,fill)} fill="none" stroke={GOLD} strokeWidth={110}/>:null}
   </g>;
  })}
  <circle cx={cx} cy={cy} r={185} fill="none" stroke={WHITE} strokeWidth={1.5} opacity={.12}/>
  <Text x={cx} y={505} text="成功区域" size={76} color={GOLD}/>
  <path d={`M${cx+Math.sin(Math.PI*.2)*181} ${cy-Math.cos(Math.PI*.2)*181}L${cx+Math.sin(Math.PI*.2)*310} ${cy-Math.cos(Math.PI*.2)*310}`} stroke={WHITE} strokeWidth={2} strokeDasharray="5 8" opacity={.5*enter(progress(f,rise,rise+12))}/>
  <Text x={1375} y={340} text="从 10%" size={84} color={MUTED}/>
  <Text x={1375} y={525} text={`${Math.round(p*100)}%`} size={248} numeric weight={500} color={f>=lock?GOLD:WHITE} scale={pop(f,lock,.035)} role="probability-value"/>
  <Text x={1375} y={750} text={`未中 ${100-Math.round(p*100)}%`} size={76} color={RED} role="failure-value"/>
  <Attempt x={drop.x} y={drop.y} size={80} color={f>=lock?GOLD:WHITE} tilt={f<lock?-10:0} stretch={1+.08*Math.sin(Math.PI*progress(f,rise,lock))}/>
  <Contact f={f} at={lock} x={tip.x} y={tip.y} strength={.45} seed="probability-thirty"/>
  <Text x={1735} y={825} text="示意模型" size={23} color={MUTED} align="end"/>
 </Frame>;
}
