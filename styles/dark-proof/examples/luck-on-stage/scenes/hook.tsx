import {sampleTrail,type CodeSceneProps} from 'm2v/code-scene';
import LightTrail from 'm2v/style/components/light-trail';
import {Attempt} from './attempt';
import {Contact,flight} from './cues';
import {Backdrop} from './details';
import {Frame,Text,WHITE,GOLD,RED,MUTED,progress,smooth,enter,useClock} from './shared';

const paths=[flight('M400 690 C690 290 1200 410 1490 710'),flight('M400 690 C690 210 1200 160 1490 340'),flight('M400 690 C720 320 1250 480 1660 530')];
export default function Hook(config:CodeSceneProps){
  const {f,e}=useClock(config),starts=[e.frame('launch'),e.frame('retry'),e.frame('last-try')],ends=[e.frame('miss-one'),e.frame('miss-two'),e.frame('hit')];
  const current=f<starts[1]?0:f<starts[2]?1:2,at=ends[current],landed=f>=at;
  const p=progress(f,starts[current],at),pos=sampleTrail({points:paths[current],progress:p,length:.2,count:16,easing:smooth})[0];
  const color=landed?(current===2?GOLD:RED):WHITE;
  const wobble=(time:number)=>f<time?0:Math.sin((f-time)*.6)*Math.exp(-(f-time)/6)*14;
  const shake=wobble(ends[0])+wobble(ends[1]);
  return <Frame config={config}>
    <style>{'.luck-hook-composite g{mix-blend-mode:normal!important}'}</style>
    <g className="luck-hook-composite">
    <Backdrop id="hook-stage"/>
    <Text x={350} y={190} text="运气" size={220} align="start" alpha={1-smooth(progress(f,40,51))} role="hook-title"/>
    <g opacity={enter(progress(f,8,20))}>
      <path d={`M1490 240 Q${1490+shake} 320 1490 390 M1490 610 Q${1490-shake} 700 1490 790`} fill="none" stroke={WHITE} strokeWidth={9} strokeLinecap="round"/>
      <path d="M1465 390H1515 M1465 610H1515" stroke={WHITE} strokeWidth={4}/>
    </g>
    {f>=starts[current]?<>
      <LightTrail points={paths[current]} progress={p} width={13} length={.2} samples={16} glow={3} dust={3} color={WHITE} opacity={1-smooth(progress(f,at,at+7))} seed={`hook-${current}`}/>
      <Attempt x={pos.x} y={pos.y} size={82} color={color} frame={f} landAt={at} groundY={pos.y} stretch={landed?1:1+.12*Math.sin(p*Math.PI)} tilt={landed?0:12*Math.sin(p*Math.PI)}/>
    </>:null}
    {landed?<Text x={current===2?1660:1170} y={current===2?710:550} text={current===2?'命中':'未中'} color={color} size={88} role="hook-result"/>:null}
    <Contact f={f} at={ends[0]} x={1490} y={710} strength={.4} seed="hook-miss-one"/>
    <Contact f={f} at={ends[1]} x={1490} y={340} strength={.4} seed="hook-miss-two"/>
    <Contact f={f} at={ends[2]} x={1660} y={530} strength={.7} seed="hook-hit"/>
    <Text x={1780} y={810} text="示意" size={23} color={MUTED}/>
    </g>
  </Frame>;
}
