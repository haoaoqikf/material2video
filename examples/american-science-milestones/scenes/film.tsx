/** 十项科技里程碑的档案蒙太奇：画面变化来自题材本身，不使用逐页信息卡模板。 */
import {useEffect, useRef, type CSSProperties} from 'react';
import {Chart, motion, useMediaAsset, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {Mechanism} from './mechanisms';

type Chapter = {id: string; year: string; title: string; caption: string; asset?: string; accent: string};
const clamp = (v: number) => Math.max(0, Math.min(1, v));
const ease = (v: number) => {const t=clamp(v);return t*t*(3-2*t);};
const telephoneWave = {animation:false,grid:{left:30,right:20,top:20,bottom:20},xAxis:{show:false,type:'category',data:Array.from({length:80},(_,i)=>i)},yAxis:{show:false,type:'value',min:-1,max:1},series:[{type:'line',data:Array.from({length:80},(_,i)=>Math.sin(i*.37)*(.3+Math.sin(i*.11)**2*.55)),smooth:true,symbol:'none',lineStyle:{color:'#d9c29e',width:3},areaStyle:{color:'rgba(217,194,158,.12)'}}]};

function useArchives() {
  return {
    telegraph: useMediaAsset('telegraph'), telephone: useMediaAsset('telephone'),
    flight: useMediaAsset('flight'), trinity: useMediaAsset('trinity'),
    eniac: useMediaAsset('eniac'), transistor: useMediaAsset('transistor'),
    moon: useMediaAsset('moon'), arpanet: useMediaAsset('arpanet'), genome: useMediaAsset('genome'),
  };
}

function Archive({asset,progress,ready,style}:{asset:ReturnType<typeof useMediaAsset>;progress:number;ready:()=>void;style?:CSSProperties}) {
  const video=useRef<HTMLVideoElement>(null);
  useEffect(()=>{const el=video.current;if(el){el.muted=true;void el.play().catch(()=>undefined);}},[]);
  const base:CSSProperties={width:'100%',height:'100%',objectFit:'cover',transform:`scale(${1.025+progress*.08}) translate3d(${progress*-18}px,0,0)`,filter:'saturate(.76) contrast(1.08)',...style};
  return asset.kind==='video'
    ? <video ref={video} src={asset.src} muted playsInline preload="auto" onCanPlay={ready} style={base}/>
    : <img src={asset.src} onLoad={ready} style={base}/>;
}

function Credits({t}:{t:number}) {
  const a=ease((t-.2)/.8);
  return <div style={{position:'absolute',inset:0,background:'radial-gradient(ellipse at 75% 30%,#233c43 0%,#0a1116 62%)',display:'flex',alignItems:'center',padding:'0 120px'}}>
    <div style={{width:'100%',opacity:a,transform:`translateY(${(1-a)*16}px)`}}>
      <div style={{fontSize:24,letterSpacing:7,color:'#b8c2c1'}}>1844 — 2022</div>
      <h1 style={{fontSize:67,fontWeight:450,letterSpacing:2,margin:'18px 0 10px'}}>每一次突破，都有来路。</h1>
      <p style={{fontSize:31,lineHeight:1.35,color:'#d3d9d5',margin:'0 0 18px'}}>知识在接力，探索仍在继续。</p>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:56,fontSize:30,lineHeight:1.42,color:'#c3cdcf',maxWidth:1680}}>
        <div>
          <div>档案影像：John T. Daniels、Jack W. Aeby、美国陆军、NASA、NHGRI、佚名（公有领域）</div>
          <div style={{marginTop:10}}>晶体管照片：Unitronic</div>
          <div>CC BY-SA 3.0 · creativecommons.org/licenses/by-sa/3.0/</div>
          <div>commons.wikimedia.org/wiki/File:1st-Transistor.jpg</div>
          <div>改动：裁切、调色</div>
        </div>
        <div>
          <div>ARPANET 地图：UCLA、BBN</div>
          <div>CC BY-SA 4.0</div>
          <div>commons.wikimedia.org/wiki/File:ARPANET_1970_Map.png</div>
          <div>改动：调色</div>
          <div style={{marginTop:10}}>本片依 CC BY-SA 4.0 共享</div>
          <div>creativecommons.org/licenses/by-sa/4.0/</div>
        </div>
      </div>
    </div>
  </div>;
}

