import {useEffect,useState} from 'react';
import type {CodeSceneProps} from 'm2v/code-scene';
import {MathFormula,ensureMathReady} from 'm2v/code-scene/math';
import Counter from 'm2v/style/components/counter';
import Burst from 'm2v/style/components/burst';
import {Frame,Text,Ball,GOLD,MUTED,progress,arrive,smooth,mix,useClock} from './shared';
import {compounded} from './model';

export default function Resolution(config:CodeSceneProps){
  const {f,e}=useClock(config);
  const [mathReady,setMathReady]=useState(false),[loadError,setLoadError]=useState<Error|null>(null);
  // 在字体资源完成后才挂载Frame并发出ready，首帧不能以系统字体代替公式字形。
  useEffect(()=>{let active=true;ensureMathReady().then(()=>{if(active)setMathReady(true);},error=>{if(active)setLoadError(error instanceof Error?error:new Error(String(error)));});return()=>{active=false;};},[]);
  if(loadError)throw loadError;
  if(!mathReady)return null;
  const base=e.frame('formula-base'),rate=e.frame('formula-rate'),land=e.frame('exponent-land');
  const answer=e.frame('answer-count'),lock=e.frame('answer-lock'),release=e.frame('answer-release'),closing=e.frame('closing-land');
  const transfer=smooth(progress(f,0,land));
  const formulaOpacity=arrive(progress(f,base,base+12))*(1-smooth(progress(f,release,release+18)));
  const answerOpacity=arrive(progress(f,answer,answer+8))*(1-smooth(progress(f,release,release+18)));
  const dot=progress(f,release,release+18),entry=arrive(progress(f,closing,closing+18));
  const titleScale=1+.035*Math.sin(Math.PI*progress(f,closing,closing+18));
  // phantom只保留排版尺寸：初始量、增长因子、指数依次公开，不在切换时跳字宽。
  const tex=f<rate?String.raw`100\phantom{\times(1.01)^{100}}`:f<land?String.raw`100\times(1.01)^{\phantom{100}}`:String.raw`100\times(1.01)^{100}`;
  return <Frame config={config} impacts={[{id:'answer-lock',preset:'finale',origin:{x:960,y:650},startFrame:lock}]} html={<>
    {f<release+18?<div style={{position:'absolute',left:450,top:335,lineHeight:1,whiteSpace:'nowrap',opacity:formulaOpacity}}>
      <MathFormula tex={tex} fontSize={110} color="#F3EDDC" role={f>=land?'formula':undefined}/>
    </div>:null}
    {f>=answer&&f<release+18?<div style={{position:'absolute',inset:0,opacity:answerOpacity}}>
      <Counter from={100} to={compounded(100)} progress={progress(f,answer,lock)} easing={arrive} decimals={2} x={960} y={670} size={250} color={GOLD}/>
    </div>:null}
  </>}>
    {/* 落点来自当前离线KaTeX字形的实际量测，避免接入上标时跳位。 */}
    {f<land?<text x={mix(1500,1222,transfer)} y={mix(350,378,transfer)-Math.sin(Math.PI*transfer)*80}
      textAnchor="middle" dominantBaseline="central" fontFamily="KaTeX_Main" fontWeight={400}
      fontSize={mix(72,93.17,transfer)} fill={GOLD} data-m2v-role="exponent-token">100</text>:null}
    {f>=answer&&f<release+18?<Text x={400} y={670} text="≈" size={110} numeric alpha={answerOpacity}/>:null}
    {f>=base&&f<release+18?<Text x={960} y={835} text="理想固定增速模型" size={50} color={MUTED} alpha={formulaOpacity} role="model-note"/>:null}
    <Burst origin={{x:1280,y:665}} progress={progress(f,lock,lock+36)} count={76} distance={360} size={4.5} rings={2} ringTravel={260} seed="equation-earned"/>
    {f>=release?<g data-m2v-role={f>=release+18?'closing-ball':undefined}>
      <Ball x={mix(1000,1540,smooth(dot))} y={mix(730,730,dot)-Math.sin(Math.PI*dot)*155} r={mix(10,16,dot)}/>
    </g>:null}
    {f>=closing?<g data-m2v-role="closing-title" opacity={entry} transform={`translate(960 500) scale(${titleScale}) translate(-960 -500)`}>
      <Text x={960} y={250} text="复利效应" size={70} color={GOLD}/>
      <Text x={960} y={420} text="让积累，" size={146}/>
      <Text x={960} y={660} text="参与下一次。" size={146}/>
    </g>:null}
  </Frame>;
}
