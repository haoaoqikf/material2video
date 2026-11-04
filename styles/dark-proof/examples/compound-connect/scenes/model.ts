/** 时间选择观察状态；轮次决定数学真值。资源与读数必须共同取用此模型。 */
export type Model = {initial: number; rate: number; rounds: number; unit: number};
export type Point = {x: number; y: number};
export type Events = Readonly<Record<string, number>>;
export const clamp = (x: number) => Math.max(0, Math.min(1, x));
export const ease = (x: number) => -(Math.cos(Math.PI * clamp(x)) - 1) / 2;
export const progress = (f: number, a: number, b: number) => clamp((f-a)/Math.max(1,b-a));
export const mix = (a: number, b: number, t: number) => a+(b-a)*t;
export function ledger(model: Model, round: number, reinvest: boolean) {
  const n = Math.max(0, Math.min(model.rounds, Math.floor(round)));
  const active = reinvest ? model.initial*(1+model.rate)**n : model.initial;
  const saved = reinvest ? 0 : model.initial*model.rate*n;
  return {round:n, active, saved, total:active+saved, output:active*model.rate};
}
export function tokenPosition(index: number): Point {
  return {x:800+(index%6)*64, y:590+Math.floor(index/6)*64};
}
/** 一条连续返回路径，终点就是新资源圆片的位置。 */
export function returnPath(destination: Point): Point[] {
  const arc = Array.from({length:100},(_,i)=>{
    // 从右下出口出发，一圈后在资源区下缘并入，避免连接线横穿主读数。
    const a=.62+i/99*(Math.PI*2+.23);
    return {x:960+Math.cos(a)*330,y:452+Math.sin(a)*300};
  });
  const last=arc[arc.length-1];
  return [...arc,...Array.from({length:22},(_,i)=>{
    const t=(i+1)/22;
    return {x:mix(last.x,destination.x,t),y:mix(last.y,destination.y,t)};
  })];
}
export function returnState(frame: number, events: Events, model: Model) {
  const cycles=['return','second','third'].map((id,i)=>({round:i+1,
    outputAt:events[`${id}-output`],travelAt:events[`${id}-travel`],mergeAt:events[`${id}-merge`]}));
  const done=cycles.filter(x=>frame>=x.mergeAt).length;
  const current=cycles.find(x=>frame>=x.outputAt&&frame<x.mergeAt);
  const state=ledger(model,done,true);
  if(!current) return {...state,packet:null};
  const source=ledger(model,current.round-1,true);
  const path=returnPath(tokenPosition(Math.floor(source.active/model.unit)));
  const travel=progress(frame,current.travelAt,current.mergeAt);
  return {...state,packet:{value:source.output,travel,path,round:current.round}};
}
export function format(value: number,digits=0): string {
  return value.toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
}
