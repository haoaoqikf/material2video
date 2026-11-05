import {WHITE,GOLD,INK} from './shared';
const noise=(i:number)=>{const v=Math.sin(i*127.1+17.3)*43758.5453;return v-Math.floor(v);};
export function Snowball({f,r=150,x=1000,y=580,role}:{f:number;r?:number;x?:number;y?:number;role?:string}){
 const path=Array.from({length:70},(_,i)=>{const a=i/69*Math.PI*2,j=1+.018*Math.sin(i*2.4)+.009*Math.cos(i*5.9);return `${i===0?'M':'L'}${Math.cos(a)*r*j} ${Math.sin(a)*r*j}`;}).join(' ')+'Z';
 return <g transform={`translate(${x} ${y})`} data-m2v-role={role}>
  <path d={path} fill={WHITE} stroke={WHITE} strokeWidth={4}/>
  <g transform={`rotate(${f*1.7})`}>
  {[.3,.58,.8].map((q,i)=><path key={q} d={`M${-r*q} 0 A${r*q} ${r*q*.9} 0 1 1 ${r*q} 2 A${r*q*.8} ${r*q} 0 0 1 ${r*q*.1} ${r*q*.75}`} stroke={i===1?GOLD:INK} opacity={i===1?.6:.28} strokeWidth={i===1?3:2} fill="none"/>)}
  {Array.from({length:48},(_,i)=>{const a=noise(i)*6.28,d=Math.sqrt(noise(i+130))*r*.94;return <path key={i} d={`M${Math.cos(a)*d} ${Math.sin(a)*d} l${noise(i+70)*12+2} ${noise(i+19)*7-3}`} stroke={INK} strokeWidth={1.4} opacity={.18}/>;})}
  </g>
 </g>;
}
