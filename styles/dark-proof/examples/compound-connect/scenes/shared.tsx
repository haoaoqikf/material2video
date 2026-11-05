import {useEffect, useMemo, type ReactNode} from 'react';
import {createSceneEvents, motionCurve, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import Stage from 'm2v/style/components/stage';
import ScreenSubtitle, {type ScreenSubtitleItem} from 'm2v/style/components/screen-subtitle';
import Impact, {type ImpactEvent} from 'm2v/style/components/impact';
import {T, SANS, LATIN} from 'm2v/style/components/kit';

export const WHITE=T.colors.ivory, GOLD=T.colors.gold, INK=T.colors.ink, MUTED=T.colors.muted, LINE=T.colors.line;
export const clamp=(p:number)=>Math.max(0,Math.min(1,p));
export const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
export const progress=(f:number,a:number,b:number)=>clamp((f-a)/Math.max(1,b-a));
export const arrive=motionCurve('easeOutExpo'), smooth=motionCurve('easeInOutCubic');
export const opacity=(f:number,a:number,b:number,span=10)=>f<a||f>=b?0:(.25+.75*arrive(progress(f,a,a+span)))*(1-.75*smooth(progress(f,b-span,b)));
export const fixed=(n:number)=>n.toFixed(2);
export function useClock(config:CodeSceneProps){
  const {elapsedSeconds}=useSceneContext();
  const events=useMemo(()=>createSceneEvents(config.eventFrames),[config.eventFrames]);
  return {f:elapsedSeconds*config.fps,e:events};
}
export function Text({x,y,text,size=72,color=WHITE,alpha=1,role,numeric=false,align='middle',weight=650}:{x:number;y:number;text:string;size?:number;color?:string;alpha?:number;role?:string;numeric?:boolean;align?:'start'|'middle'|'end';weight?:number}){
  return <text x={x} y={y} dominantBaseline="central" textAnchor={align} fontFamily={numeric?LATIN:SANS} fontSize={size} fontWeight={weight} fill={color} opacity={alpha} style={{fontVariantNumeric:'tabular-nums'}} data-m2v-role={role}>{text}</text>;
}
export function Ball({x,y,r=12,alpha=1}:{x:number;y:number;r?:number;alpha?:number}){
  return <g opacity={alpha}><circle cx={x} cy={y} r={r*4.6} fill="url(#gold-glow)"/><circle cx={x} cy={y} r={r} fill={GOLD}/><circle cx={x-r*.23} cy={y-r*.24} r={r*.26} fill="#FFF4D6"/></g>;
}
export function Frame({config,children,html,impacts=[]}:{config:CodeSceneProps;children:ReactNode;html?:ReactNode;impacts?:ImpactEvent[]}){
  const {elapsedSeconds,ready}=useSceneContext();
  useEffect(()=>{ready();},[ready]);
  const captions=(config.props as {screenSubtitles?:ScreenSubtitleItem[]}).screenSubtitles??[];
  return <Stage width={config.width} height={config.height}>
    <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>
      <defs><radialGradient id="gold-glow"><stop stopColor="#FFF4D6" stopOpacity=".9"/><stop offset=".22" stopColor={GOLD} stopOpacity=".38"/><stop offset="1" stopColor={GOLD} stopOpacity="0"/></radialGradient></defs>
      {children}
    </svg>
    {html}
    <Impact frame={elapsedSeconds*config.fps} width={1920} height={1080} totalFrames={config.durationInFrames} maskBottom={850} events={impacts}/>
    <ScreenSubtitle items={captions} frame={Math.floor(elapsedSeconds*config.fps+1e-5)} safeArea={config.subtitleSafeArea} size={64} risePx={12} driftPx={3} emphasis={/下一次|留下|差距|100轮|270.48/}/>
  </Stage>;
}
