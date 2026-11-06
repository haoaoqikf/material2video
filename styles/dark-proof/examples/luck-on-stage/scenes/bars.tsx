import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,MUTED,LINE,progress,enter,smooth,mix,mixHex,pop,useClock} from './shared';
import {Backdrop} from './details';
import {AccentRelease,Contact,FlightMotes,type LightSample} from './cues';
import {Attempt} from './attempt';

const CASES=[{n:10,p:10,result:1},{n:30,p:10,result:3},{n:30,p:30,result:9}];
const BALL_COLORS=[WHITE,'#DCC78C',GOLD] as const;
export default function Bars(config:CodeSceneProps){
 const {f,e}=useClock(config),base=650,maxH=414;
 const ids=['one','three','nine'];
 const stages=CASES.map((c,i)=>{
  const start=e.frame(`${ids[i]}-start`),lock=e.frame(`${ids[i]}-lock`);
  return {...c,x:450+i*490,start,lock,height:c.result/9*maxH*enter(progress(f,start,lock))};
 });
 const current=f<stages[1].start-8?0:f<stages[2].start-8?1:2;
 const active=stages[current],previous=stages[Math.max(0,current-1)];
 const launch=active.start-8,arrive=active.start+18;
 const flight=current===0?1:smooth(progress(f,launch,arrive));
 const secondView=smooth(progress(f,stages[1].start-8,stages[1].start+22));
 const finalView=smooth(progress(f,stages[2].start-20,stages[2].start+8));
 const zoom=mix(mix(4,1.6,secondView),1,finalView);
 const center=mix(mix(stages[0].x,720,secondView),960,finalView);
 const screenX=(x:number)=>960+(x-center)*zoom;
 const screenY=(height:number)=>base-height*zoom;
 const heightAt=(index:number,time:number)=>CASES[index].result/9*maxH*enter(progress(time,stages[index].start,stages[index].lock));
 const bodyAt=(time:number)=>{
  const q=current===0?1:smooth(progress(time,launch,arrive));
  const prevHeight=heightAt(Math.max(0,current-1),time),nextHeight=heightAt(current,time);
  const worldX=mix(previous.x,active.x,q),worldY=base-mix(prevHeight,nextHeight,q);
  const stretch=1+.1*Math.sin(Math.PI*q);
  // 跳跃高度在屏幕空间约 90px，避免镜头放大把球和光滴推入标题。
  return {x:screenX(worldX),y:base+(worldY-base)*zoom-(current===0?0:360*q*(1-q))-4,stretch,q};
 };
 const colorAt=(time:number)=>current===0?BALL_COLORS[0]:mixHex(BALL_COLORS[current-1],BALL_COLORS[current],enter(progress(time,launch+3,arrive-2)));
 const ball=bodyAt(f),ballColor=colorAt(f);
 const samples:LightSample[]=current===0?[]:Array.from({length:13},(_,i)=>f-i).filter(time=>time>=launch).map(time=>{
  const position=bodyAt(time);
  return {x:position.x,y:position.y-38*position.stretch,color:colorAt(time)};
 });
 const trailEnergy=current===0||f>=arrive+8?0:flight<1?Math.min(1,Math.sin(Math.PI*Math.min(flight,.6))*1.2):1-smooth(progress(f,arrive,arrive+8));
 const labels=enter(progress(f,e.frame('nine-start')+4,e.frame('nine-start')+18));
 return <Frame config={config} subtitleVariants={{10:{enter:'wipe',enterFrames:8,exitFrames:6}}} overlay={<>
  <AccentRelease f={f} at={e.frame('three-lock')} x={screenX(stages[1].x)} y={screenY(stages[1].height)} id="bar-three-flash" scale={.65}/>
  <AccentRelease f={f} at={e.frame('nine-lock')} x={screenX(stages[2].x)} y={screenY(stages[2].height)} id="bar-nine-flash" scale={.9}/>
 </>}>
  <Backdrop id="bars-stage"/>
  <Text x={960} y={130} text="预期成功次数" size={116} role="bars-title"/>
  <g>
   <path d={`M220 ${base}H1690`} stroke={LINE} strokeWidth={3}/>
   {stages.map((s,i)=>{
    if(f<s.start)return null;
    const visible=enter(progress(f,s.start,s.start+10)),gold=i===2&&f>=s.lock;
    return <g key={i} opacity={visible}>
     <rect x={screenX(s.x)-91*zoom} y={screenY(s.height)} width={182*zoom} height={s.height*zoom} fill={gold?GOLD:WHITE} opacity={i===current?1:.68}/>
     <path d={`M${screenX(s.x)-91*zoom} ${screenY(s.height)}H${screenX(s.x)+91*zoom}`} stroke={i===current?BALL_COLORS[i]:WHITE} strokeWidth={4}/>
     {f>=s.lock?<Text x={screenX(s.x)+91*zoom+65} y={screenY(s.height)+16} text={String(s.result)} size={i===current?154:110} numeric weight={550} color={BALL_COLORS[i]} scale={pop(f,s.lock,.04)} role={`bar-result-${i}`}/>:null}
     {labels>0?<>
      <Text x={s.x} y={740} text={`${s.n}次`} size={70} color={WHITE} alpha={labels} role={`bar-count-${i}`}/>
      <Text x={s.x} y={840} text={`${s.p}%`} size={70} numeric color={i===2?GOLD:MUTED} alpha={labels} role={`bar-rate-${i}`}/>
     </>:null}
    </g>;
   })}
   <FlightMotes samples={samples} energy={trailEnergy}/>
   {f>=stages[0].start?<Attempt x={ball.x} y={ball.y} size={76} color={ballColor} stretch={ball.stretch} groundY={screenY(active.height)-4} frame={f} landAt={active.lock} glow={.2+.3*trailEnergy}/>:null}
   <Contact f={f} at={e.frame('three-lock')} x={screenX(stages[1].x)} y={screenY(stages[1].height)} strength={.65} seed="bar-three-arrival"/>
   <Contact f={f} at={e.frame('nine-lock')} x={screenX(stages[2].x)} y={screenY(maxH)} strength={1.05} seed="bar-nine-arrival"/>
   {f>=e.frame('three-start')&&f<e.frame('nine-start')+4?<Text x={960} y={815} text={`${active.n}次 · 每次${active.p}%`} size={92} role="current-conditions"/>:null}
  </g>
 </Frame>;
}
