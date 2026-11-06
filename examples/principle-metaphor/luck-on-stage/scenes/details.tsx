import {burstField} from 'm2v/code-scene';
import {GOLD,INK,progress} from './shared';

/** 复用确定性粒子场；寿命内先扩散再下坠，不给整层套统一淡出。 */
export function Afterglow({f,at,x,y,seed,span=38,count=38,color=GOLD}:{f:number;at:number;x:number;y:number;seed:string;span?:number;count?:number;color?:string}){
  if(f<=at||f>=at+span)return null;
  const particles=burstField({count,progress:progress(f,at,at+span),seed,origin:{x,y},speed:165,speedJitter:.65,drag:2.6,gravity:270,lifetime:.94,size:4.8,opacity:.8,easing:p=>p});
  return <g>{particles.map(p=><ellipse key={p.index} cx={p.x} cy={p.y} rx={p.size*.65} ry={p.size*(1+.8*p.age)} fill={color} opacity={p.opacity}/>)}</g>;
}

export function Backdrop({id}:{id:string}){
  return <><defs><radialGradient id={id} cx="50%" cy="42%" r="62%" gradientTransform="translate(0 .1596) scale(1 .62)"><stop stopColor="#121316"/><stop offset=".68" stopColor={INK}/></radialGradient></defs><rect width={1920} height={1080} fill={`url(#${id})`}/></>;
}
