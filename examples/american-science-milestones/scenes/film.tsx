/** 档案先行的无声纪录短片。所有位移、显影与示意粒子都由帧时钟求值。 */
import {useEffect, useRef} from 'react';
import {motion, useMediaAsset, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {Mechanism} from './mechanisms';

type Chapter = {id: string; year: string; title: string; english: string; caption: string;
  note: string; credit: string; asset?: string; layout: string; accent: string};
const clamp = (v: number) => Math.max(0, Math.min(1, v));
const ease = (v: number) => {const t = clamp(v); return t * t * (3 - 2 * t);};

/** 钩子顺序固定；只解析正式导入的素材。 */
function useArchives() {
  return {
    telegraph: useMediaAsset('telegraph'), telephone: useMediaAsset('telephone'),
    flight: useMediaAsset('flight'), trinity: useMediaAsset('trinity'),
    eniac: useMediaAsset('eniac'), transistor: useMediaAsset('transistor'),
    moon: useMediaAsset('moon'), arpanet: useMediaAsset('arpanet'),
    genome: useMediaAsset('genome'),
  };
}

function Archive({asset, progress, inset = false, ready}: {
  asset: ReturnType<typeof useMediaAsset>; progress: number; inset?: boolean; ready: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const el = video.current;
    if (el) {el.muted = true; void el.play().catch(() => undefined);}
  }, []);
  const fit = Math.min(1, 1030 / asset.width, 680 / asset.height);
  const style = {width: inset ? asset.width * fit : '100%', height: inset ? asset.height * fit : '100%', objectFit: (inset ? 'contain' : 'cover') as 'contain' | 'cover',
    transform: `scale(${1.015 + progress * .055}) translateX(${progress * -12}px)`,
    filter: 'saturate(.68) contrast(1.06)'};
  return asset.kind === 'video'
    ? <video ref={video} src={asset.src} muted playsInline preload="auto" onCanPlay={ready} style={style}/>
    : <img src={asset.src} onLoad={ready} style={style}/>;
}

function Finish({chapters, t}: {chapters: Chapter[]; t: number}) {
  const credits = t >= 7;
  return <div style={{position:'absolute',inset:0,padding:'150px 110px',
    background:'radial-gradient(ellipse at 75% 30%,#1b343c 0%,#080f14 60%)'}}>
    <div style={{fontSize:19,letterSpacing:7,color:'#9eabb0'}}>1776 — 2022 / SELECTED MILESTONES</div>
    <h1 style={{fontSize:64,fontWeight:500,margin:'30px 0 20px',letterSpacing:3}}>
      {credits ? '每一次突破，都有来路。' : '改变世界的，是不断延伸的探索。'}</h1>
    <div style={{fontSize:28,color:'#bdc6c8',lineHeight:1.8}}>
      {credits ? '档案与实物：美国国会图书馆 · 美国陆军 · NASA · NHGRI' : '美国主导的代表成果，建立在全球知识与国际合作之上。'}
    </div>
    <div style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:'36px 26px',marginTop:76}}>
      {chapters.map((c,i)=><div key={c.id} style={{borderTop:'1px solid #56636a',paddingTop:18,
        opacity:ease((t-i*.12)/.7)}}>
        <div style={{fontSize:18,color:'#b39b76',letterSpacing:2}}>{c.year}</div>
        <div style={{fontSize:27,marginTop:12}}>{c.title}</div>
      </div>)}
    </div>
    <div style={{marginTop:64,fontSize:21,lineHeight:1.9,color:'#b5bfc2'}}>
      {credits ? <><div>晶体管：Unitronic / CC BY-SA 3.0　·　ARPANET地图：UCLA与BBN / CC BY-SA 4.0</div>
        <div>照片裁切与调色；原图及改编部分遵循对应许可。详细来源与许可见 SOURCES.md。</div></>
        : <><div>计算机、互联网与人工智能是长期累积的共同成果。</div>
          <div>本片选取十个里程碑，不将其整体归为一国独创。</div></>}
    </div>
  </div>;
}

