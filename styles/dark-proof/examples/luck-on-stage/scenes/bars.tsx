import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,MUTED,LINE,progress,enter,smooth,mix,mixHex,pop,useClock} from './shared';
import {Backdrop} from './details';
import {AccentRelease,Contact,FlightMotes,type LightSample} from './cues';
import {Attempt} from './attempt';

const CASES=[{n:10,p:10,result:1},{n:30,p:10,result:3},{n:30,p:30,result:9}];
const BALL_COLORS=[WHITE,'#DCC78C',GOLD] as const;
const BAR_BASE=650,GROUND=750,MAX_HEIGHT=414;

export default function Bars(config:CodeSceneProps){
 const {f,e}=useClock(config);
 const stages=CASES.map((c,i)=>{
  const id=['one','three','nine'][i];
  const start=e.frame(`${id}-start`),land=i===0?start:e.frame(`${id}-land`),lock=e.frame(`${id}-lock`);
  return {...c,x:450+i*490,start,land,lock,height:c.result/9*MAX_HEIGHT*enter(progress(f,land,lock))};
 });
 const current=f<stages[1].start?0:f<stages[2].start?1:2;
 const active=stages[current],previous=stages[Math.max(0,current-1)];
 const settled=f<stages[2].land?stages[1]:stages[2];
 // 两次拉远均在球停稳时完成；飞行窗口中的相机投影保持不变。
 const secondView=smooth(progress(f,44,58));
 const finalView=smooth(progress(f,106,119));
 const zoom=mix(mix(3.2,1.25,secondView),1,finalView);
 const center=mix(mix(stages[0].x,720,secondView),960,finalView);
 const screenX=(x:number)=>960+(x-center)*zoom;
 const screenY=(height:number)=>BAR_BASE-height*zoom;
 const bodyAt=(time:number)=>{
  if(current===0){
   const prep=progress(time,stages[1].start-5,stages[1].start);
   return {x:screenX(stages[0].x),y:GROUND,stretch:1-.12*Math.sin(Math.PI*prep/2)};
  }
  const q=progress(time,active.start,active.land);
  const worldX=mix(previous.x,active.x,q);
  const lift=4*(current===1?178:158)*q*(1-q);
  const next=current===1?stages[2]:undefined;
  const anticipation=next&&time>=active.land?1-.12*Math.sin(Math.PI*progress(time,next.start-5,next.start)/2):1;
  const flightStretch=1+.07*Math.sin(Math.PI*q)-.12*(1-smooth(progress(q,0,.12)));
  return {x:screenX(worldX),y:GROUND-lift,stretch:time<active.start?anticipation:time<active.land?flightStretch:1};
 };
 const colorAt=(time:number)=>current===0?BALL_COLORS[0]:mixHex(BALL_COLORS[current-1],BALL_COLORS[current],enter(progress(time,active.start+2,active.land-2)));
 const ball=bodyAt(f),ballColor=colorAt(f);
 const samples:LightSample[]=current===0?[]:Array.from({length:13},(_,i)=>f-i)
  .filter(time=>time>=active.start).map(time=>{
   const position=bodyAt(time);
   return {x:position.x,y:position.y-38*position.stretch,color:colorAt(time)};
  });
 const trailEnergy=current===0||f>=active.land+8?0:f<active.land?enter(progress(f,active.start,active.start+4)):1-smooth(progress(f,active.land,active.land+8));
 const labels=enter(progress(f,e.frame('nine-lock')+2,e.frame('nine-lock')+16));
 return <Frame config={config} subtitleVariants={{10:{enter:'wipe',enterFrames:8,exitFrames:6}}} overlay={<>
  <AccentRelease f={f} at={e.frame('three-land')-1} x={screenX(stages[1].x)} y={GROUND-38} id="bar-three-flash" scale={.55}/>
  <AccentRelease f={f} at={e.frame('nine-land')-1} x={screenX(stages[2].x)} y={GROUND-38} id="bar-nine-flash" scale={.78}/>
 </>}>
  <Backdrop id="bars-stage"/>
  <Text x={960} y={130} text="预期成功次数" size={116} role="bars-title"/>
  <g>
   <path d={`M220 ${BAR_BASE}H1690`} stroke={LINE} strokeWidth={3}/>
   <path d={`M220 ${GROUND}H1690`} stroke={LINE} strokeWidth={2} opacity={.45}/>
   {stages.map((s,i)=>{
    if(f<s.land)return null;
    const visible=Math.max(.35,enter(progress(f,s.land,s.land+8)));
    const resultColor=BALL_COLORS[i];
    return <g key={i} opacity={visible}>
     <rect x={screenX(s.x)-91*zoom} y={screenY(s.height)} width={182*zoom} height={s.height*zoom} fill={resultColor} opacity={i===current?1:.7}/>
     <path d={`M${screenX(s.x)-91*zoom} ${screenY(s.height)}H${screenX(s.x)+91*zoom}`} stroke={resultColor} strokeWidth={4}/>
     <path d={`M${screenX(s.x)} ${GROUND-5}V${BAR_BASE}`} stroke={resultColor} strokeWidth={3} opacity={Math.max(0,1-progress(f,s.land,s.land+14))*.75}/>
     {f>=s.land?<Text x={screenX(s.x)+91*zoom+65} y={screenY(s.height)+16} text={String(s.result)} size={i===current?154:110} numeric weight={550} color={resultColor} scale={pop(f,s.land,.04)} role={`bar-result-${i}`}/>:null}
     {labels>0?<>
      <Text x={s.x} y={830} text={`${s.n}次 · ${s.p}%`} size={70} color={i===2?GOLD:i===1?BALL_COLORS[1]:MUTED} alpha={labels} role={`bar-condition-${i}`}/>
     </>:null}
    </g>;
   })}
   <FlightMotes samples={samples} energy={trailEnergy}/>
   {f>=stages[0].start?<Attempt x={ball.x} y={ball.y} size={76} color={ballColor} stretch={ball.stretch} groundY={GROUND} frame={f} landAt={current===0?undefined:active.land-1} glow={.2+.3*trailEnergy}/>:null}
   <Contact f={f} at={e.frame('three-land')-1} x={screenX(stages[1].x)} y={GROUND-38} strength={.48} seed="bar-three-arrival"/>
   <Contact f={f} at={e.frame('nine-land')-1} x={screenX(stages[2].x)} y={GROUND-38} strength={.65} seed="bar-nine-arrival"/>
   {f>=e.frame('three-land')&&f<e.frame('nine-land')+4?<Text x={960} y={810} text={`${settled.n}次 · 每次${settled.p}%`} size={70} role="current-conditions"/>:null}
  </g>
 </Frame>;
}