function ChapterText({c,t,position='lower'}:{c:Chapter;t:number;position?:'lower'|'upper'|'upperNarrow'|'right'|'vertical'}) {
  const a=ease((t-.18)/.55), duration=1;
  const pos:Record<string,CSSProperties>={
    lower:{left:116,bottom:155,maxWidth:1120}, upper:{left:120,top:118,maxWidth:1050}, upperNarrow:{left:120,top:118,maxWidth:680},
    right:{right:120,top:240,width:690}, vertical:{right:135,top:185,width:650},
  };
  return <motion.div animate={{opacity:a,y:(1-a)*20}} transition={{duration,ease:'easeOut'}} style={{position:'absolute',...pos[position],textShadow:'0 3px 22px #000'}}>
    <div style={{fontSize:31,letterSpacing:5,color:c.accent,marginBottom:16}}>{c.year}</div>
    <h1 style={{fontSize:c.title.length>9?68:82,lineHeight:1.12,fontWeight:500,letterSpacing:1,margin:'0 0 18px'}}>{c.title}</h1>
    <p style={{fontSize:46,lineHeight:1.45,fontWeight:400,color:'#f0eee7',margin:0}}>{c.caption}</p>
  </motion.div>;
}

export default function Film(config:CodeSceneProps) {
  const clock=useSceneContext(), archives=useArchives();
  const c=config.props.chapter as Chapter, t=clock.elapsedSeconds;
  const p=clamp(t/(config.durationInFrames/config.fps));
  const isOpen=c.id==='opening', isClose=c.id==='closing';
  const asset=archives[(isOpen?'flight':c.asset) as keyof typeof archives];
  useEffect(()=>{if(!asset||isClose)clock.ready();},[asset,isClose]);
  if(isClose)return <div style={{position:'relative',width:config.width,height:config.height,overflow:'hidden',background:'#080e13',color:'#f5f1e8'}}><Credits t={t}/></div>;
  const mode:Record<string,string>={telegraph:'wire',telephone:'apparatus',flight:'sky',trinity:'flash',eniac:'machine',transistor:'silicon',moon:'moon',arpanet:'map',genome:'sequence',llm:'language'};
  const special=c.id==='telephone'||c.id==='arpanet';
  const position:Record<string,'lower'|'upper'|'upperNarrow'|'right'|'vertical'>={telegraph:'upper',telephone:'right',flight:'lower',trinity:'right',eniac:'lower',transistor:'vertical',moon:'lower',arpanet:'upperNarrow',genome:'lower',llm:'upper'};
  return <div style={{position:'relative',width:config.width,height:config.height,overflow:'hidden',background:'#080d11',color:'#f5f1e8'}}>
    {asset&&<div style={{position:'absolute',inset:0,overflow:'hidden'}}>
      <Archive asset={asset} progress={p} ready={clock.ready} style={special?{opacity:.27,filter:'blur(12px) saturate(.5)',transform:'scale(1.12)'}:undefined}/>
    </div>}
    {special&&asset&&<div style={{position:'absolute',left:c.id==='telephone'?120:850,top:145,width:c.id==='telephone'?660:900,height:650,overflow:'hidden',filter:'drop-shadow(0 24px 55px #000b)'}}>
      <Archive asset={asset} progress={p} ready={clock.ready} style={{objectFit:'contain',filter:'saturate(.9) contrast(1.08)'}}/>
    </div>}
    {c.id==='telephone'&&<div style={{position:'absolute',left:735,top:320,width:1050,height:360,opacity:.9}}><Chart option={telephoneWave} width={1050} height={360}/></div>}
    <div style={{position:'absolute',inset:0,background:isOpen?'linear-gradient(90deg,#071018c9,#07101820 78%),linear-gradient(0deg,#05090ee8,transparent 55%)':'linear-gradient(0deg,#05090ff0,transparent 70%),linear-gradient(90deg,#05090f80,transparent 72%)'}}/>
    {isOpen?<>
      <div style={{position:'absolute',left:135,top:160,fontSize:26,letterSpacing:8,color:'#dcc49c'}}>一段知识接力</div>
      <motion.h1 animate={{opacity:ease((t+.1)/.5),x:(1-ease((t+.1)/.5))*-24}} style={{position:'absolute',left:126,top:270,fontSize:116,lineHeight:1.08,fontWeight:500,letterSpacing:3,margin:0,textShadow:'0 5px 36px #000'}}>从电报<br/>到大模型</motion.h1>
      <div style={{position:'absolute',left:138,top:590,fontSize:42,color:'#e1e1d8'}}>美国主导或参与的十项节点 · 全球知识的接力</div>
    </>:<>
      {c.id!=='telephone'&&<Mechanism kind={mode[c.id]??c.id} t={t} progress={p} accent={c.accent}/>}
      <ChapterText c={c} t={t} position={position[c.id]}/>
    </>}
    {c.id==='flight'&&<div style={{position:'absolute',right:118,top:118,fontSize:27,letterSpacing:4,color:'#fff',textShadow:'0 2px 20px #000'}}>KITTY HAWK · 1903</div>}
    {c.id==='moon'&&<div style={{position:'absolute',right:100,top:90,fontSize:26,letterSpacing:5,color:'#f5f2e9'}}>APOLLO 11 / ARCHIVE FILM</div>}
  </div>;
}
