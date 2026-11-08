import type {CodeSceneProps} from '../src/code-scene/context';
import Counter from './components/counter';
import Burst from './components/burst';
import {Snowball} from './snow';
import {Frame,Text,Ball,WHITE,GOLD,MUTED,progress,arrive,smooth,mix,useClock} from './shared';
import {compounded} from './model';

export default function Hook(config:CodeSceneProps){
  const {f,e}=useClock(config),lock=e.frame('number-lock'),title=e.frame('title-start'),snow=e.frame('snow-start');
  const leaveNumber=smooth(progress(f,title-8,title)),enterTitle=arrive(progress(f,title,title+12));
  const leaveTitle=smooth(progress(f,snow-12,snow+2));
  // 轮次与总量共用离散步长，避免画面把插值数值写成某个已完成轮次。
  const round=Math.min(8,Math.floor(8*progress(f,0,lock-6))),numberProgress=(compounded(round)-100)/(compounded(8)-100);
  const handoff=progress(f,title-12,title+16),bounce=progress(f,title+16,snow-14);
  const ballX=f<title+16?mix(1000,1380,smooth(handoff)):mix(1380,1050,smooth(bounce));
  const ballY=f<title+16?mix(535,690,smooth(handoff))-Math.sin(Math.PI*handoff)*230:690-Math.abs(Math.sin(bounce*Math.PI*2))*80;
  const fall=progress(f,snow-14,snow+12);
  const snowProgress=progress(f,snow+12,e.frame('snow-impact'));
  const radius=mix(32,218,smooth(snowProgress)),x=mix(1050,1240,smooth(snowProgress)),y=800-radius;
  // 让同一主体收拢到下幕首行总量，先认回数字，再公开表格。
  const handoffStart=e.frame('snow-wipe'),handoffEnd=config.durationInFrames-12;
  const transfer=smooth(progress(f,handoffStart,handoffEnd));
  const shell=1-smooth(progress(f,handoffStart+6,handoffEnd-4));
  const ground=1-smooth(progress(f,handoffStart,handoffEnd-6));
  const titleOpacity=enterTitle*(1-leaveTitle);
  return <Frame config={config} impacts={[
    {id:'number-lock',preset:'formula',origin:{x:960,y:490},startFrame:lock},
  ]} html={<>{f<title?<div style={{position:'absolute',inset:0,opacity:1-leaveNumber}}>
    <Counter from={100} to={compounded(8)} progress={numberProgress} easing={p=>p} decimals={2} x={960} y={470} size={270} color={WHITE} ghosts={f<lock-6?{count:2,step:.045,offsetY:9,opacity:.15}:undefined}/>
  </div>:null}
  </>}>
    {f<title?<g opacity={1-leaveNumber}>
      <Text x={960} y={200} text="如果每轮只多1%" size={90}/>
      <Text x={960} y={695} text={`第 ${Math.floor(round)} 轮`} size={54} color={MUTED}/>
    </g>:null}
    {f>=title&&f<snow+2?<g opacity={titleOpacity} transform={`translate(0 ${30*(1-enterTitle)})`}>
      <Text x={960} y={330} text="让过去的成果" size={150}/>
      <Text x={960} y={580} text="参与下一次" size={174}/>
      <path d="M420 715Q950 620 1500 715" fill="none" stroke={GOLD} strokeWidth={2} opacity={.24}/>
      <Burst origin={{x:1380,y:690}} progress={progress(f,title+14,title+36)} count={20} rings={0} distance={90} size={3}/>
    </g>:null}
    {f>=title-12&&f<snow+12?<g><Ball x={mix(ballX,1050,smooth(fall))} y={mix(ballY,768,smooth(fall))} r={mix(18,32,fall)}/></g>:null}
    {f>=snow?<g>
      <g opacity={ground}>
      <path d="M100 805 Q800 785 1820 802" stroke={WHITE} strokeWidth={3.2} fill="none" opacity={arrive(progress(f,snow,snow+10))}/>
      {Array.from({length:48},(_,i)=>{
        const base=160+i*34,px=base-((f-snow)*4%34),taken=px<x+radius*.7;
        return <ellipse key={i} cx={px} cy={799+(i%3)*4} rx={5+i%5} ry={3} fill={taken?GOLD:WHITE} opacity={taken?.1:.6}/>;
      })}
      {[e.frame('snow-hit-1'),e.frame('snow-hit-2'),e.frame('snow-impact')].map((at,i)=><Burst key={at} origin={{x:mix(1050,1240,smooth(progress(at,snow+12,e.frame('snow-impact')))),y:798}} progress={progress(f,at,at+22)} count={20+i*10} distance={100+i*35} size={3} rings={0} seed={`snow-${i}`}/>)}
      </g>
      {shell>0?<g opacity={shell}><Snowball f={Math.min(f,handoffStart)-snow} x={mix(x,920,transfer)} y={mix(y,425,transfer)} r={mix(radius,24,transfer)}/></g>:null}
      {f>=handoffEnd-4?<Text x={920} y={425} text="100.00" size={70} numeric color={GOLD} alpha={.25+.75*arrive(progress(f,handoffEnd-4,handoffEnd))}/>:null}
    </g>:null}
  </Frame>;
}
