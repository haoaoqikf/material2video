import {useEffect, useMemo, type ReactNode} from 'react';
import {createSceneEvents, motionCurve, painter, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import Stage from 'm2v/style/components/stage';
import ScreenSubtitle, {type ScreenSubtitleItem,type SubtitleVariant} from 'm2v/style/components/screen-subtitle';
import {T, SANS, LATIN} from 'm2v/style/components/kit';

export const WHITE='#F3EDDC', GOLD='#F1C64C', RED='#DE3B4B';
export const INK=T.colors.ink, MUTED=T.colors.muted, LINE=T.colors.line;
export const clamp=(v:number)=>Math.min(1,Math.max(0,v));
export const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
export const mixHex=(a:string,b:string,p:number)=>{
  const t=clamp(p),channel=(v:string,i:number)=>parseInt(v.slice(i,i+2),16);
  return `#${[1,3,5].map(i=>Math.round(mix(channel(a,i),channel(b,i),t)).toString(16).padStart(2,'0')).join('')}`;
};
export const progress=(f:number,a:number,b:number)=>clamp((f-a)/Math.max(1,b-a));
export const enter=motionCurve('easeOutCubic');
export const smooth=motionCurve('easeInOutSine');
export const track=(f:number,values:readonly [number,number][])=>painter.keyframeAt(values.map(([at,value])=>({at,value})),f,'smooth');
export const fade=(f:number,a:number,b:number,span=8)=>f<a||f>=b?0:(.25+.75*enter(progress(f,a,a+span)))*(1-.75*smooth(progress(f,b-span,b)));
export const pop=(f:number,at:number,amount=.06)=>track(f,[[at,1],[at+3,1+amount],[at+6,.99],[at+10,1]]);

export function useClock(config:CodeSceneProps){
  const clock=useSceneContext();
  const events=useMemo(()=>createSceneEvents(config.eventFrames),[config.eventFrames]);
  return {f:clock.elapsedSeconds*config.fps,e:events};
}
export function Text({x,y,text,size=72,color=WHITE,alpha=1,numeric=false,weight=650,align='middle',role,scale=1}:{x:number;y:number;text:string;size?:number;color?:string;alpha?:number;numeric?:boolean;weight?:number;align?:'start'|'middle'|'end';role?:string;scale?:number}){
  if(alpha<=0)return null;
  return <text x={x} y={y} textAnchor={align} dominantBaseline="central" fill={color} opacity={alpha} fontFamily={numeric?LATIN:SANS} fontSize={size} fontWeight={weight} transform={`translate(${x} ${y}) scale(${scale}) translate(${-x} ${-y})`} style={{fontVariantNumeric:'tabular-nums'}} data-m2v-role={role}>{text}</text>;
}
export function Dot({x,y,r=14,color=WHITE,alpha=1,sx=1,sy=1,glow=false,role}:{x:number;y:number;r?:number;color?:string;alpha?:number;sx?:number;sy?:number;glow?:boolean;role?:string}){
  return <g opacity={alpha} transform={`translate(${x} ${y}) scale(${sx} ${sy})`}>
    {glow?<circle r={r*4} fill="url(#luck-glow)"/>:null}
    <circle r={r} fill={color} data-m2v-role={role}/>
  </g>;
}
export function Frame({config,children,overlay,foreground,subtitleVariants}:{config:CodeSceneProps;children:ReactNode;overlay?:ReactNode;foreground?:ReactNode;subtitleVariants?:Record<number,SubtitleVariant>}){
  const {ready,elapsedSeconds}=useSceneContext();
  useEffect(()=>{ready();},[ready]);
  const captions=(config.props as {screenSubtitles?:ScreenSubtitleItem[]}).screenSubtitles??[];
  return <Stage width={config.width} height={config.height}>
    <svg width={config.width} height={config.height} viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>
      <defs><radialGradient id="luck-glow"><stop stopColor={GOLD} stopOpacity=".55"/><stop offset=".3" stopColor={GOLD} stopOpacity=".18"/><stop offset="1" stopColor={GOLD} stopOpacity="0"/></radialGradient></defs>
      {children}
    </svg>
    {overlay}
    {foreground?<svg width={config.width} height={config.height} viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>{foreground}</svg>:null}
    <ScreenSubtitle items={captions} frame={Math.floor(elapsedSeconds*config.fps+1e-5)} safeArea={config.subtitleSafeArea} size={96} glow={.04} risePx={7} driftPx={0} emphasis={/上场次数|每一次|预期|3倍|单次概率/} variants={subtitleVariants}/>
  </Stage>;
}
