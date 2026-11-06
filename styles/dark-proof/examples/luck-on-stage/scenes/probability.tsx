import {arcPath,type CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,RED,MUTED,progress,enter,smooth,pop,track,useClock} from './shared';
import {Backdrop} from './details';
import {AccentRelease} from './cues';
import {Portal,PORTAL_FRAMES} from './portal';

export default function Probability(config:CodeSceneProps){
 const {f,e}=useClock(config),rise=e.frame('rise'),lock=e.frame('lock');
 const p=.1+.2*smooth(progress(f,rise,lock));
 const cx=610,cy=530,r=246,theta=p*Math.PI*2;
 const tip={x:cx+Math.sin(theta)*302,y:cy-Math.cos(theta)*302};
 const lockGlow=track(f,[[lock,0],[lock+2,1],[lock+6,.4],[lock+14,0]]);
 return <Frame config={config} overlay={<AccentRelease f={f} at={lock} x={1375} y={525} id="probability-thirty-flash" scale={.7}/> }>
  <Backdrop id="probability-stage"/>
  <g opacity={enter(progress(f,0,e.frame('portal-exit')))}>
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
  <path d={arcPath(cx,cy,r+56,Math.max(1,p*360-7),p*360+7)} fill="none" stroke={GOLD} strokeWidth={7} opacity={.45+.4*smooth(progress(f,rise,lock))}/>
  <circle cx={cx} cy={cy} r={r+55+45*enter(progress(f,lock,lock+16))} fill="none" stroke={GOLD} strokeWidth={3} opacity={lockGlow*.7}/>
  <path d={`M${tip.x-28} ${tip.y}L${tip.x+28} ${tip.y}`} stroke={WHITE} strokeWidth={3} opacity={lockGlow*.7}/>
  <path d={`M${tip.x} ${tip.y-28}L${tip.x} ${tip.y+28}`} stroke={WHITE} strokeWidth={3} opacity={lockGlow*.7}/>
  <Text x={1735} y={825} text="示意模型" size={23} color={MUTED} align="end"/>
  </g>
  <Portal frame={f-e.frame('portal-exit')+PORTAL_FRAMES}/>
 </Frame>;
}
