import {useEffect,useRef} from 'react';
import {useSceneContext,sampleTrail,motionCurve,type CodeSceneProps} from 'm2v/code-scene';
import {ensureMathReady} from 'm2v/code-scene/math';
import Stage from 'm2v/style/components/stage';
import LightTrail from 'm2v/style/components/light-trail';
import Burst from 'm2v/style/components/burst';
import ScreenSubtitle, {type ScreenSubtitleItem} from 'm2v/style/components/screen-subtitle';
import {T} from 'm2v/style/components/kit';
import {ease,format,ledger,mix,progress,returnPath,returnState,tokenPosition,
  type Events,type Model} from './model';
import {Text,Dot,WHITE,GOLD,MUTED,type Phases} from './visual';
import {History,Comparison} from './data-story';
import {Reason,Closing} from './finale';

type Config={model:Model;phases:Phases;screenSubtitles:ScreenSubtitleItem[]};
function Resources({value}:{value:number}){
  const units=value/10;
  return <g>{Array.from({length:Math.ceil(units-1e-8)},(_,i)=><Dot key={i} at={tokenPosition(i)}
    radius={22*Math.sqrt(Math.min(1,units-i))} role="active-resource"/>)}</g>;
}
function Opening({frame,phases}:{frame:number;phases:Phases}){
  if(frame>=phases.setup+22)return null;
  const count=Math.max(1,Math.round(mix(1,30,ease(progress(frame,0,36)))));
  const shrink=ease(progress(frame,phases.setup-18,phases.setup+22));
  const opacity=1-progress(frame,phases.setup+6,phases.setup+22);
  return <g opacity={opacity} transform={`translate(${mix(960,195,shrink)} ${mix(442,350,shrink)}) scale(${mix(1,.2,shrink)}) translate(-960 -442)`}>
    {Array.from({length:30},(_,i)=>{
      const a=-Math.PI*.98+i/29*Math.PI*1.38;
      return <line key={i} x1={960+Math.cos(a)*332} y1={442+Math.sin(a)*332}
        x2={960+Math.cos(a)*350} y2={442+Math.sin(a)*350} stroke={i<7?GOLD:MUTED}
        opacity={i<count?.7:.12} strokeWidth={4}/>;
    })}
    <Text x={910} y={437} size={380} weight={800} latin role="opening-number">{count}</Text>
    <Text x={1280} y={477} size={150} weight={700}>次</Text>
    <Text x={960} y={736} size={34} color={MUTED} latin>REPEAT OR COMPOUND</Text>
    <Dot at={{x:960+Math.cos(-Math.PI*.87)*332,y:442+Math.sin(-Math.PI*.87)*332}} radius={7} color={GOLD} glow/>
  </g>;
}
/** 单一投入簇与出口。实体资源负责数量，尾迹只负责方向。 */
function Experiment({frame,phases,events,model}:{frame:number;phases:Phases;events:Events;model:Model}){
  if(frame<phases.setup||frame>=phases.history+20)return null;
  const enter=ease(progress(frame,phases.setup,phases.setup+22));
  const returning=frame>=phases.return;
  const state=returnState(frame,events,model);
  // 实体包和光轨共用SDK的弧长采样及同一缓动，避免两种采样法产生分离的“两个头”。
  const packetHead=state.packet?sampleTrail({points:state.packet.path,progress:state.packet.travel,
    length:.15,count:12,easing:motionCurve('easeInOutSine')})[0]:null;
  const tp=progress(frame,phases.take,events['take-finish']);
  const takeRound=frame<phases.take?(frame>=events['first-output']+42?1:0):Math.min(30,Math.floor(1+tp*29));
  const take=ledger(model,takeRound,false);
  const active=returning?state.active:model.initial;
  const round=returning?state.round+Number(Boolean(state.packet)):takeRound;
  const focus=ease(progress(frame,phases.return,phases.return+22));
  const route=returnPath(tokenPosition(10));
  const path=route.map((p,i)=>`${i?'L':'M'}${p.x} ${p.y}`).join(' ');
  const takeFlight=frame>=phases.take?(frame-phases.take)/Math.max(1,(events['take-finish']-phases.take)/29)%1
    :progress(frame,events['first-output'],events['first-output']+42);
  const nextSaved={x:1380+(takeRound%5)*50,y:620+Math.floor(takeRound/5)*27};
  const exportAt={x:mix(1290,nextSaved.x,ease(takeFlight)),y:mix(452,nextSaved.y,ease(takeFlight))};
  const exporting=frame>=events['first-output']&&frame<events['take-finish']&&
    (frame<events['first-output']+42||frame>=phases.take);
  return <g opacity={enter*(1-progress(frame,phases.history,phases.history+20))}>
    <path d={path} fill="none" stroke={WHITE} strokeWidth={4.5} opacity={.13+.13*focus}/>
    {returning?<path d={path} fill="none" stroke={GOLD} strokeWidth={5} opacity={.6} pathLength={1}
      strokeDasharray={`${Math.max(.02,state.packet?ease(state.packet.travel):Number(state.round>0))} 1`}/>:null}
    <Text x={960} y={214} size={46} weight={650}>{returning?'接回产出':'取走产出'}</Text>
    <Text x={mix(1160,960,enter)} y={386} size={active%1>.01?205:280} weight={800} latin role="active-value">{format(active,active%1>.01?1:0)}</Text>
    <Text x={960} y={505} size={31} color={MUTED}>当轮投入</Text>
    <Resources value={active}/>
    {frame>=phases.take?<Text x={960} y={780} size={33} color={MUTED}>第 {round} 轮</Text>:null}
    {!returning?<>
      <line x1={1170} y1={452} x2={1290} y2={452} stroke={WHITE} strokeWidth={5} opacity={.6}/>
      {exporting?<Dot at={exportAt} color={GOLD} glow role="output-resource"/>:null}
      {frame>=events['first-output']?<Text x={1330} y={390} size={48} color={GOLD} weight={750} latin>+10</Text>:null}
      <Text x={1490} y={230} size={36} color={MUTED}>已取走</Text>
      <Text x={1490} y={305} size={90} weight={750} latin role="saved-value">{format(take.saved)}</Text>
      {Array.from({length:takeRound},(_,i)=><Dot key={i} at={{x:1380+(i%5)*50,y:620+Math.floor(i/5)*27}}
        radius={9} opacity={.72} role="saved-resource"/>)}
      {frame<phases.take?<Text x={960} y={782} size={46} color={MUTED}>每片 10 单位</Text>:null}
    </>:<>
      <g opacity={.7*focus}>
        <Text x={195} y={292} size={33} color={WHITE}>取走 · 30轮</Text>
        <Text x={195} y={354} size={68} weight={700} latin>400</Text>
        <Text x={195} y={413} size={30} color={WHITE}>100 ＋ 300 已取</Text>
      </g>
      {state.packet?<>
        <LightTrail points={state.packet.path} progress={state.packet.travel} width={12} length={.15} glow={5} dust={7}/>
        <Dot at={packetHead??state.packet.path[0]} radius={22*Math.sqrt(state.packet.value/model.unit)} color={GOLD} glow role="return-packet"/>
        <Text x={1440} y={445} size={74} weight={750} color={GOLD} latin role="output-value">+{format(state.packet.value,state.packet.value%1>.01?1:0)}</Text>
        <Text x={1440} y={511} size={25} color={MUTED}>本轮产出</Text>
      </>:<Text x={1440} y={452} size={28} color={MUTED}>产出参与下一轮</Text>}
      {['return','second','third'].map((id,i)=><Burst key={id} origin={tokenPosition(10+i)}
        progress={progress(frame,events[`${id}-merge`],events[`${id}-merge`]+34)} count={i===0?50:20}
        distance={i===0?140:80} size={4} rings={1} ringTravel={120} seed={`merge-${i}`} opacity={.8}/>)}
    </>}
    <Text x={960} y={845} size={52} color={WHITE} opacity={frame<phases.take?.65:0} role="model-note">
      示意：100起步，每轮10%，忽略损耗。
    </Text>
  </g>;
}
export default function CompoundConnect(config:CodeSceneProps){
  const {props,width,height,fps,eventFrames={}}=config;
  const {elapsedSeconds,ready}=useSceneContext();
  const notified=useRef(false);
  useEffect(()=>{if(!notified.current){notified.current=true;void ensureMathReady().then(ready);}},[ready]);
  const frame=Math.round(elapsedSeconds*fps);
  const {model,phases,screenSubtitles}=props as unknown as Config;
  return <Stage width={width} height={height} style={{fontWeight:650}}>
    <svg width={width} height={height} viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>
      <defs><radialGradient id="packet-glow"><stop offset="0" stopColor={T.light.core} stopOpacity={.95}/>
        <stop offset=".25" stopColor={GOLD} stopOpacity={.45}/><stop offset="1" stopColor={GOLD} stopOpacity={0}/>
      </radialGradient></defs>
      <Opening frame={frame} phases={phases}/>
      <Experiment frame={frame} phases={phases} events={eventFrames} model={model}/>
      <History frame={frame} phases={phases} model={model}/>
      <Comparison frame={frame} phases={phases} model={model}/>
      <Reason frame={frame} phases={phases}/>
      <Closing frame={frame} phases={phases} events={eventFrames}/>
    </svg>
    <ScreenSubtitle items={screenSubtitles} frame={frame} safeArea={config.subtitleSafeArea}
      size={60} enSize={24} risePx={0} driftPx={0} glow={.06}
      emphasis={/接回|110|121|1,745|4\.36|400/}/>
  </Stage>;
}
