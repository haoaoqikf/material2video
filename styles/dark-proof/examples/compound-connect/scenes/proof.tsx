import type {CodeSceneProps} from 'm2v/code-scene';
import {ChartLine,ChartMarker} from 'm2v/style/components/proof-chart';
import Burst from 'm2v/style/components/burst';
import {Frame,Text,Ball,WHITE,GOLD,MUTED,LINE,progress,arrive,smooth,mix,fixed,opacity,useClock} from './shared';
import {compounded,constant,increment,chartPoint,CHART,BAR} from './model';
// 为差值留出独立数据行，柱体仍使用同一零基准和比例。
const BAR_VIEW={bottom:BAR.bottom-70,scale:BAR.scale*.85};

function Ledger({f,exit,rowFrames}:{f:number;exit:number;rowFrames:number[]}){
  return <g opacity={1-exit} transform={`translate(${-100*exit} 0)`}>
    <Text x={960} y={145} text="新增长，留在下一轮" size={90}/>
    <Text x={960} y={245} text="理想模型：初始100，每轮按现有总量增长1%" size={46} color={MUTED} role="method"/>
    {[['轮次',340],['现有总量',920],['本轮新增',1480]].map(([s,x])=><Text key={s} x={Number(x)} y={335} text={String(s)} size={48} color={MUTED}/>)}
    <path d="M220 375H1700" stroke={MUTED} strokeWidth={2}/>
    {[0,1,2,3].map((n)=>{
      const at=n===0?0:rowFrames[n-1],a=n===0?1:arrive(progress(f,at,at+12));
      const next=n<3?rowFrames[n]:150,active=f>=at&&f<next,yy=425+n*100;
      return <g key={n} opacity={a} transform={`translate(0 ${15*(1-a)})`}>
        {n>0&&active?<rect x={225} y={yy-42} width={1470} height={86} rx={2} fill={GOLD} opacity={.055}/>:null}
        <Text x={340} y={yy} text={String(n)} size={64} numeric color={active?GOLD:WHITE}/>
        <Text x={920} y={yy} text={n===3&&f>=150?'':fixed(compounded(n))} size={70} numeric color={active?GOLD:WHITE}/>
        <Text x={1480} y={yy} text={n===0?'—':`+${fixed(increment(n))}`} size={66} numeric color={active?GOLD:WHITE}/>
        <path d={`M220 ${yy+48}H1700`} stroke={LINE} strokeWidth={1.5}/>
      </g>;
    })}
    {[1,2].map(n=>{
      const p=progress(f,rowFrames[n]-18,rowFrames[n]+6),visible=f>=rowFrames[n]-18&&f<rowFrames[n]+18;
      if(!visible)return null;
      return <g key={n}><path d={`M1000 ${425+n*100} Q1500 ${375+n*100} 1470 ${425+(n+1)*100}`} stroke={GOLD} strokeWidth={2} fill="none" opacity={.35}/>
        <Ball x={mix(1000,1470,smooth(p))} y={mix(425+n*100,425+(n+1)*100,smooth(p))-Math.sin(Math.PI*p)*50} r={8}/></g>;
    })}
  </g>;
}

function Curve({f,start,run,complete,leave}:{f:number;start:number;run:number;complete:number;leave:number}){
  if(f<start)return null;
  const a=arrive(progress(f,start,start+14))*(1-smooth(progress(f,leave,leave+14)));
  // 匀速推进的是轮次数，路径形状始终由同一模型决定。
  const n=3+97*progress(f,run,complete),whole=Math.floor(n);
  const points=(formula:(n:number)=>number)=>[...Array.from({length:whole+1},(_,i)=>chartPoint(i,formula(i))),...(n>whole?[chartPoint(n,formula(n))]:[])];
  const [gx,gy]=chartPoint(n,compounded(n)),[wx,wy]=chartPoint(n,constant(n));
  return <g opacity={a}>
    <Text x={960} y={145} text="开始很像，后来拉开" size={90}/>
    <path d="M345 257H405" stroke={WHITE} strokeWidth={5}/><Text x={435} y={257} text="固定加1" align="start" size={44}/>
    <path d="M930 257H990" stroke={GOLD} strokeWidth={5}/><Text x={1020} y={257} text="按现有总量加1%" align="start" size={44} color={GOLD}/>
    {[100,200,300].map(v=>{const y=chartPoint(0,v)[1];return <g key={v}><path d={`M${CHART.left} ${y}H${CHART.right}`} stroke={LINE} strokeWidth={1.4}/><Text x={195} y={y} text={String(v)} size={40} numeric color={MUTED} align="end"/></g>;})}
    <path d={`M${CHART.left} ${CHART.top}V${CHART.bottom}H${CHART.right}`} stroke={MUTED} strokeWidth={2.5} fill="none"/>
    {[0,50,100].map(k=><Text key={k} x={chartPoint(k,100)[0]} y={842} text={String(k)} size={40} numeric color={MUTED}/>)}
    <Text x={1550} y={842} text="轮" size={38} color={MUTED}/>
    <ChartLine points={points(constant)} color={WHITE} width={5}/><ChartLine points={points(compounded)} color={GOLD} width={6}/>
    <ChartMarker x={wx} y={wy} color={WHITE} radius={7}/><Ball x={gx} y={gy} r={12}/>
    <Text x={gx+45} y={gy-30} text={fixed(compounded(n))} size={60} numeric color={GOLD} align="start" role="compound-value"/>
    {n>=32?<Text x={wx+45} y={wy+40} text={fixed(constant(n))} size={54} numeric align="start"/>:null}
  </g>;
}

