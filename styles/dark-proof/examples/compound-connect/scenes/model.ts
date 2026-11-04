/** 原创机制寓言状态；无现实倍率或金融模型。时刻由 compose.py 注入。 */
import {motionCurve} from 'm2v/code-scene';
export type Point={x:number;y:number};
export type Beats=Record<string,number>;
export const clamp=(x:number)=>Math.max(0,Math.min(1,x));
export const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
export const progress=(f:number,a:number,b:number)=>clamp((f-a)/Math.max(1,b-a));
export const ease=motionCurve('easeInOutCubic');
export const arrive=motionCurve('easeOutCubic');
export const MOTHER={x:540,y:770,scale:1};
export const CHILD={x:1130,y:770,scale:.68};
export const THIRD={x:1550,y:770,scale:.43};
export const POD={x:220,y:-335};
export const podAt=(tree:typeof MOTHER)=>({x:tree.x+POD.x*tree.scale,y:tree.y+POD.y*tree.scale});
export function flight(f:number,start:number,end:number,from:Point,to:Point):Point{
  const p=progress(f,start,end);
  return {x:mix(from.x,to.x,ease(p)),y:mix(from.y,to.y,p*p)-Math.sin(Math.PI*p)*85};
}
export function pulse(f:number,start:number,duration=20):number{
  const p=progress(f,start,start+duration);return 1+Math.sin(Math.PI*p)*.085;
}
export function growth(f:number,start:number,end:number):number{return arrive(progress(f,start,end));}
export function groveState(f:number,b:Beats){
  return {mother:growth(f,b['mother-grow'],b['mother-ready']),child:growth(f,b['child-grow'],b['child-ready']),
    third:growth(f,b['third-grow'],b['third-ready']),firstFlying:f>=b['first-release']&&f<b['first-land'],
    secondFlying:f>=b['second-release']&&f<b['second-land'],motherProductive:f>=b['mother-fruit'],
    childProductive:f>=b['child-fruit'],thirdProductive:f>=b['third-fruit']};
}
