import type {CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,MUTED,progress,enter,smooth,pop,useClock} from './shared';
import {Backdrop} from './details';
import {Contact,StrongRelease} from './cues';
import {Attempt} from './attempt';

export default function Area(config:CodeSceneProps){
 const {f,e}=useClock(config);
 const n=10+20*smooth(progress(f,e.frame('width-start'),e.frame('width-lock')));
 const percent=10+20*smooth(progress(f,e.frame('height-start'),e.frame('height-lock')));
 const expected=n*percent/100,w=280*n/10,h=120*percent/10;
 const result=Math.abs(expected-Math.round(expected))<.04?String(Math.round(expected)):expected.toFixed(1);
 const formula=e.frame('formula-start'),collapse=enter(progress(f,formula,formula+10));
 const formulaIn=enter(progress(f,formula+12,e.frame('formula-lock')));
 const foreground=f>=formula+12?<g opacity={formulaIn}>
   <Text x={420} y={450} text="30" size={220} numeric weight={500} role="formula-n"/>
   <Text x={700} y={450} text="×" size={100} numeric color={WHITE} role="formula-times"/>
   <Text x={1000} y={450} text="30%" size={220} numeric weight={500} role="formula-p"/>
   <Text x={1320} y={450} text="=" size={100} numeric role="formula-equals"/>
   <Text x={1580} y={450} text="9" size={250} numeric weight={550} color={GOLD} scale={pop(f,e.frame('formula-lock'),.04)} role="formula-result"/>
   <Text x={420} y={730} text="上场次数" size={74} role="formula-n-label"/>
   <Text x={1000} y={730} text="单次成功概率" size={74} role="formula-p-label"/>
   <Text x={1580} y={730} text="预期次数" size={74} color={GOLD} role="formula-result-label"/>
  </g>:null;
 return <Frame config={config} foreground={foreground} overlay={<StrongRelease f={f} at={e.frame('formula-lock')} x={1530} y={450} id="formula-nine-release"/>}>
  <Backdrop id="area-stage"/>
  <Text x={960} y={130} text="预期成功次数" size={116} role="area-title"/>
  {f<formula+10?<g opacity={1-collapse}>
   <Text x={480+w/2} y={280} text={`${Math.round(n)}次上场`} size={80} role="area-count"/>
   <Text x={250} y={420} text="单次概率" size={72} role="area-rate-label"/>
   <Text x={250} y={570} text={`${Math.round(percent)}%`} size={100} numeric color={f>=e.frame('height-start')?GOLD:WHITE} role="area-rate"/>
   <g transform={`translate(${900+680*collapse} ${520-10*collapse}) scale(${1-.94*collapse}) translate(-900 -520)`}>
    {/* 量测只绑定定量矩形，避免把球体柔光的包围盒误当成面积主体。 */}
    <rect x={480} y={700-h} width={w} height={h} fill={GOLD} opacity={.88} data-m2v-role="area-model"/>
    {[1,2].map(k=><g key={k}>
     {w>280*k?<path d={`M${480+280*k} ${700-h}V700`} stroke={WHITE} strokeWidth={3} opacity={.65}/>:null}
     {h>120*k?<path d={`M480 ${700-120*k}H${480+w}`} stroke={WHITE} strokeWidth={3} opacity={.65}/>:null}
    </g>)}
    <path d={`M480 ${700-h}H${480+w}V700H480Z`} fill="none" stroke={GOLD} strokeWidth={3}/>
    <Attempt x={480+w-30} y={700-h-6} size={70} color={WHITE} groundY={700-h-6} frame={f} landAt={e.frame('height-lock')}/>
   </g>
   <Text x={1580} y={520} text={result} size={230} numeric weight={550} color={GOLD} scale={pop(f,e.frame('nine-lock'),.055)} role="area-result"/>
   <Text x={1580} y={755} text="预期次数" size={76} color={GOLD} role="area-result-label"/>
   <Text x={1730} y={825} text="乘法示意" size={23} color={MUTED} align="end"/>
   <Contact f={f} at={e.frame('width-lock')} x={480+w} y={700-h} strength={.5} kind="touch" seed="area-width"/>
   <Contact f={f} at={e.frame('height-lock')} x={480+w} y={700-h} strength={.65} kind="touch" seed="area-height"/>
  </g>:null}

 </Frame>;
}
