import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,MUTED,progress,enter,smooth,pop,track,useClock} from './shared';
import {Backdrop} from './details';
import {AccentRelease,StrongRelease} from './cues';

export default function Area(config:CodeSceneProps){
 const {f,e}=useClock(config);
 const n=10+20*smooth(progress(f,e.frame('width-start'),e.frame('width-lock')));
 const percent=10+20*smooth(progress(f,e.frame('height-start'),e.frame('height-lock')));
 const shownN=Math.round(n),shownPercent=Math.round(percent);
 const expected=shownN*shownPercent/100,w=280*n/10,h=120*percent/10;
 const result=Math.abs(expected-Math.round(expected))<.04?String(Math.round(expected)):expected.toFixed(1);
 const formula=e.frame('formula-start'),collapse=enter(progress(f,formula,formula+10));
 const formulaIn=enter(progress(f,formula+12,e.frame('formula-lock')));
 const widthLight=track(f,[[e.frame('width-start'),0],[e.frame('width-start')+3,.8],[e.frame('width-lock'),.6],[e.frame('width-lock')+8,0]]);
 const heightLight=track(f,[[e.frame('height-start'),0],[e.frame('height-start')+3,.8],[e.frame('height-lock'),.6],[e.frame('height-lock')+8,0]]);
 const nineFlash=track(f,[[e.frame('nine-lock'),0],[e.frame('nine-lock')+2,1],[e.frame('nine-lock')+5,.3],[e.frame('nine-lock')+12,0]]);
 const foreground=f>=formula+12?<g opacity={formulaIn}>
   <Text x={420} y={450} text="30" size={220} numeric weight={500}/>
   <Text x={700} y={450} text="×" size={100} numeric color={WHITE}/>
   <Text x={1000} y={450} text="30%" size={220} numeric weight={500}/>
   <Text x={1320} y={450} text="=" size={100} numeric/>
   <Text x={1580} y={450} text="9" size={250} numeric weight={550} color={GOLD} scale={pop(f,e.frame('formula-lock'),.04)}/>
   <Text x={420} y={730} text="尝试次数" size={74}/>
   <Text x={1000} y={730} text="单次成功概率" size={74}/>
   <Text x={1580} y={730} text="预期次数" size={74} color={GOLD}/>
  </g>:null;
 return <Frame config={config} subtitleVariants={{0:{enter:'wipe',enterFrames:8,exitFrames:6}}} foreground={foreground} overlay={<>
  <AccentRelease f={f} at={e.frame('nine-lock')} x={1580} y={520} id="area-nine-flash" scale={.7}/>
  <StrongRelease f={f} at={e.frame('formula-lock')} x={1530} y={450} id="formula-nine-release"/>
 </>}>
  <Backdrop id="area-stage"/>
  <Text x={960} y={130} text="预期成功次数" size={116}/>
  {f<formula+10?<g opacity={1-collapse}>
   <Text x={480+w/2} y={280} text={`${shownN}次尝试`} size={80}/>
   <Text x={250} y={420} text="单次概率" size={72}/>
   <Text x={250} y={570} text={`${shownPercent}%`} size={100} numeric color={f>=e.frame('height-start')?GOLD:WHITE}/>
   <g transform={`translate(${900+680*collapse} ${520-10*collapse}) scale(${1-.94*collapse}) translate(-900 -520)`}>
    {/* 量测只绑定定量矩形；扫光是边缘反馈，不改变面积比例。 */}
    <rect x={480} y={700-h} width={w} height={h} fill={GOLD} opacity={.88}/>
    {[1,2].map(k=><g key={k}>
     {w>280*k?<path d={`M${480+280*k} ${700-h}V700`} stroke={WHITE} strokeWidth={3} opacity={.65}/>:null}
     {h>120*k?<path d={`M480 ${700-120*k}H${480+w}`} stroke={WHITE} strokeWidth={3} opacity={.65}/>:null}
    </g>)}
    <path d={`M480 ${700-h}H${480+w}V700H480Z`} fill="none" stroke={GOLD} strokeWidth={3}/>
    <path d={`M${480+w} ${700-h}V700`} stroke={WHITE} strokeWidth={8} opacity={widthLight}/>
    <path d={`M480 ${700-h}H${480+w}`} stroke={WHITE} strokeWidth={8} opacity={heightLight}/>
    <rect x={480-6} y={700-h-6} width={w+12} height={h+12} fill="none" stroke={WHITE} strokeWidth={8} opacity={nineFlash*.8}/>
   </g>
   <Text x={1580} y={520} text={result} size={230} numeric weight={550} color={GOLD} scale={pop(f,e.frame('nine-lock'),.055)}/>
   <Text x={1580} y={755} text="预期次数" size={76} color={GOLD}/>
   <Text x={1730} y={825} text="乘法示意" size={23} color={MUTED} align="end"/>
  </g>:null}

 </Frame>;
}
