import type {ReactNode} from 'react';
import {LATIN,SANS,T} from 'm2v/style/components/kit';
import type {Point} from './model';

export const {ivory:WHITE,gold:GOLD,muted:MUTED}=T.colors;
export type Phases=Record<string,number>;
export function Text({x,y,children,size=32,color=WHITE,weight=500,align='middle',opacity=1,latin=false,role}:{
  x:number;y:number;children:ReactNode;size?:number;color?:string;weight?:number;
  align?:'middle'|'start'|'end';opacity?:number;latin?:boolean;role?:string;
}){
  return <text x={x} y={y} textAnchor={align} dominantBaseline="central" data-m2v-role={role}
    fontFamily={latin?LATIN:SANS} fontSize={size} fontWeight={weight} fill={color} opacity={opacity}
    style={{fontVariantNumeric:'tabular-nums',letterSpacing:latin?'-.025em':'0'}}>{children}</text>;
}
export function Dot({at,radius=22,color=WHITE,opacity=1,glow=false,role}:{
  at:Point;radius?:number;color?:string;opacity?:number;glow?:boolean;role?:string;
}){
  return <g opacity={opacity}>
    {glow?<circle cx={at.x} cy={at.y} r={radius*3.6} fill="url(#packet-glow)"/>:null}
    <circle cx={at.x} cy={at.y} r={radius} fill={color} data-m2v-role={role}/>
    {glow?<circle cx={at.x-3} cy={at.y-4} r={radius*.37} fill={T.light.core} opacity={.85}/>:null}
  </g>;
}
