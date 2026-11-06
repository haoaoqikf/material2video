import {samplePath,sampleTrail,ScreenBurstLayer,type Vec2} from 'm2v/code-scene';
import Burst from 'm2v/style/components/burst';
import {GOLD,WHITE,progress,smooth,enter,track} from './shared';
import {Afterglow} from './details';

export const flight=(d:string)=>samplePath(d,48);

/** 离散短寿命光点随速度收回，不生成连续白色笔触。 */
export function FlightMotes({points,p,energy=1}:{points:readonly Vec2[];p:number;energy?:number}){
  if(energy<=0)return null;
  const trail=sampleTrail({points,progress:p,length:.045,count:7,easing:smooth});
  return <g opacity={energy} data-m2v-effect="flight-motes">{trail.slice(1).map((v,i)=><circle key={i} cx={v.x} cy={v.y+(i%2?1:-1)*(3+i)} r={2.8-i*.28} fill={GOLD} opacity={(1-i/7)*.6}/>)}</g>;
}

/** 普通接触只轻点，关键结果才释放亮核、扩环和独立下坠余光。 */
export function Contact({f,at,x,y,strength=1,seed,kind='local',color=GOLD}:{f:number;at:number;x:number;y:number;strength?:number;seed:string;kind?:'touch'|'local';color?:string}){
  const touch=kind==='touch',span=touch?15:25;
  if(f<at||f>=at+span+14)return null;
  const p=progress(f,at,at+span),attack=track(f,[[at,0],[at+1,1],[at+3,.35],[at+5,0]]);
  return <g data-m2v-effect={touch?'contact-touch':'contact-local'}>
    {f<at+span?<Burst origin={{x,y}} progress={enter(p)} count={Math.round((touch?10:65)*strength)} distance={(touch?55:230)*strength} size={touch?2.8:4.2} rings={touch?0:1} ringTravel={200*strength} ringThickness={2} seed={seed} color={color} secondaryColor={color===GOLD?WHITE:color} opacity={touch?.55:.85}/>:null}
    <circle cx={x} cy={y} r={(touch?30:85)*strength} fill={color===GOLD?'url(#luck-glow)':color} opacity={attack*(touch?.28:.95)}/>
    {!touch?<circle cx={x} cy={y} r={8*strength} fill={WHITE} opacity={attack}/>:null}
    <Afterglow f={f} at={at+2} x={x} y={y} seed={`${seed}-fall`} color={color} count={Math.round((touch?8:48)*strength)} span={touch?18:34}/>
  </g>;
}

/** 主爆快起后衰减，公式及字幕由前景层保护；只在当前事件窗口挂载Canvas。 */
export function StrongRelease({f,at,x,y,id}:{f:number;at:number;x:number;y:number;id:string}){
  if(f<at||f>=at+36)return null;
  const age=f-at,warped=at+32*enter(progress(f,at,at+32));
  return <div className="luck-strong-release">
    <style>{'.luck-strong-release canvas{mix-blend-mode:normal!important}'}</style>
    <ScreenBurstLayer frame={warped} width={1920} height={1080} maskBottom={850} bursts={[{
      id,origin:{x,y},startFrame:at,durationFrames:32,count:900,reach:820,
      seed:id,opacity:.95,color:{core:WHITE,primary:GOLD,secondary:WHITE},
      bokehRatio:.015,streakRatio:.2,dustRatio:.06,lifetime:.95,drag:1.8,gravity:300,
      flash:.35,rings:{count:2,travel:1050,thickness:2,opacity:.7},
    }]}/>
    <svg width="1920" height="1080" viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>
      <circle cx={x} cy={y} r={100} fill="url(#luck-glow)" opacity={track(age,[[0,0],[1,1],[3,.65],[6,0]])}/>
      <circle cx={x} cy={y} r={12} fill={WHITE} opacity={track(age,[[0,0],[1,1],[3,0]])}/>
    </svg>
  </div>;
}
