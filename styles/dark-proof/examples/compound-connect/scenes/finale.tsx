import {sampleTrail,motionCurve} from 'm2v/code-scene';
import {MathFormula} from 'm2v/code-scene/math';
import LightTrail from 'm2v/style/components/light-trail';
import Burst from 'm2v/style/components/burst';
import {ease,mix,progress,returnPath,tokenPosition,type Events} from './model';
import {Text,Dot,WHITE,GOLD,MUTED,type Phases} from './visual';

export function Reason({frame,phases}:{frame:number;phases:Phases}){
  if(frame<phases.reason-18||frame>=phases.close)return null;
  const second=ease(progress(frame,phases.reason+112,phases.reason+138));
  const enter=ease(progress(frame,phases.reason-18,phases.reason+12));
  const textEnter=ease(progress(frame,phases.reason-2,phases.reason+16));
  const leave=1-ease(progress(frame,phases.close-18,phases.close));
  const q=progress(frame,phases.reason+25,phases.reason+105);
  const r=progress(frame,phases.reason+135,phases.reason+215);
  const loop=returnPath(tokenPosition(10));
  const p=sampleTrail({points:loop,progress:r,length:.15,count:12,easing:motionCurve('easeInOutSine')})[0];
  return <g opacity={enter*leave}>
    <g opacity={textEnter}>
    <Text x={960} y={92} size={44} color={MUTED}>第 n 轮的总量</Text>
    <Text x={370} y={217} size={52} weight={700}>取走</Text>
    <foreignObject x={580} y={142} width={1020} height={200}>
      <div style={{textAlign:'center',color:WHITE}}><MathFormula tex={'100+10n'} fontSize={110} role="withdraw-formula"/></div>
    </foreignObject>
    </g>
    <line x1={350} y1={380} x2={1550} y2={380} stroke={WHITE} strokeWidth={5} opacity={.4}/>
    <Dot at={{x:mix(500,1550,ease(q)),y:380}} radius={18} color={WHITE} opacity={q<1?1:.2}/>
    <Text x={350} y={447} size={36} color={MUTED}>起点不变</Text>
    <g opacity={second}>
      <Text x={370} y={595} size={52} color={GOLD} weight={700}>接回</Text>
      <foreignObject x={580} y={517} width={1020} height={200}>
        <div style={{textAlign:'center',color:GOLD}}><MathFormula tex={'100\\times1.1^{n}'} fontSize={110} role="reinvest-formula"/></div>
      </foreignObject>
      <g transform="translate(-158 500) scale(.58 .4)">
        <path d={loop.map((x,i)=>`${i?'L':'M'}${x.x} ${x.y}`).join(' ')} fill="none" stroke={GOLD} strokeWidth={7} opacity={.55}/>
        <LightTrail points={loop} progress={r} width={12} length={.15} glow={4} dust={4}/>
      </g>
      <Dot at={{x:-158+p.x*.58,y:500+p.y*.4}} radius={18} color={GOLD} glow/>
      <Text x={1090} y={742} size={36} color={GOLD}>带着上一次</Text>
    </g>
  </g>;
}

/** 回到第一次产出并入的位置，片名在动作之后出现。 */
export function Closing({frame,phases,events}:{frame:number;phases:Phases;events:Events}){
  if(frame<phases.close)return null;
  const p=progress(frame,phases.close+6,events['title-arrive']);
  const title=ease(progress(frame,events['title-arrive']-8,events['title-arrive']+22));
  const path=returnPath(tokenPosition(10));
  const head=sampleTrail({points:path,progress:p,length:.15,count:12,easing:motionCurve('easeInOutSine')})[0];
  return <g>
    <path d={path.map((x,i)=>`${i?'L':'M'}${x.x} ${x.y}`).join(' ')} fill="none" stroke={GOLD} strokeWidth={5}
      pathLength={1} strokeDasharray={`${ease(p)} 1`} opacity={.6}/>
    <LightTrail points={path} progress={p} width={15} length={.13} glow={6} dust={8}/>
    <Dot at={head} radius={22} color={GOLD} glow/>
    <Burst origin={tokenPosition(10)} progress={progress(frame,events['title-arrive'],events['title-arrive']+44)}
      count={60} distance={160} size={4} rings={1} ringTravel={160} seed="closing-merge"/>
    <g opacity={title} transform={`translate(960 421) scale(${mix(.94,1,title)}) translate(-960 -421)`}>
      <Text x={960} y={421} size={310} weight={800} role="title">接</Text>
      <Text x={960} y={805} size={29} color={MUTED} latin>OUTPUT BECOMES INPUT</Text>
    </g>
  </g>;
}