export default function Film(config: CodeSceneProps) {
  const clock = useSceneContext();
  const archives = useArchives();
  const c = config.props.chapter as Chapter;
  const all = (config.props.chapters ?? []) as Chapter[];
  const t = clock.elapsedSeconds;
  const p = clamp(t / (config.durationInFrames / config.fps));
  const intro = c.id === 'opening', ending = c.id === 'closing';
  const asset = archives[(intro ? 'flight' : c.asset) as keyof typeof archives];
  const index = Number(config.props.index ?? 0);
  const textOpacity = ease((t - .35) / .65);
  // 无素材场景也必须显式就绪；图像/视频场景由解码事件就绪。
  useEffect(() => {if (!asset || ending) clock.ready();}, [asset, ending]);
  const inset = c.layout === 'plate' || c.layout === 'split';
  return <div style={{position:'relative',width:config.width,height:config.height,overflow:'hidden',
    background:'#080d11',color:'#f4eee2'}}>
    {!ending && asset && <div style={inset
      ? {position:'absolute',left:770,top:140,width:1030,height:680,overflow:'hidden',display:'flex',alignItems:'center',justifyContent:'center'}
      : {position:'absolute',inset:0,overflow:'hidden'}}>
      <Archive key={c.id} asset={asset} progress={p} inset={inset} ready={clock.ready}/>
    </div>}
    {!ending && !inset && <div style={{position:'absolute',inset:0,
      background:intro ? 'linear-gradient(90deg,rgba(4,9,13,.88),rgba(4,9,13,.05)),linear-gradient(0deg,#080d11 0%,transparent 45%)'
        : 'linear-gradient(90deg,rgba(4,9,13,.90),rgba(4,9,13,.3) 53%,transparent 85%),linear-gradient(0deg,#080d11 0%,transparent 50%)'}}/>}
    {!ending && <div style={{position:'absolute',inset:0,
      background:'radial-gradient(ellipse at center,transparent 35%,rgba(0,0,0,.32))'}}/>}
    {intro ? <motion.div animate={{opacity:ease((t+.3)/1)}}
      transition={{duration:.18,ease:'easeOut'}}
      style={{position:'absolute',left:110,top:210}}>
      <div style={{fontSize:23,letterSpacing:9,color:'#d8b589'}}>1776：故事的起点</div>
      <h1 style={{fontSize:100,fontWeight:500,lineHeight:1.3,letterSpacing:6,margin:'32px 0'}}>从电报<br/>到大模型</h1>
      <div style={{fontSize:29,color:'#c7c8c1',letterSpacing:4}}>美国科学与技术 · 十个里程碑</div>
      <div style={{fontSize:19,color:'#a9b5b9',marginTop:40}}>SELECTED MILESTONES / A SILENT DOCUMENTARY</div>
    </motion.div> : ending ? <Finish chapters={all} t={t}/> : <>
      <div style={{position:'absolute',left:110,top:145,color:c.accent,letterSpacing:6,fontSize:21}}>
        {String(index).padStart(2,'0')} / 10　—　{c.english}</div>
      <div style={{position:'absolute',left:104,top:225,fontSize:c.year.length>6?108:150,
        lineHeight:1,fontWeight:300,letterSpacing:-5,color:c.accent,opacity:.85,
        transform:`translateY(${(1-ease(t/1.2))*20}px)`}}>{c.year}</div>
      <motion.div animate={{opacity:textOpacity, y:(1-textOpacity)*16}}
        transition={{duration:.18,ease:'easeOut'}}
        style={{position:'absolute',left:110,top:430}}>
        <h1 style={{fontSize:c.title.length>7?55:64,fontWeight:500,letterSpacing:2,margin:'0 0 30px'}}>{c.title}</h1>
        <div style={{width:inset?610:780,fontSize:29,lineHeight:1.8,color:'#deded5'}}>{c.caption}</div>
        <div style={{marginTop:24,fontSize:21,color:'#aab9bf',maxWidth:660,lineHeight:1.7}}>{c.note}</div>
      </motion.div>
      <Mechanism kind={c.id} t={t} accent={c.accent}/>
      <div style={{position:'absolute',left:110,top:835,fontSize:17,letterSpacing:1,color:'#a9b6bb'}}>{c.credit}</div>
    </>}
    {!ending && <>
      <div style={{position:'absolute',left:110,top:60,fontSize:16,letterSpacing:5,color:'#c3c9c6'}}>A HISTORY OF POSSIBILITY</div>
      <div style={{position:'absolute',right:110,top:60,fontSize:16,letterSpacing:3,color:'#c3c9c6'}}>美国科学与技术</div>
      <div style={{position:'absolute',left:110,right:110,top:910,height:1,background:'#b5ac962d'}}>
        <div style={{width:`${intro?p*2:2+(index-1)*9.5+p*9.5}%`,height:1,background:'#d8b589'}}/>
      </div>
      <div style={{position:'absolute',left:110,top:942,color:'#7e9099',fontSize:16,letterSpacing:4}}>1776</div>
      <div style={{position:'absolute',right:110,top:942,color:'#7e9099',fontSize:16,letterSpacing:4}}>2022</div>
    </>}
    {/* 稀疏细线以帧为种子变化，避免随机噪声破坏同帧确定性与文字清晰度。 */}
    <svg width="1920" height="1080" style={{position:'absolute',inset:0,pointerEvents:'none',opacity:.045}}>
      {Array.from({length:36},(_,i)=><line key={i} x1="0" x2="1920" y1={(i*31+Math.floor(t*12)%7)%1080} y2={(i*31+Math.floor(t*12)%7)%1080} stroke="#fff" strokeWidth=".5"/>)}
    </svg>
  </div>;
}
