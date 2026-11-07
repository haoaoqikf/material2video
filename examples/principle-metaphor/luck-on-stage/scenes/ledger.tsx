import {painter,type CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,RED,MUTED,LINE,progress,enter,track,pop,useClock} from './shared';
import {Backdrop} from './details';
import {Contact} from './cues';
import {Attempt} from './attempt';

// 非定量尝试记录，仅承接开场的两次未中/一次命中；不用于推导固定概率。
const successful=new Set([3,11,18,27]);
export default function Ledger(config:CodeSceneProps){
 const {f:clockFrame,e}=useClock(config),f=Math.round(clockFrame*1e6)/1e6;
 const lock=e.frame('count-lock');
 // 开场第三次命中直接成为记录起点，再向第4、5次和30次推进。
 const points:readonly [number,number][]=[[0,3],[24,3],[e.frame('record-four'),4],[e.frame('record-five'),5],[e.frame('accelerate'),6],[e.frame('group-ten'),10],[e.frame('group-twenty'),20],[e.frame('brake'),28],[lock,30]];
 // 数据进度采用分段线性，拒绝Hermite在停顿段的负过冲；速度由段斜率决定。
 const quantity=(at:number)=>painter.keyframeAt(points.map(([at,value])=>({at,value})),at,'linear');
 const raw=quantity(f),count=Math.min(30,Math.floor(raw+1e-7)),speed=Math.abs(quantity(f+1)-raw);
 // 高速只保留可辨组节拍，避免每个整数都让角色高频抖动。
 const beat=painter.keyframeAt([{at:0,value:0},{at:24,value:0},{at:e.frame('record-five'),value:2},{at:e.frame('accelerate'),value:3},{at:e.frame('brake'),value:7},{at:lock,value:8}],f,'linear');
 const phase=beat-Math.floor(beat),jump=f>=lock?0:Math.sin(Math.PI*phase);
 const dx=f>=lock?0:86*Math.cos(Math.PI*beat);
 const lastReturn=f>=e.frame('brake')?1-enter(progress(f,e.frame('brake'),lock)):1;
 const markerX=1440+dx*lastReturn,markerY=350-92*jump*lastReturn;
 return <Frame config={config}>
  <Backdrop id="ledger-stage"/>
  <Text x={220} y={155} text="每一次，都算数" size={124} align="start"/>
  <Text x={285} y={300} text="尝试" size={52} color={MUTED} align="start"/>
  <Text x={920} y={300} text="结果" size={52} color={MUTED} align="end"/>
  <path d="M230 345H970" stroke={LINE} strokeWidth={2}/>
  <defs><clipPath id="ledger-clip"><rect x={200} y={365} width={820} height={430}/></clipPath>
   <linearGradient id="ledger-fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".68" stopColor="white"/><stop offset="1" stopColor="black"/></linearGradient>
   <mask id="ledger-mask"><rect x={200} y={365} width={820} height={430} fill="url(#ledger-fade)"/></mask></defs>
  <g clipPath="url(#ledger-clip)" mask="url(#ledger-mask)">
   {Array.from({length:30},(_,i)=>{
    const n=i+1,y=418+(raw-n)*94;if(n>count||y<350||y>840)return null;
    const success=successful.has(n),active=n===count,color=success?GOLD:RED;
    return <g key={n}>
     {active?<rect x={225} y={y-40} width={750} height={82} fill={color} opacity={.075}/>:null}
     {[1,0].map(ghost=><g key={ghost} opacity={ghost?Math.min(.13,speed*.17):active?1:.72} transform={`translate(0 ${ghost*speed*17})`}>
      <Text x={295} y={y} text={`第 ${n} 次`} size={70} align="start" color={WHITE}/>
      <Text x={925} y={y} text={success?'✓ 命中':'× 未中'} size={68} color={color} align="end"/>
     </g>)}
     <path d={`M240 ${y+46}H965`} stroke={LINE} strokeWidth={1.5}/>
    </g>;
   })}
  </g>
  <Text x={1440} y={560} text={String(count)} size={300} numeric weight={550} scale={pop(f,lock,.045)}/>
  <Text x={1440} y={830} text="尝试次数" size={80}/>
  <Attempt x={markerX} y={markerY} size={94} color={WHITE} stretch={1+.16*jump} tilt={f>=lock?0:-8*Math.sin(Math.PI*beat)} groundY={350} frame={f} landAt={lock}/>
  <Contact f={f} at={lock} x={1440} y={350} strength={.6} kind="touch" seed="ledger-thirty"/>
  <Text x={970} y={825} text="示意" size={23} color={MUTED} align="end"/>
 </Frame>;
}
