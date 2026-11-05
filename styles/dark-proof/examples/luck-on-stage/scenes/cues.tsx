import {samplePath,sampleTrail,ScreenBurstLayer,type Vec2} from 'm2v/code-scene';
import LightTrail from 'm2v/style/components/light-trail';
import Burst from 'm2v/style/components/burst';
import {Dot,GOLD,WHITE,progress,smooth,track} from './shared';
import {Afterglow} from './details';

/** 作品专属路径在模块加载时采样；球与风格光轨共用弧长及缓动，避免头尾脱节。 */
export const flight=(d:string)=>samplePath(d,48);
export function CueBall({f,start,end,points,fadeAt=end+5,r=24,seed}:{f:number;start:number;end:number;points:readonly Vec2[];fadeAt?:number;r?:number;seed:string}){
  if(f<start||f>=fadeAt+8)return null;
  const p=progress(f,start,end),head=sampleTrail({points,progress:p,length:.24,count:16,easing:smooth})[0];
  const alpha=1-smooth(progress(f,fadeAt,fadeAt+8));
  const sx=track(f,[[end,1],[end+2,1.32],[end+5,.93],[end+9,1]]);
  return <g opacity={alpha}>
    <LightTrail points={points} progress={p} width={18} length={.24} samples={16} glow={5} dust={5} opacity={f<end?1:1-smooth(progress(f,end,end+7))} seed={seed}/>
    <Dot x={head.x} y={head.y} r={r} color={WHITE} role="cue-ball" glow sx={sx} sy={2-sx}/>
  </g>;
}

/** 短促接触亮核和下坠余韵分别计时，文字稳定后不留整片发光遮罩。 */
export function Contact({f,at,x,y,strength=1,seed}:{f:number;at:number;x:number;y:number;strength?:number;seed:string}){
  return <>
    {f>at&&f<at+20?<Burst origin={{x,y}} progress={progress(f,at,at+20)} count={Math.round(30*strength)} distance={170*strength} size={5.5} rings={2} ringTravel={92*strength} ringThickness={3} seed={seed}/>:null}
    {f>=at&&f<at+5?<circle cx={x} cy={y} r={110*strength} fill="url(#luck-glow)" opacity={track(f,[[at,0],[at+1,.95],[at+4,0]])}/>:null}
    <Afterglow f={f} at={at+3} x={x} y={y} seed={`${seed}-fall`} count={Math.round(34*strength)} span={34}/>
  </>;
}

/** 复用SDK整屏粒子，仅在强重音挂载十帧；下落余光由Contact继续，不留常亮微尘。 */
export function StrongRelease({f,at,x,y,id}:{f:number;at:number;x:number;y:number;id:string}){
  if(f<at||f>=at+10)return null;
  return <div className="luck-strong-release">
    <style>{'.luck-strong-release canvas{mix-blend-mode:normal!important}'}</style>
    <ScreenBurstLayer frame={f} width={1920} height={1080} maskBottom={790} bursts={[{
      id,origin:{x,y},startFrame:at,durationFrames:10,count:560,reach:900,
      seed:id,opacity:.72,color:{core:WHITE,primary:GOLD,secondary:WHITE},
      bokehRatio:.07,streakRatio:.12,dustRatio:.04,lifetime:.85,drag:1.2,gravity:220,
      flash:.9,rings:{count:1,travel:600,thickness:2,opacity:.4},
    }]}/>
  </div>;
}
