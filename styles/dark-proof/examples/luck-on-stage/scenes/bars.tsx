import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,MUTED,LINE,progress,enter,smooth,mix,track,pop,useClock} from './shared';
import {Backdrop} from './details';
import {Contact} from './cues';
import {Attempt} from './attempt';

const CASES=[{n:10,p:10,result:1},{n:30,p:10,result:3},{n:30,p:30,result:9}];
export default function Bars(config:CodeSceneProps){
 const {f,e}=useClock(config),base=650,maxH=414;
 const ids=['one','three','nine'];
 const stages=CASES.map((c,i)=>{
  const start=e.frame(`${ids[i]}-start`),lock=e.frame(`${ids[i]}-lock`);
  return {...c,x:450+i*490,start,lock,height:c.result/9*maxH*enter(progress(f,start,lock))};
 });
 const current=f<stages[1].start?0:f<stages[2].start?1:2;
 const active=stages[current],previous=stages[Math.max(0,current-1)];
 const flight=current===0?1:smooth(progress(f,active.start-8,active.start+18));
 const secondView=smooth(progress(f,stages[1].start-8,stages[1].start+22));
 const finalView=smooth(progress(f,stages[2].start-20,stages[2].start+8));
 const zoom=mix(mix(4,1.6,secondView),1,finalView);
 const center=mix(mix(stages[0].x,720,secondView),960,finalView);
 const screenX=(x:number)=>960+(x-center)*zoom;
 const screenY=(height:number)=>base-height*zoom;
 const x=screenX(mix(previous.x,active.x,flight)),surface=mix(screenY(previous.height),screenY(active.height),flight);
 const hop=current===0?0:150*Math.sin(Math.PI*flight);
 const lift=18*Math.sin(Math.PI*progress(f,active.lock,active.lock+16));
 const impact=f>=active.lock?active.lock+16:current===0?active.lock:active.start+18;
 const labels=enter(progress(f,e.frame('nine-start')+4,e.frame('nine-start')+18));
 return <Frame config={config}>
  <Backdrop id="bars-stage"/>
  <Text x={960} y={130} text="预期成功次数" size={116} role="bars-title"/>
  <g>
   <path d={`M220 ${base}H1690`} stroke={LINE} strokeWidth={3}/>
   {stages.map((s,i)=>{
    if(f<s.start)return null;
    const visible=enter(progress(f,s.start,s.start+10)),gold=i===2&&f>=s.lock;
    return <g key={i} opacity={visible}>
     <rect x={screenX(s.x)-91*zoom} y={screenY(s.height)} width={182*zoom} height={s.height*zoom} fill={gold?GOLD:WHITE} opacity={i===current?1:.68}/>
     <path d={`M${screenX(s.x)-91*zoom} ${screenY(s.height)}H${screenX(s.x)+91*zoom}`} stroke={i===current?GOLD:WHITE} strokeWidth={4}/>
     {f>=s.lock?<Text x={screenX(s.x)+91*zoom+65} y={screenY(s.height)+16} text={String(s.result)} size={i===current?154:110} numeric weight={550} color={gold?GOLD:WHITE} scale={pop(f,s.lock,.04)} role={`bar-result-${i}`}/>:null}
     {labels>0?<>
      <Text x={s.x} y={740} text={`${s.n}次`} size={70} color={WHITE} alpha={labels} role={`bar-count-${i}`}/>
      <Text x={s.x} y={840} text={`${s.p}%`} size={70} numeric color={i===2?GOLD:MUTED} alpha={labels} role={`bar-rate-${i}`}/>
     </>:null}
    </g>;
   })}
   {f>=stages[0].start?<Attempt x={x} y={surface-hop-lift-4} size={76} color={current===2?GOLD:WHITE} stretch={1+.18*Math.sin(Math.PI*flight)} groundY={surface-4} frame={f} landAt={impact}/>:null}
   <Contact f={f} at={e.frame('nine-lock')} x={screenX(stages[2].x)} y={screenY(maxH)} strength={1.05} seed="bar-nine-arrival"/>
   {f>=e.frame('three-start')&&f<e.frame('nine-start')+4?<Text x={960} y={815} text={`${active.n}次 · 每次${active.p}%`} size={92} role="current-conditions"/>:null}
  </g>
 </Frame>;
}
