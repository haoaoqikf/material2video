import {useEffect,type ReactNode} from 'react';
import {useSceneContext,type CodeSceneProps} from 'm2v/code-scene';
import Stage from 'm2v/style/components/stage';
import ScreenSubtitle,{type ScreenSubtitleItem} from 'm2v/style/components/screen-subtitle';
import HandDrawnLine from 'm2v/style/components/hand-drawn-line';
import {SANS,LATIN,T} from 'm2v/style/components/kit';
import {arrive,clamp,type Beats} from './model';
export const WHITE=T.colors.ivory,GOLD=T.colors.gold,INK=T.colors.ink,MUTED=T.colors.muted;
export type Props={beats:Beats;screenSubtitles:ScreenSubtitleItem[]};
export function Text({x,y,children,size=60,color=WHITE,opacity=1,weight=650,latin=false,role}:{
  x:number;y:number;children:ReactNode;size?:number;color?:string;opacity?:number;weight?:number;latin?:boolean;role?:string}){
  return <text x={x} y={y} textAnchor="middle" dominantBaseline="central" fill={color}
    opacity={opacity} fontFamily={latin?LATIN:SANS} fontSize={size} fontWeight={weight}
    data-m2v-role={role} style={{fontVariantNumeric:'tabular-nums',letterSpacing:latin?'-.025em':'.025em'}}>{children}</text>;
}
export function Frame({config,children,impact}:{config:CodeSceneProps;children:ReactNode;impact?:ReactNode}){
  const {elapsedSeconds,ready}=useSceneContext();const {screenSubtitles}=config.props as unknown as Props;
  useEffect(()=>{ready();},[ready]);
  return <Stage width={config.width} height={config.height}>
    <svg width={config.width} height={config.height} viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>
      <defs><radialGradient id="seed-light"><stop offset="0" stopColor="#FFF4D6" stopOpacity=".8"/>
        <stop offset=".3" stopColor={GOLD} stopOpacity=".25"/><stop offset="1" stopColor={GOLD} stopOpacity="0"/></radialGradient></defs>
      {children}<Text x={1740} y={847} size={20} color={MUTED} weight={450}>机制示意</Text>
    </svg>{impact}
    <ScreenSubtitle items={screenSubtitles} frame={Math.round(elapsedSeconds*config.fps)} safeArea={config.subtitleSafeArea}
      size={66} risePx={17} driftPx={6} glow={.09} emphasis={/新的种子|也结出|方法|复利效应/}/>
  </Stage>;
}
export function Seed({x,y,scale=1,angle=0,gold=true,opacity=1,role}:{x:number;y:number;scale?:number;angle?:number;gold?:boolean;opacity?:number;role?:string}){
  return <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`} opacity={opacity} data-m2v-role={role}>
    {gold?<ellipse rx={61} ry={48} fill="url(#seed-light)" opacity={.7}/>:null}
    <path d="M0 -27 C30 -13 29 14 0 29 C-25 15 -25 -13 0 -27Z" fill={gold?GOLD:WHITE} stroke={WHITE} strokeWidth={1.2}/>
    <path d="M1 -22 Q-8 0 1 24" fill="none" stroke={INK} strokeWidth={2.3} opacity={.6}/>
    <path d="M5 -17 Q15 -6 13 7" fill="none" stroke={WHITE} strokeWidth={2} opacity={.65}/>
  </g>;
}
const branches=[
  {d:'M0 0 C-14 -120 20 -210 0 -440',w:29,end:[0,-440]},
  {d:'M-3 -170 C-47 -210 -130 -220 -205 -284',w:21,end:[-205,-284]},
  {d:'M0 -214 C70 -244 153 -226 253 -315',w:20,end:[253,-315]},
  {d:'M-2 -280 C-68 -293 -94 -345 -147 -380',w:15,end:[-147,-380]},
  {d:'M4 -315 C59 -338 103 -380 121 -432',w:14,end:[121,-432]},
  {d:'M-104 -231 Q-119 -281 -98 -326',w:10,end:[-98,-326]},
  {d:'M138 -260 Q160 -307 151 -359',w:10,end:[151,-359]},
  {d:'M-37 -344 Q-72 -398 -53 -461',w:10,end:[-53,-461]},
  {d:'M50 -352 Q33 -400 54 -467',w:10,end:[54,-467]},
];
const leaves=branches.flatMap((branch,i)=>{
  const [x,y]=branch.end;return Array.from({length:4},(_,j)=>({x:x+Math.cos(j*1.7+i)*37,y:y+Math.sin(j*1.8+i)*26,
    angle:(j%2===0?-1:1)*(40+j*19)+i*13,start:.38+i*.018+j*.025}));
});
export function Soil({x=960,y=785,width=1500,opacity=1}:{x?:number;y?:number;width?:number;opacity?:number}){
  return <g opacity={opacity}><path d={`M${x-width/2} ${y} Q${x-width*.15} ${y-4} ${x} ${y} T${x+width/2} ${y}`}
    fill="none" stroke={WHITE} strokeWidth={2} opacity={.35}/>
    {Array.from({length:17},(_,i)=><path key={i} d={`M${x-width/2+i*width/16} ${y+9+(i%3)*5} l${9+i%4} ${-2-i%2}`}
      stroke={MUTED} strokeWidth={1.4} opacity={.5}/>)}</g>;
}
export function Tree({x,y,scale=1,grow=1,gold=false,tone,fruit=0,departed=false,role}:{x:number;y:number;scale?:number;grow?:number;gold?:boolean;tone?:string;fruit?:number;departed?:boolean;role?:string}){
  const p=clamp(grow),color=tone??(gold?GOLD:WHITE);if(p<=0)return null;
  return <g transform={`translate(${x} ${y}) scale(${scale})`} data-m2v-role={role}>
    <g opacity={arrive(p)}>
      <HandDrawnLine d="M0 0 Q-35 27 -91 28 M0 0 Q30 23 86 26 M0 0 Q-12 32 -32 44" color={color} width={7} progress={Math.min(1,p*2)} ghostOffset={0}/>
      {branches.map((b,i)=><HandDrawnLine key={i} d={b.d} color={color} width={b.w} progress={clamp((p-i*.025)/.7)} ghostOffset={.45}/>)}
      {leaves.map((leaf,i)=>{
        const lp=arrive(clamp((p-leaf.start)/.25));return <g key={i} opacity={lp}>
          <path d={`M${branches[Math.floor(i/4)].end.join(' ')} L${leaf.x} ${leaf.y}`} stroke={color} strokeWidth={2.1}/>
          <g transform={`translate(${leaf.x} ${leaf.y}) rotate(${leaf.angle}) scale(${lp})`}>
          <path d="M0 0 C-35 -7 -51 -34 -46 -58 C-18 -56 5 -29 0 0Z" fill={color}/>
          <path d="M-3 -7 L-38 -49" stroke={INK} strokeWidth={1.1} opacity={.5}/></g></g>;
      })}
    </g>
    {fruit>0?<g opacity={fruit}>{[[220,-335],[-164,-292],[91,-397]].map(([a,b],i)=><g key={i} opacity={i===0&&departed?0:1}>
      <path d={i===0?'M253 -315 Q245 -355 220 -360 L220 -355':`M${a-4} ${b-25} q7 10 4 22`}
        stroke={GOLD} strokeWidth={3} fill="none"/><Seed x={a} y={b} scale={.8}/>
    </g>)}</g>:null}
  </g>;
}
