import {useId} from 'react';
import {WHITE, GOLD, INK, track} from './shared';

/** 圆形上场标记的底点为局部 y=0；落地形变不改变接触点，且不依赖前帧状态。 */
export function Attempt({x,y,size=92,color=WHITE,alpha=1,stretch=1,tilt=0,groundY,frame=0,landAt,glow=.18,role='attempt-character'}:{
  x:number;y:number;size?:number;color?:string;alpha?:number;stretch?:number;tilt?:number;
  groundY?:number;frame?:number;landAt?:number;glow?:number;role?:string;
}){
  const uid=useId().replace(/[^a-zA-Z0-9_-]/g,'');
  const impact=landAt===undefined?0:track(frame,[[landAt,0],[landAt+2,1],[landAt+5,-.23],[landAt+10,0]]);
  const sy=stretch*(1-.18*impact),sx=(1+.2*impact)/stretch;
  const height=groundY===undefined?0:Math.max(0,groundY-y);
  return <g opacity={alpha}>
    <defs><radialGradient id={`${uid}-surface`} cx="32%" cy="25%" r="78%">
      <stop stopColor={color===GOLD?'#FFF5C8':color}/><stop offset=".65" stopColor={color}/><stop offset="1" stopColor={color===GOLD?'#B78A27':color===WHITE?'#BEB496':color}/>
    </radialGradient></defs>
    {glow>0?<circle cx={x} cy={y-size*.5} r={size*1.45} fill="url(#luck-glow)" opacity={glow}/>:null}
    {groundY!==undefined?<ellipse cx={x} cy={groundY+4} rx={size*(.28+Math.min(.38,height/500))} ry={size*.045} fill={color} opacity={.2*Math.max(0,1-height/380)}/>:null}
    <g transform={`translate(${x} ${y}) rotate(${tilt}) scale(${size*sx} ${size*sy})`}>
      <circle cx={0} cy={-.5} r={.5} fill={`url(#${uid}-surface)`} data-m2v-role={role}/>
      <path d="M-.29 -.63 A.33 .33 0 0 1 -.08 -.83" fill="none" stroke={color===GOLD?WHITE:INK} strokeOpacity={color===GOLD?.45:.12} strokeWidth={.045} strokeLinecap="round"/>
    </g>
  </g>;
}
