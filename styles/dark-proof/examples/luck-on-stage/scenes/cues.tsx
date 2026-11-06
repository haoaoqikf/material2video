import {samplePath,sampleTrail,ScreenBurstLayer,type Vec2} from 'm2v/code-scene';
import Burst from 'm2v/style/components/burst';
import LightTrail from 'm2v/style/components/light-trail';
import {GOLD,WHITE,progress,smooth,enter,track} from './shared';
import {Afterglow} from './details';

export const flight=(d:string)=>samplePath(d,48);

/** 复用风格包的锥形笔触；离散尾光越旧越向下落，收速后同步熄灭。 */
export function FlightMotes({points,p,energy=1}:{points:readonly Vec2[];p:number;energy?:number}){
  if(energy<=0)return null;
  const trail=sampleTrail({points,progress:p,length:.19,count:11,easing:smooth});
  return <g data-m2v-effect="flight-trail">
    <LightTrail points={points} progress={p} color={GOLD} width={18} length={.19} samples={20} opacity={energy*.85} glow={1.2} dust={0}/>
    {trail.slice(1).map((v,i)=><circle key={i} cx={v.x} cy={v.y+1.1*(i+1)*(i+1)} r={Math.max(.8,4.2-i*.32)} fill={GOLD} opacity={energy*(1-i/10)*.85}/>) }
  </g>;
}

/** 普通接触只轻点，关键结果才释放亮核、扩环和独立下坠余光。 */
export function Contact({f,at,x,y,strength=1,seed,kind='local',color=GOLD}:{f:number;at:number;x:number;y:number;strength?:number;seed:string;kind?:'touch'|'local';color?:string}){
  const touch=kind==='touch',span=touch?15:25;
  if(f<at||f>=at+span+14)return null;
  const p=progress(f,at,at+span),attack=track(f,[[at,0],[at+1,1],[at+3,.35],[at+5,0]]);
  return <g data-m2v-effect={touch?'contact-touch':'contact-local'}>
    {f<at+span?<Burst origin={{x,y}} progress={enter(p)} count={Math.round((touch?10:110)*strength)} distance={(touch?55:300)*strength} size={touch?2.8:4.2} rings={touch?0:2} ringTravel={320*strength} ringThickness={2.4} seed={seed} color={color} secondaryColor={color===GOLD?WHITE:color} opacity={touch?.55:.95}/>:null}
    <circle cx={x} cy={y} r={(touch?30:85)*strength} fill={color===GOLD?'url(#luck-glow)':color} opacity={attack*(touch?.28:.95)}/>
    {!touch?<>
      <circle cx={x} cy={y} r={42*strength} fill={WHITE} opacity={attack*.24}/>
      <circle cx={x} cy={y} r={13*strength} fill={WHITE} opacity={attack}/>
      <circle cx={x} cy={y} r={16+155*strength*enter(p)} fill="none" stroke={GOLD} strokeWidth={3} opacity={1-smooth(progress(f,at+2,at+span))}/>
    </>:null}
    <Afterglow f={f} at={at+2} x={x} y={y} seed={`${seed}-fall`} color={color} count={Math.round((touch?8:48)*strength)} span={touch?18:34}/>
  </g>;
}

/** 数值或命中落定时的短促闪释；独立粒子随后受重力下落。 */
export function AccentRelease({f,at,x,y,id,scale=1}:{f:number;at:number;x:number;y:number;id:string;scale?:number}){
  if(f<at||f>=at+27)return null;
  const warped=at+26*enter(progress(f,at,at+26));
  return <div className="luck-accent-release">
    <style>{'.luck-accent-release canvas{mix-blend-mode:normal!important}'}</style>
    <ScreenBurstLayer frame={warped} width={1920} height={1080} maskBottom={850} bursts={[{
      id,origin:{x,y},startFrame:at,durationFrames:27,count:Math.round(300*scale),reach:540*scale,
      seed:id,opacity:.9,color:{core:WHITE,primary:GOLD,secondary:WHITE},
      bokehRatio:.02,streakRatio:.16,dustRatio:.06,lifetime:.9,drag:1.6,gravity:320,
      flash:.95,rings:{count:2,travel:680*scale,thickness:2.4,opacity:.85},
    }]}/>
  </div>;
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
      flash:.85,rings:{count:3,travel:1120,thickness:2.5,opacity:.9},
    }]}/>
    <svg width="1920" height="1080" viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>
      <circle cx={x} cy={y} r={260} fill="url(#luck-glow)" opacity={track(age,[[0,0],[1,1],[3,.65],[6,0]])}/>
      <circle cx={x} cy={y} r={28} fill={WHITE} opacity={track(age,[[0,0],[1,1],[3,0]])}/>
    </svg>
  </div>;
}
