/** 十项科技里程碑的档案蒙太奇：画面变化来自题材本身，不使用逐页信息卡模板。 */
import {useEffect, useRef, type CSSProperties} from 'react';
import {Chart, motion, useMediaAsset, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {Mechanism} from './mechanisms';

type Chapter = {id: string; year: string; title: string; caption: string; alias?: string; creditDetails?: string; asset?: string; accent: string};
const clamp = (v: number) => Math.max(0, Math.min(1, v));
const ease = (v: number) => {const t=clamp(v);return t*t*(3-2*t);};
const telephoneWave = {animation:false,grid:{left:30,right:20,top:20,bottom:20},xAxis:{show:false,type:'category',data:Array.from({length:80},(_,i)=>i)},yAxis:{show:false,type:'value',min:-1,max:1},series:[{type:'line',data:Array.from({length:80},(_,i)=>Math.sin(i*.37)*(.3+Math.sin(i*.11)**2*.55)),smooth:true,symbol:'none',lineStyle:{color:'#d9c29e',width:3},areaStyle:{color:'rgba(217,194,158,.12)'}}]};

function useArchives() {
  return {
    telegraph: useMediaAsset('telegraph'), telephone: useMediaAsset('telephone'),
    flight: useMediaAsset('flight'), trinity: useMediaAsset('trinity'),
    eniac: useMediaAsset('eniac'), transistor: useMediaAsset('transistor'),
    moon: useMediaAsset('moon'), arpanet: useMediaAsset('arpanet'), genome: useMediaAsset('genome'),
    chatgptIcon: useMediaAsset('chatgpt-icon'),
  };
}

function Archive({asset,progress,ready,style,startOffsetSeconds=0}:{asset:ReturnType<typeof useMediaAsset>;progress:number;ready:()=>void;style?:CSSProperties;startOffsetSeconds?:number}) {
  const video=useRef<HTMLVideoElement>(null);
  useEffect(()=>{const el=video.current;if(el){el.muted=true;const seekAndPlay=()=>{if(startOffsetSeconds>0)el.currentTime=Math.min(startOffsetSeconds,Math.max(0,el.duration-.1));void el.play().catch(()=>undefined);};el.addEventListener('loadedmetadata',seekAndPlay,{once:true});if(el.readyState>=1)seekAndPlay();return()=>el.removeEventListener('loadedmetadata',seekAndPlay);}},[startOffsetSeconds]);
  const base:CSSProperties={width:'100%',height:'100%',objectFit:'cover',transform:`scale(${1.025+progress*.08}) translate3d(${progress*-18}px,0,0)`,filter:'saturate(.76) contrast(1.08)',...style};
  return asset.kind==='video'
    ? <video ref={video} src={asset.src} muted playsInline preload="auto" onCanPlay={ready} style={base}/>
    : <img src={asset.src} onLoad={ready} style={base}/>;
}

function Credits() {
  return <div style={{position:'absolute',inset:0,background:'radial-gradient(ellipse at 75% 30%,#233c43 0%,#0a1116 62%)',display:'flex',alignItems:'center',padding:'0 120px'}}>
    <div style={{width:'100%',textAlign:'center',textShadow:'0 2px 16px #000'}}>
      <div style={{fontSize:41,lineHeight:1.55,fontWeight:500,color:'#f0eee7'}}>晶体管《1st Transistor》 Unitronic｜CC BY-SA 3.0｜裁切、调色</div>
      <div style={{fontSize:41,lineHeight:1.55,fontWeight:500,color:'#e1e7e6'}}>阿帕网地图 UCLA、BBN｜CC BY-SA 4.0｜裁切、调色｜本片 CC BY-SA 4.0</div>
    </div>
  </div>;
}

function ChatGPTDemo({asset,progress,t}:{asset:ReturnType<typeof useMediaAsset>;progress:number;t:number}) {
  const answer='全球研究积累，推动语言生成走向大众。';
  const visible=Math.min(answer.length,Math.max(0,Math.floor((progress-.28)/.52*answer.length)));
  return <div style={{position:'absolute',right:106,top:160,width:800,height:760,borderRadius:34,background:'linear-gradient(145deg,#192923,#101815 72%)',border:'1px solid #ffffff24',boxShadow:'0 30px 100px #0009',overflow:'hidden',transform:`translateY(${Math.sin(t*1.2)*4}px)`}}>
    <div style={{height:96,display:'flex',alignItems:'center',padding:'0 32px',borderBottom:'1px solid #ffffff20',gap:20}}>
      <img src={asset.src} style={{width:54,height:54,objectFit:'contain'}}/>
      <div><div style={{fontSize:31,fontWeight:600}}>ChatGPT <span style={{fontSize:25,color:'#c7d2cc'}}> / OpenAI</span></div><div style={{fontSize:19,color:'#b8c7be',marginTop:2}}>示意界面</div></div>
      <div style={{marginLeft:'auto',fontSize:18,color:'#cbd7d0',border:'1px solid #ffffff35',borderRadius:18,padding:'7px 13px'}}>界面重绘 · 非真实对话</div>
    </div>
    <div style={{padding:'54px 42px',fontSize:31,lineHeight:1.55,color:'#f4f3eb'}}>
      <div style={{marginLeft:130,marginBottom:44,padding:'18px 24px',borderRadius:24,background:'#ffffff14'}}>科学知识如何走向大众？</div>
      <div style={{display:'flex',gap:20,alignItems:'flex-start'}}>
        <img src={asset.src} style={{width:42,height:42,objectFit:'contain',flex:'0 0 auto'}}/>
        <div>{answer.slice(0,visible)}<span style={{opacity:visible<answer.length&&Math.sin(t*8)>0?.9:.0,color:'#b9e4c3'}}>▍</span></div>
      </div>
      <div style={{marginTop:42,display:'flex',alignItems:'center',gap:12,color:'#b8d8c0',fontSize:22}}><span style={{width:9,height:9,borderRadius:'50%',background:'#b8d8c0',boxShadow:'0 0 14px #b8d8c0'}}/>语言模型研究持续积累</div>
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
      {c.alias&&<div style={{fontSize:26,letterSpacing:3,color:'#c3cdcf',margin:'-8px 0 12px'}}>{c.alias}</div>}
    <p style={{fontSize:46,lineHeight:1.45,fontWeight:400,color:'#f0eee7',margin:0}}>{c.caption}</p>
  </motion.div>;
}

export default function Film(config:CodeSceneProps) {
  const clock=useSceneContext(), archives=useArchives();
  const c=config.props.chapter as Chapter, t=clock.elapsedSeconds;
  const p=clamp(t/(config.durationInFrames/config.fps));
  const isOpen=c.id==='opening', isClose=c.id==='closing';
  const asset=archives[c.asset as keyof typeof archives];
  const chatgptIcon=archives.chatgptIcon;
  useEffect(()=>{if(!asset||isClose)clock.ready();},[asset,isClose]);
  if(isClose)return <div style={{position:'relative',width:config.width,height:config.height,overflow:'hidden',background:'#080e13',color:'#f5f1e8'}}><Credits/></div>;
  const mode:Record<string,string>={telegraph:'wire',telephone:'apparatus',flight:'sky',trinity:'flash',eniac:'machine',transistor:'silicon',moon:'moon',arpanet:'map',genome:'sequence',llm:'language'};
  const special=c.id==='telephone'||c.id==='arpanet';
  const position:Record<string,'lower'|'upper'|'upperNarrow'|'right'|'vertical'>={telegraph:'upper',telephone:'right',flight:'lower',trinity:'right',eniac:'lower',transistor:'vertical',moon:'lower',arpanet:'upperNarrow',genome:'lower',llm:'upper'};
  if(c.id==='llm')return <div style={{position:'relative',width:config.width,height:config.height,overflow:'hidden',background:'radial-gradient(ellipse at 83% 46%,#244537 0%,#0a1210 48%,#070c10 100%)',color:'#f5f1e8'}}>
    <div style={{position:'absolute',inset:0,background:'linear-gradient(90deg,#070c10 0%,#070c10db 34%,transparent 72%)'}}/>
    <div style={{position:'absolute',left:126,top:215,width:730,textShadow:'0 3px 22px #000'}}>
      <div style={{fontSize:30,letterSpacing:5,color:c.accent,marginBottom:20}}>2020—2022</div>
      <h1 style={{fontSize:78,lineHeight:1.1,fontWeight:500,margin:'0 0 25px'}}>大语言模型</h1>
      <p style={{fontSize:43,lineHeight:1.45,margin:0,color:'#f0eee7'}}>全球研究积累<br/>推动语言生成走向大众。</p>
      <div style={{marginTop:38,fontSize:25,color:'#bdd4c8'}}>从基础研究到日常对话</div>
    </div>
    <ChatGPTDemo asset={chatgptIcon} progress={p} t={t}/>
    <div style={{position:'absolute',left:126,bottom:68,fontSize:19,color:'#aebdb4'}}>全球研究与产业协作 · ChatGPT 为具体产品实例</div>
  </div>;
  return <div style={{position:'relative',width:config.width,height:config.height,overflow:'hidden',background:'#080d11',color:'#f5f1e8'}}>
    {asset&&<div style={{position:'absolute',inset:0,overflow:'hidden'}}>
      <Archive asset={asset} progress={p} ready={clock.ready} startOffsetSeconds={isOpen?4:0} style={special?{opacity:.27,filter:'blur(12px) saturate(.5)',transform:'scale(1.12)'}:undefined}/>
    </div>}
    {special&&asset&&<div style={{position:'absolute',left:c.id==='telephone'?120:850,top:145,width:c.id==='telephone'?660:900,height:650,overflow:'hidden',filter:'drop-shadow(0 24px 55px #000b)'}}>
      <Archive asset={asset} progress={p} ready={clock.ready} style={{objectFit:'contain',filter:'saturate(.9) contrast(1.08)'}}/>
    </div>}
    {c.id==='telephone'&&<div style={{position:'absolute',left:735,top:320,width:1050,height:360,opacity:.9}}><Chart option={telephoneWave} width={1050} height={360}/></div>}
    <div style={{position:'absolute',inset:0,background:isOpen?'linear-gradient(90deg,#071018c9,#07101820 78%),linear-gradient(0deg,#05090ee8,transparent 55%)':'linear-gradient(0deg,#05090ff0,transparent 70%),linear-gradient(90deg,#05090f80,transparent 72%)'}}/>
    {isOpen?<>
      <div style={{position:'absolute',left:135,top:160,fontSize:26,letterSpacing:5,color:'#dcc49c'}}>十项里程碑 · 一段知识接力</div>
      <h1 style={{position:'absolute',left:126,top:270,fontSize:116,lineHeight:1.08,fontWeight:500,letterSpacing:3,margin:0,textShadow:'0 5px 36px #000'}}>美国科学<br/>高光时刻</h1>
      <div style={{position:'absolute',left:138,top:590,fontSize:42,color:'#e1e1d8'}}>美国主导或参与的十项科技节点</div>
    </>:<>
      {c.id!=='telephone'&&<Mechanism kind={mode[c.id]??c.id} t={t} progress={p} accent={c.accent}/>}
      <ChapterText c={c} t={t} position={position[c.id]}/>
    </>}
  </div>;
}
