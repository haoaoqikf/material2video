/**
 * 拥堵波五幕：同一份离线轨迹，按真实旁白时间窗推进。
 *
 * 车辆位置、灯态与图表都从 `traffic.ts` 采样，视觉时钟来自录制帧；旁白段只决定
 * 段落与提示出现的时机，不手工改写运动。分幕由 `props.mode` 选择，画面共用同一套
 * 道路、环路与车辆零件，避免每幕换一套视觉语言。
 */
import {useLayoutEffect, useRef, type ReactNode} from 'react';
import {Chart, gsap, type CodeSceneProps} from 'm2v/code-scene';
import {sample, slowCenter, wrapDelta, speedRatio, gapToAhead, gapUnits, TRAFFIC, type CarState, type GroupName} from './traffic';
import {useNarration, useReady} from './stage';

const C = {bg: '#080f19', road: '#182431', edge: '#344555', white: '#f4f3ee', dim: '#99aabb', red: '#ff704b', blue: '#67e2ec'};
const clamp = (x: number) => Math.max(0, Math.min(1, x));
const ease = (x: number) => {const t = clamp(x); return t*t*(3-2*t);};

function Car({car, x, y, scale = 1.6, focus = false, angle = 0}: {car: CarState; x: number; y: number; scale?: number; focus?: boolean; angle?: number}) {
  return <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`}>
    {focus && <rect x={-33} y={-23} width={66} height={46} rx={14} fill="none" stroke={C.blue} strokeWidth={2}/>}
    <ellipse cx={-2} cy={7} rx={29} ry={13} fill="#000" opacity={0.5}/>
    <rect x={-25} y={-13} width={50} height={26} rx={8} fill={focus ? C.blue : '#c6d2db'}/>
    <rect x={-9} y={-10} width={24} height={20} rx={5} fill="#526677"/>
    <path d="M 8 -10 L 14 -8 L 14 8 L 8 10 Z" fill="#b6d8e2"/>
    <rect x={-26} y={-11} width={4} height={22} rx={2} fill={car.brake ? C.red : '#663c3a'}/>
    {car.brake && <rect x={-33} y={-16} width={15} height={32} rx={7} fill={C.red} opacity={0.28} filter="url(#glow)"/>}
    <path d="M 22 -9 L 28 -9 M 22 9 L 28 9" stroke={C.white} strokeWidth={3}/>
    <text x={-14} y={4} fontSize={9} fontWeight={700} fill="#0e1a24">{car.id}</text>
  </g>;
}

function Label({y, children, color=C.white, size=46, opacity=1}: {y:number; children:ReactNode; color?:string; size?:number; opacity?:number}) {
  return <div style={{position:'absolute',left:76,right:76,top:y,fontSize:size,fontWeight:650,lineHeight:1.25,color,opacity}}>{children}</div>;
}

function Road({seconds, y, group='high', camera, zoom=1, focus=7}: {seconds:number; y:number; group?:GroupName; camera?:number; zoom?:number; focus?:number}) {
  const cars = sample(group, seconds);
  const ref = camera ?? (slowCenter(cars) ?? cars[0].s);
  const slow = cars.filter(c=>speedRatio(c.speed)<TRAFFIC.thresholds.slowRatio);
  return <g>
    <rect x={-20} y={y-92} width={1120} height={184} fill={C.road}/>
    <path d={`M0 ${y-92}H1080 M0 ${y+92}H1080`} stroke={C.edge} strokeWidth={2}/>
    {Array.from({length:18},(_,i)=>{const x=((i*90-ref*zoom)%1620+1620)%1620-270;return <path key={i} d={`M${x} ${y}h38`} stroke="#69808e" strokeWidth={3} opacity={0.35}/>;})}
    {slow.map(c=><rect key={c.id} x={540+wrapDelta(c.s,ref)*zoom-74} y={y-79} width={148} height={158} rx={50} fill={C.red} opacity={0.12}/>)}
    {cars.map(car=>{const x=540+wrapDelta(car.s,ref)*zoom;return Math.abs(x-540)<650?<Car key={car.id} car={car} x={x} y={y} focus={car.id===focus}/>:null;})}
  </g>;
}

function Ring({seconds, scale=1, y=890, focus=7}: {seconds:number; scale?:number; y?:number; focus?:number}) {
  const cars=sample('high',seconds);
  return <g transform={`translate(540 ${y}) scale(${scale})`}>
    <ellipse rx={TRAFFIC.loop.rx} ry={TRAFFIC.loop.ry} fill="none" stroke={C.edge} strokeWidth={104}/>
    <ellipse rx={TRAFFIC.loop.rx} ry={TRAFFIC.loop.ry} fill="none" stroke={C.road} strokeWidth={100}/>
    <ellipse rx={TRAFFIC.loop.rx} ry={TRAFFIC.loop.ry} fill="none" stroke="#69808e" strokeWidth={2} strokeDasharray="20 32" opacity={0.45}/>
    {cars.filter(c=>speedRatio(c.speed)<TRAFFIC.thresholds.slowRatio).map(c=><circle key={c.id} cx={c.x} cy={c.y} r={72} fill={C.red} opacity={0.17}/>)}
    {cars.map(car=><Car key={car.id} car={car} x={car.x} y={car.y} angle={car.heading*180/Math.PI} scale={1.4} focus={car.id===focus}/>)}
  </g>;
}

const curve = (group:GroupName, upto:number):[number,number][] => Array.from({length:Math.floor(clamp(upto)*160)+1},(_,i)=>[i/10,Math.round(speedRatio(sample(group,7+i/10)[5].speed)*100)]);

export default function Film(props:CodeSceneProps) {
  useReady();
  const clock = useNarration(props);
  const t = clock.elapsedSeconds;
  // 不同幕的旁白段不同；公共计算只读存在的段，避免跨幕取进度时报错。
  const at = (id: string) => (props.segmentWindows[id] ? clock.progress(id) : 0);
  // 文案在段首快速淡入，避免长时间停在低对比度状态。
  const revealOf = (id: string, speed = 6) => Math.min(1, at(id) * speed);
  const mode=String(props.props.mode ?? 'hook');
  const draft=Boolean(props.props.draft);
  const hookTime=10+t*.65;
  // hook 固定道路参照下可同时看见车辆右行和低速区域左移。
  const anchor=slowCenter(sample('high',10)) ?? 0;
  const time=mode==='origin'?5+clock.progress('o1')*8:mode==='relay'?11+t*.65:13+t*.55;
  const reveal=ease((t-1.8)/1.5);
  // 红色反向箭头由帧时间驱动 GSAP 补间；不使用挂钟，重复录制逐帧一致。
  const arrow=useRef<SVGGElement>(null);
  useLayoutEffect(()=>{
    if(!arrow.current) return;
    gsap.set(arrow.current,{opacity:clamp(reveal),x:24*(1-clamp(reveal))});
  },[reveal]);
  const chart={animation:false,backgroundColor:'transparent',grid:{left:60,right:36,top:44,bottom:52},
    textStyle:{color:C.dim,fontSize:24,fontFamily:'Noto Sans SC'},
    xAxis:{type:'value',min:0,max:16,axisLabel:{color:C.dim,fontSize:22},splitLine:{show:false}},
    yAxis:{type:'value',min:0,max:100,axisLabel:{color:C.dim,fontSize:22,formatter:'{value}%'},splitLine:{lineStyle:{color:'#263543'}}},
    series:[{type:'line',data:curve('high',at('d1')),showSymbol:false,lineStyle:{color:C.red,width:5}},
      {type:'line',data:curve('low',at('d1')),showSymbol:false,lineStyle:{color:C.blue,width:5}}]};
  return <div style={{width:props.width,height:props.height,position:'relative',overflow:'hidden',background:C.bg,color:C.white}}>
    {!draft&&<div style={{position:'absolute',inset:0,background:'radial-gradient(ellipse at 70% 42%, #223342 0%, transparent 65%)',opacity:.55}}/>}
    <div style={{position:'absolute',left:76,top:82,fontSize:24,letterSpacing:5,color:C.dim}}>车流实验 · 机制示意</div>
    <svg width={1080} height={1570} style={{position:'absolute',inset:0}}>
      <defs><filter id="glow"><feGaussianBlur stdDeviation="5"/></filter><linearGradient id="fade"><stop stopColor={C.red} stopOpacity="0"/><stop offset="1" stopColor={C.red} stopOpacity=".8"/></linearGradient></defs>
      {mode==='hook'&&<>
        <Road seconds={hookTime} y={780} camera={anchor} zoom={.85}/>
        <path d="M150 1050H925 m-30 -15l30 15 -30 15" fill="none" stroke={C.blue} strokeWidth={5}/>
        <g ref={arrow}><path d="M925 1180H150 m30 -15l-30 15 30 15" fill="none" stroke={C.red} strokeWidth={7}/></g>
      </>}
      {mode==='origin'&&<>
        <Ring seconds={time} scale={.48} y={600} focus={1}/>
        <Road seconds={time} y={1200} camera={sample('high',time)[1].s} zoom={1.25} focus={1}/>
        <text x={76} y={1340} fontSize={28} fill={C.dim}>
          1 号车与后车：{gapUnits(gapToAhead(sample('high',time),1)).toFixed(1)} 车位
        </text>
      </>}
      {mode==='relay'&&<Ring seconds={time} scale={.98}/>}
      {mode==='compare'&&<>
        <Road seconds={7+t*1.1} y={580} camera={slowCenter(sample('high',7+t*1.1)) ?? sample('high',7+t*1.1)[0].s} zoom={.85} focus={6}/>
        <Road seconds={7+t*1.1} y={900} group="low" camera={slowCenter(sample('high',7+t*1.1)) ?? sample('high',7+t*1.1)[0].s} zoom={.85} focus={6}/>
      </>}
      {mode==='ending'&&<>
        <Ring seconds={time} scale={.77} y={860}/>
        <g opacity={ease(at('e1'))}><circle cx={540} cy={860} r={155} fill="none" stroke={C.red} strokeWidth={1.5} opacity={.55}/><circle cx={540} cy={860} r={175+20*Math.sin(t*.5)} fill="none" stroke={C.red} opacity={.16}/></g>
      </>}
    </svg>
    {mode==='hook'&&<>
      <Label y={190} size={98}>车在向前。</Label>
      <div style={{position:'absolute',left:76,top:320,fontSize:98,fontWeight:750,color:C.red,opacity:reveal,transform:`translateY(${24*(1-reveal)}px)`}}>拥堵，向后。</div>
      <Label y={1000} size={34} color={C.blue}>车辆前进 →</Label>
      <Label y={1220} size={34} color={C.red}>← 低速区域移动</Label>
      <Label y={1420} size={40} opacity={revealOf('h2', 5)}>没有事故，谁在“倒退”？</Label>
    </>}
    {mode==='origin'&&<>
      <Label y={190} size={76}>倒回一次减速</Label>
      <Label y={305} size={34} color={C.dim}>没有路口，没有出口，也没有障碍。</Label>
      <Label y={930} size={54}>反应，不会同时发生。</Label>
      <Label y={1420} size={36} color={C.red}>红灯逐车亮起，响应沿车队传递。</Label>
    </>}
    {mode==='relay'&&<>
      <Label y={185} size={76}>车已经走了，</Label><Label y={285} size={76} color={C.red}>慢，还在传。</Label>
      <div style={{position:'absolute',left:350,top:760,width:380,fontSize:54,fontWeight:700,lineHeight:1.45,textAlign:'center',opacity:revealOf('r2')}}>同一团拥堵<br/><span style={{color:C.red}}>不同的车</span></div>
      <Label y={1465} size={36} color={C.blue}>蓝框车辆持续向前，红色慢区不断换车。</Label>
    </>}
    {mode==='compare'&&<>
      <Label y={185} size={74}>同样的减速，</Label><Label y={280} size={74}>两种结果。</Label>
      <Label y={420} size={36} color={C.red}>密集车流 · 响应放大</Label><Label y={740} size={36} color={C.blue}>稀疏车流 · 逐渐减弱</Label>
      <div style={{position:'absolute',left:76,top:1090,fontSize:30,color:C.dim}}>同序号第6辆车 · 相对速度</div>
      <div style={{position:'absolute',left:60,top:1140,width:950,height:360}}><Chart option={chart} width={950} height={360}/></div>
      <Label y={1505} size={24} color={C.dim} opacity={revealOf('d2', 5)}>预设模型 · 非实测 · 仅解释一种机制</Label>
    </>}
    {mode==='ending'&&<>
      <Label y={190} size={76}>堵到前面，</Label><Label y={290} size={76}>却什么也没有？</Label>
      <div style={{position:'absolute',left:330,top:775,width:420,fontSize:78,fontWeight:750,lineHeight:1.2,color:C.red,textAlign:'center'}}>拥堵波</div>
      <Label y={1320} size={48} opacity={revealOf('e2', 5)}>你可能刚刚穿过了一道波。</Label>
      <Label y={1450} size={24} color={C.dim}>原创示意动画与声音 · 机制依据：杉山等，2008<br/>预设模型，非实测；仅解释拥堵的一种机制。</Label>
    </>}
  </div>;
}
