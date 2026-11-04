import {ChartLine} from 'm2v/style/components/proof-chart';
import {ease,format,ledger,mix,progress,type Model} from './model';
import {Text,Dot,WHITE,GOLD,MUTED,type Phases} from './visual';

/** 同一线性轴；曲线来自整数轮账本，轮间只做可视插值，不改写轮次真值。 */
export function History({frame,phases,model}:{frame:number;phases:Phases;model:Model}){
  if(frame<phases.history||frame>=phases.compare)return null;
  const at=frame-phases.history;
  const beats=[[0,0],[36,0],[114,3],[165,10],[225,20],[288,30]];
  let n=30;
  for(let i=1;i<beats.length;i++){
    if(at<=beats[i][0]){
      const [a,x]=beats[i-1],[b,y]=beats[i];n=mix(x,y,ease(progress(at,a,b)));break;
    }
  }
  const integer=Math.floor(n),fraction=n-integer;
  const total=(reinvest:boolean)=>mix(ledger(model,integer,reinvest).total,
    ledger(model,Math.min(30,integer+1),reinvest).total,fraction);
  const x=(round:number)=>340+round*36;
  const y=(value:number)=>760-value/1800*500;
  const points=(reinvest:boolean):[number,number][]=>Array.from({length:31},(_,i)=>[x(i),y(ledger(model,i,reinvest).total)]);
  const enter=ease(progress(at,12,36));
  return <g opacity={enter}>
    <defs><clipPath id="history-clip"><rect x={330} y={225} width={x(n)-330+1} height={550}/></clipPath></defs>
    <Text x={960} y={143} size={48} weight={700}>同样起点 · 同样30轮</Text>
    <Text x={960} y={215} size={42} color={MUTED}>
      {fraction>.001&&fraction<.999?`第 ${integer} → ${integer+1} 轮`:`第 ${Math.round(n)} 轮`}
    </Text>
    {[0,600,1200,1800].map(v=><g key={v}>
      <line x1={340} y1={y(v)} x2={1420} y2={y(v)} stroke={WHITE} opacity={v===0?.35:.09} strokeWidth={2}/>
      <Text x={294} y={y(v)} size={40} color={MUTED} latin align="end">{format(v)}</Text>
    </g>)}
    {[0,10,20,30].map(i=><Text key={i} x={x(i)} y={813} size={42} color={MUTED} latin>{i}</Text>)}
    <Text x={230} y={192} size={32} color={MUTED}>总量</Text>
    <Text x={1462} y={813} size={32} color={MUTED}>轮</Text>
    <g clipPath="url(#history-clip)">
      <ChartLine points={points(false)} color={WHITE} width={6}/>
      <ChartLine points={points(true)} color={GOLD} width={7}/>
    </g>
    <Dot at={{x:x(n),y:y(total(false))}} radius={9}/>
    <Dot at={{x:x(n),y:y(total(true))}} radius={12} color={GOLD} glow/>
    <Text x={1640} y={295} size={44} weight={700} color={GOLD}>接回</Text>
    <Text x={1640} y={385} size={100} weight={800} latin color={GOLD} role="history-return">{format(total(true))}</Text>
    <Text x={1640} y={565} size={44} weight={700}>取走</Text>
    <Text x={1640} y={650} size={100} weight={800} latin role="history-take">{format(total(false))}</Text>
    {at<100?<Text x={435} y={687} size={44} weight={650} latin>100</Text>:null}
  </g>;
}

export function Comparison({frame,phases,model}:{frame:number;phases:Phases;model:Model}){
  if(frame<phases.compare||frame>=phases.reason)return null;
  const a=ledger(model,30,false).total,b=ledger(model,30,true).total;
  const ratio=ease(progress(frame,phases.compare+120,phases.compare+147));
  const leave=1-ease(progress(frame,phases.reason-18,phases.reason));
  return <g opacity={leave}>
    <Text x={960} y={179} size={48} color={MUTED}>第30轮 · 总量</Text>
    <Text x={470} y={310} size={55} weight={700}>取走</Text>
    <Text x={1265} y={310} size={55} color={GOLD} weight={700}>接回</Text>
    <Text x={470} y={476} size={205} weight={800} latin role="compare-take">{format(a)}</Text>
    <Text x={1265} y={476} size={265} weight={800} latin color={GOLD} role="compare-return">{format(b)}</Text>
    <Text x={470} y={668} size={43} color={MUTED}>100 投入 ＋ 300 已取</Text>
    <Text x={1265} y={668} size={43} color={MUTED}>全部参与下一轮</Text>
    <g opacity={ratio} transform={`translate(960 766) scale(${mix(.92,1,ratio)}) translate(-960 -766)`}>
      <Text x={960} y={766} size={100} color={GOLD} weight={750} latin>{format(b/a,2)}×</Text>
    </g>
  </g>;
}
