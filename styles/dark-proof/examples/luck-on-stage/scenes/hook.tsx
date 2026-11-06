import {sampleTrail,type CodeSceneProps} from 'm2v/code-scene';
import {Attempt} from './attempt';
import {AccentRelease,Contact,FlightMotes,flight,type LightSample} from './cues';
import {Backdrop} from './details';
import {Frame,Text,WHITE,GOLD,RED,MUTED,progress,smooth,enter,useClock} from './shared';

const paths=[flight('M400 690 C690 290 1200 410 1490 710'),flight('M400 690 C690 210 1200 160 1490 340'),flight('M400 690 C720 320 1250 480 1660 530')];
export default function Hook(config:CodeSceneProps){
  const {f,e}=useClock(config),starts=[e.frame('launch'),e.frame('retry'),e.frame('last-try')],ends=[e.frame('miss-one'),e.frame('miss-two'),e.frame('hit')];
  const current=f<starts[1]?0:f<starts[2]?1:2,at=ends[current],landed=f>=at;
  const p=progress(f,starts[current],at);
  const age=Math.max(0,f-at),fall=Math.min(10,age),success=current===2;
  // 球体与每颗光滴都查询同一个任意帧位置，触碰后保留惯性并自然下落。
  const atFrame=(time:number)=>{
    const phase=progress(time,starts[current],at),point=sampleTrail({points:paths[current],progress:phase,length:.2,count:2,easing:smooth})[0];
    const post=Math.max(0,time-at),drop=Math.min(10,post),stretch=time>=at?1:1+.07*Math.sin(phase*Math.PI);
    const x=point.x+(success?24:-18)*enter(progress(post,0,10)),y=point.y+.52*drop*drop;
    return {x,y,centerY:y-41*stretch,stretch};
  };
  const body=atFrame(f),{x,y}=body;
  const samples:LightSample[]=Array.from({length:13},(_,i)=>f-i).filter(time=>time>=starts[current]).map(time=>{
    const position=atFrame(time);
    return {x:position.x,y:position.centerY,color:GOLD};
  });
  const alpha=landed&&!success?1-smooth(progress(age,4,12)):1;
  const light=landed?1-smooth(progress(age,0,8)):Math.min(1,Math.sin(Math.PI*p)*1.35);
  const color=landed?(current===2?GOLD:RED):WHITE;
  const wobble=(time:number)=>f<time?0:Math.sin((f-time)*.6)*Math.exp(-(f-time)/6)*14;
  const shake=wobble(ends[0])+wobble(ends[1]);
  return <Frame config={config} subtitleVariants={{18:{enter:'wipe',enterFrames:8,exitFrames:6},90:{enter:'wipe',enterFrames:8,exitFrames:6}}} overlay={<AccentRelease f={f} at={e.frame('hit-land')} x={1684} y={541} id="hook-hit-flash" scale={.9}/> }>
    <style>{'.luck-hook-composite g{mix-blend-mode:normal!important}'}</style>
    <g className="luck-hook-composite">
    <Backdrop id="hook-stage"/>
    <Text x={350} y={190} text="运气" size={220} align="start" alpha={1-smooth(progress(f,40,51))} role="hook-title"/>
    <g opacity={enter(progress(f,8,20))}>
      <path d={`M1490 240 Q${1490+shake} 320 1490 390 M1490 610 Q${1490-shake} 700 1490 790`} fill="none" stroke={WHITE} strokeWidth={9} strokeLinecap="round"/>
      <path d="M1465 390H1515 M1465 610H1515" stroke={WHITE} strokeWidth={4}/>
    </g>
    {f>=starts[current]?<>
      <FlightMotes samples={samples} energy={light}/>
      <Attempt x={x} y={y} size={82} color={color} alpha={alpha} glow={.22+.3*light} frame={f} landAt={success?e.frame('hit-land'):undefined} stretch={body.stretch} tilt={landed?0:8*Math.sin(p*Math.PI)}/>
    </>:null}
    {landed?<Text x={current===2?1660:1170} y={current===2?710:550} text={current===2?'命中':'未中'} color={color} size={88} role="hook-result"/>:null}
    <Contact f={f} at={ends[0]} x={1490} y={680} strength={.6} kind="touch" color={RED} seed="hook-miss-one"/>
    <Contact f={f} at={ends[1]} x={1490} y={310} strength={.6} kind="touch" color={RED} seed="hook-miss-two"/>
    <Contact f={f} at={e.frame('hit-land')} x={1684} y={541} strength={1.25} seed="hook-hit"/>
    <Text x={1780} y={810} text="示意" size={23} color={MUTED}/>
    </g>
  </Frame>;
}