function Bars({f,start,hits,end}:{f:number;start:number;hits:number[];end:number}){
  if(f<start)return null;
  const enter=arrive(progress(f,start,start+14)),exit=smooth(progress(f,end-18,end-10));
  return <g opacity={enter*(1-exit)}>
    <Text x={960} y={145} text="差距，正在被放大" size={90}/>
    <Text x={660} y={255} text="固定加1" size={44}/><Text x={1240} y={255} text="按现有总量加1%" size={44} color={GOLD}/>
    <path d={`M220 ${BAR_VIEW.bottom}H1700`} stroke={MUTED} strokeWidth={2}/>
    {BAR.rounds.map((n,i)=>{
      const p=arrive(progress(f,hits[i]-18,hits[i]+12)),cx=BAR.centers[i];
      return <g key={n}>{[-1,1].map(dir=>{
        const value=dir===1?compounded(n):constant(n),h=value*BAR_VIEW.scale*p,x=cx+dir*95,color=dir===1?GOLD:WHITE;
        return <g key={dir}><rect x={x-44} y={BAR_VIEW.bottom-h} width={88} height={h} fill={color}/>
          {p>.08?<Text x={x} y={BAR_VIEW.bottom-h-38} text={fixed(value*p)} size={45} numeric color={color} role={`bar-label-${i}-${dir}`}/>:null}</g>;
      })}<Text x={n===100&&f>end-18?1507:cx} y={776} text={n===100&&f>end-18?'轮':`${n}轮`} size={44} role={`round-label-${i}`}/>
        {f>=hits[i]+18?<Text x={cx} y={847} text={`差 ${fixed(compounded(n)-constant(n))}`} size={44} color={GOLD} role={`bar-gap-${i}`} alpha={opacity(f,hits[i]+18,end-18)}/>:null}
      </g>;
    })}
  </g>;
}

export default function Proof(config:CodeSceneProps){
  const {f,e}=useClock(config),cs=e.frame('curve-start'),bs=e.frame('bars-start');
  const hits=[e.frame('bar-10'),e.frame('bar-50'),e.frame('bar-100')];
  const flight=progress(f,cs-30,cs+15),[fromX,fromY]=chartPoint(100,compounded(100));
  const drop=progress(f,bs-18,hits[0]+12),firstTop=BAR_VIEW.bottom-compounded(10)*BAR_VIEW.scale;
  const exit=progress(f,config.durationInFrames-18,config.durationInFrames);
  return <Frame config={config} impacts={[
    {id:'curve-result',preset:'reveal',origin:{x:fromX,y:fromY},startFrame:e.frame('curve-flash')},
    {id:'bar-final',preset:'formula',origin:{x:1565,y:BAR_VIEW.bottom-compounded(100)*BAR_VIEW.scale},startFrame:e.frame('bar-flash')},
  ]}>
    {f<cs+2?<Ledger f={f} exit={smooth(progress(f,cs-14,cs+2))} rowFrames={[e.frame('row-1'),e.frame('row-2'),e.frame('row-3')]}/>:null}
    {f>=cs-30&&f<cs+15?<g opacity={1-Math.max(0,flight-.8)*5}>
      <Text x={mix(920,chartPoint(3,compounded(3))[0],smooth(flight))} y={mix(725,chartPoint(3,compounded(3))[1],smooth(flight))+Math.sin(Math.PI*flight)*100} text="103.03" size={mix(70,24,flight)} numeric color={GOLD}/>
      <Ball x={mix(920,chartPoint(3,compounded(3))[0],smooth(flight))} y={mix(725,chartPoint(3,compounded(3))[1],smooth(flight))} r={mix(4,12,flight)}/>
    </g>:null}
    <Curve f={f} start={cs} run={e.frame('curve-run')} complete={e.frame('curve-result')} leave={bs-8}/>
    <Bars f={f} start={bs} hits={hits} end={config.durationInFrames}/>
    {f>=bs-18&&f<hits[0]+13?<Ball x={mix(fromX,545,smooth(drop))} y={mix(fromY,firstTop,smooth(drop))-Math.sin(Math.PI*drop)*160} r={12}/>:null}
    {hits.map((at,i)=><Burst key={i} origin={{x:BAR.centers[i]+95,y:BAR_VIEW.bottom-compounded(BAR.rounds[i])*BAR_VIEW.scale}} progress={progress(f,at+12,at+35)} count={24} distance={100} rings={0} size={3} seed={`bar-${i}`}/>)}
    {exit>0?<Text x={mix(1450,1500,smooth(exit))} y={mix(776,350,smooth(exit))} text="100" size={mix(44,72,exit)} numeric color={GOLD}/>:null}
  </Frame>;
}
