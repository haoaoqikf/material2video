import {particleField} from 'm2v/code-scene';
import {GOLD,WHITE,INK,progress,smooth,mix,track} from './shared';

export const PORTAL_FRAMES=24;
/** 两幕用同一个局部时钟求值；剪点前后保持同一中心、环半径与粒子位置。 */
export function Portal({frame}:{frame:number}){
  if(frame<0||frame>=PORTAL_FRAMES)return null;
  const p=progress(frame,0,PORTAL_FRAMES),move=smooth(p);
  const x=mix(1490,610,move),y=mix(610,530,move);
  const radius=track(frame,[[0,36],[5,80],[12,980],[18,440],[24,246]]);
  const space=Math.sin(Math.PI*progress(frame,3,24));
  const alpha=1-smooth(progress(frame,18,24));
  const dust=particleField({count:72,progress:progress(frame,3,24),seed:'luck-through-ring',origin:{x,y},distance:1500,lifetime:1,size:2.2,opacity:.7,easing:p=>p});
  return <g data-m2v-effect="ring-passage" opacity={alpha}>
    <rect width={1920} height={1080} fill={INK} opacity={space*.92}/>
    {dust.map(v=>{
      const dx=v.x-x,dy=v.y-y,scale=1+.035*space;
      return <line key={v.index} x1={v.x} y1={v.y} x2={x+dx*scale} y2={y+dy*scale} stroke={v.index%5===0?WHITE:GOLD} strokeWidth={1.2} opacity={v.opacity*space}/>;
    })}
    {[.25,.5,.75].map((k,i)=><circle key={k} cx={x} cy={y} r={Math.max(1,radius*k)} fill="none" stroke={i%2?WHITE:GOLD} strokeWidth={1.5} opacity={space*.25}/>)}
    <circle cx={x} cy={y} r={radius} fill="none" stroke={GOLD} strokeWidth={3} opacity={.9}/>
  </g>;
}
