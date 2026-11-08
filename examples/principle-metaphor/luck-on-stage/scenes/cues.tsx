import {samplePath} from '../src/code-scene/dynamics';
import {ScreenBurstLayer} from '../src/code-scene/effects/screen-burst';
import type {Vec2} from '../src/code-scene/dynamics';
import Burst from './components/burst';
import {GOLD,WHITE,mixHex,progress,smooth,enter,track} from './shared';
import {Afterglow} from './details';

export const flight=(d:string)=>samplePath(d,48);

export type LightSample=Vec2&{color:string};

/** 头部直接取球心；旧光滴保留发出时色相，随后因年龄下坠并逐粒衰减。 */
export function FlightMotes({samples,energy=1}:{samples:readonly LightSample[];energy?:number}){
  if(energy<=0||samples.length===0)return null;
  const head=samples[0];
  return <g data-m2v-effect="flight-motes" style={{mixBlendMode:'screen'}}>
    <circle cx={head.x} cy={head.y} r={35} fill="url(#luck-glow)" opacity={energy*.8}/>
    <circle cx={head.x} cy={head.y} r={6} fill={WHITE} opacity={energy*.72}/>
    {samples.slice(1).flatMap((v,i)=>{
      const age=i+1,life=Math.max(0,1-age/13),gravity=.42*age*age;
      const before=samples[i],dx=before.x-v.x,dy=before.y-v.y,length=Math.hypot(dx,dy)||1;
      return [0,1].map(k=>{
        const spread=(k===0?-1:1)*(2+(age%4)*1.5),jitter=((age*17+k*11)%7-3)*1.1;
        const x=v.x-dy/length*spread+jitter,y=v.y+dx/length*spread+gravity;
        const size=(k===0?(age%4===0?6:4.2):(age%3===0?3.5:1.9))*life;
        const opacity=energy*life*(k===0?(age%5===0?.38:1):.7);
        return <g key={`${age}-${k}`}>
          <circle cx={x} cy={y} r={size*2.4} fill={v.color} opacity={opacity*.12}/>
          <circle cx={x} cy={y} r={Math.max(.55,size)} fill={k===0?mixHex(v.color,WHITE,.55):v.color} opacity={opacity}/>
        </g>;
      });
    })}
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
