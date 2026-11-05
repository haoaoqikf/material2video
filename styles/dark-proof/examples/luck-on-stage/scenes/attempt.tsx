import {WHITE, GOLD, INK, track} from './shared';

/** 原创无五官轮廓。底点为局部y=0，压扁不改变接触点；无前帧状态。 */
export function Attempt({x,y,size=92,color=WHITE,alpha=1,stretch=1,tilt=0,groundY,frame=0,landAt,role='attempt-character'}:{
  x:number;y:number;size?:number;color?:string;alpha?:number;stretch?:number;tilt?:number;
  groundY?:number;frame?:number;landAt?:number;role?:string;
}){
  const impact=landAt===undefined?0:track(frame,[[landAt,0],[landAt+2,1],[landAt+5,-.23],[landAt+10,0]]);
  const sy=stretch*(1-.3*impact),sx=(1+.36*impact)/stretch;
  const height=groundY===undefined?0:Math.max(0,groundY-y);
  return <g opacity={alpha}>
    {groundY!==undefined?<ellipse cx={x} cy={groundY+4} rx={size*(.28+Math.min(.38,height/500))} ry={size*.045} fill={color} opacity={.2*Math.max(0,1-height/380)}/>:null}
    <g transform={`translate(${x} ${y}) rotate(${tilt}) scale(${size*sx} ${size*sy})`}>
      <path d="M0 -1.2 C-.12 -.98 -.46 -.56 -.46 -.3 C-.46 .1 .46 .1 .46 -.3 C.46 -.56 .12 -.98 0 -1.2Z" fill={color} data-m2v-role={role}/>
      <path d="M-.25 -.49 Q-.32 -.3 -.2 -.19" fill="none" stroke={color===GOLD?WHITE:INK} strokeOpacity={color===GOLD?.5:.12} strokeWidth={.045} strokeLinecap="round"/>
    </g>
  </g>;
}
