/** 档案先行的无声纪录短片。所有位移、显影与示意粒子都由帧时钟求值。 */
import {useEffect, useRef, type CSSProperties, type ReactNode} from 'react';
import {motion, useMediaAsset, useSceneContext, type CodeSceneProps, type MediaAsset} from 'm2v/code-scene';
import {ArpanetNodes, GenomeHelix, LLMNetwork, MorsePulse, TelephoneWave, TransistorDiagram} from './mechanisms';

type Chapter = {
  id: string; year: string; title: string; english: string; caption: string;
  note: string; treatment: string; accent: string; asset?: string;
};

const clamp = (value: number) => Math.max(0, Math.min(1, value));
const shadow: CSSProperties = {textShadow: '0 2px 26px rgba(0,0,0,.68)'};

/** 无素材场景只需在挂载后声明一次就绪。 */
function useReadyOnce(ready: () => void) {
  const done = useRef(false);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    ready();
  }, [ready]);
}

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

/** 图像与视频共用同一取用口；视频在挂载后按静音连续播放，由录制时钟定位。 */
function Archive({asset, style, ready}: {asset: MediaAsset; style: CSSProperties; ready: () => void}) {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const element = video.current;
    if (asset.kind === 'video' && element) {element.muted = true; void element.play().catch(() => undefined);}
  }, [asset]);
  return asset.kind === 'video'
    ? <video ref={video} src={asset.src} muted playsInline preload="auto" onCanPlay={ready} style={style}/>
    : <img src={asset.src} onLoad={ready} style={style}/>;
}

function Frame({children}: {children: ReactNode}) {
  return <div style={{position:'absolute',inset:0,overflow:'hidden',background:'#070b0f',
    color:'#f4eee2'}}>{children}</div>;
}

/** 开场的三秒：首飞档案缓慢推移，底部的年代线走完全片跨度。 */
function Opening({asset, t, ready}: {asset: MediaAsset; t: number; ready: () => void}) {
  const p = clamp(t / 3);
  return <Frame>
    <Archive asset={asset} ready={ready} style={{position:'absolute',left:'-3%',top:'-10%',
      width:'106%',height:'120%',objectFit:'cover',objectPosition:'60% 45%',
      transform:`scale(${1.03 + p * .05}) translateX(${-10 + p * 24}px)`,
      filter:'saturate(.7) contrast(1.06)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(90deg,rgba(4,8,12,.94) 0%,rgba(4,8,12,.62) 38%,rgba(4,8,12,.08) 72%)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(0deg,rgba(4,8,12,.92) 0%,rgba(4,8,12,0) 48%)'}}/>
    <motion.div initial={{opacity:0}} animate={{opacity:1}} transition={{duration:.5}}
      style={{position:'absolute',left:120,top:112,width:2,height:82,background:'#d3b38a'}}/>
    <div style={{position:'absolute',left:120,top:236,
      opacity:clamp(t / .55),transform:`translateY(${(1 - clamp(t / .55)) * 14}px)`}}>
      <div style={{fontSize:21,letterSpacing:9,color:'#d8b589',...shadow}}>1776 — 2022</div>
      <h1 style={{fontSize:108,fontWeight:500,lineHeight:1.12,letterSpacing:4,
        margin:'30px 0 22px',...shadow}}>从电报<br/>到大模型</h1>
      <div style={{fontSize:31,color:'#d6d7cf',letterSpacing:3,...shadow}}>美国科学与技术 · 十个里程碑</div>
      <div style={{fontSize:17,color:'#a9b5b9',letterSpacing:6,marginTop:30,...shadow}}>
        SELECTED MILESTONES / A SILENT DOCUMENTARY</div>
    </div>
    <div style={{position:'absolute',left:120,top:792,width:780,height:1,background:'#ffffff22'}}/>
    <div style={{position:'absolute',left:120,top:791,width:780 * p,height:2,background:'#d3b38a'}}/>
    <div style={{position:'absolute',left:120 + 780 * p - 4,top:788,width:9,height:9,
      borderRadius:'50%',background:'#ffe8b8',boxShadow:'0 0 20px #d3b38a'}}/>
    <div style={{position:'absolute',left:120,top:810,fontSize:16,letterSpacing:4,color:'#8fa0a8'}}>1776</div>
    <div style={{position:'absolute',left:858,top:810,fontSize:16,letterSpacing:4,color:'#8fa0a8'}}>2022</div>
  </Frame>;
}

/** 电报：竖幅实物占据右侧，左侧以年号与信号带建立“电码穿过距离”的动势。 */
function Telegraph({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 4);
  return <Frame>
    <div style={{position:'absolute',inset:0,
      background:'radial-gradient(ellipse at 78% 40%,#152126 0%,#070b0f 65%)'}}/>
    <div style={{position:'absolute',right:110,top:80,width:592,height:920,overflow:'hidden',
      border:'1px solid #ffffff18',boxShadow:'0 40px 120px rgba(0,0,0,.55)'}}>
      <Archive asset={asset} ready={ready} style={{width:'100%',height:'100%',objectFit:'cover',
        objectPosition:'50% 38%',transform:`scale(${1.02 + p * .055})`,
        filter:'saturate(.6) contrast(1.08) sepia(.06)'}}/>
      <div style={{position:'absolute',inset:0,
        background:'linear-gradient(180deg,rgba(7,11,15,.05) 40%,rgba(7,11,15,.5))'}}/>
    </div>
    <div style={{position:'absolute',left:120,top:64,fontSize:188,fontWeight:300,lineHeight:1,
      letterSpacing:-8,color:chapter.accent,opacity:.88,...shadow}}>1844</div>
    <div style={{position:'absolute',left:124,top:270,fontSize:19,letterSpacing:7,
      color:'#9eabb0'}}>{chapter.english}</div>
    <h1 style={{position:'absolute',left:120,top:312,fontSize:68,fontWeight:500,letterSpacing:3,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:426,width:920,fontSize:38,lineHeight:1.7,
      color:'#deded5',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:520,width:900,fontSize:31,lineHeight:1.7,
      color:'#aab9bf',...shadow}}>{chapter.note}</div>
    <MorsePulse t={t} accent={chapter.accent}/>
  </Frame>;
}

/** 电话：档案被压暗成背景，清晰实物与波形共同解释“声音转为电信号”。 */
function Telephone({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 4);
  return <Frame>
    <Archive asset={asset} ready={ready} style={{position:'absolute',inset:'-12%',width:'124%',
      height:'124%',objectFit:'cover',filter:'blur(30px) brightness(.28) saturate(.45)',opacity:.6}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(90deg,rgba(7,11,15,.9),rgba(7,11,15,.5) 55%,rgba(7,11,15,.25))'}}/>
    <div style={{position:'absolute',left:1060,top:180,width:640,height:492,overflow:'hidden',
      border:'1px solid #ffffff20',boxShadow:'0 30px 100px rgba(0,0,0,.5)'}}>
      <Archive asset={asset} ready={ready} style={{width:'100%',height:'100%',objectFit:'cover',
        transform:`scale(${1.04 + p * .04})`,filter:'saturate(.7) contrast(1.06)'}}/>
      <div style={{position:'absolute',left:0,right:0,top:`${(p * 1.25 % 1) * 100}%`,height:1.5,
        background:chapter.accent,opacity:.55}}/>
      <div style={{position:'absolute',left:14,bottom:12,fontSize:20,color:'#e2dccbcc',
        letterSpacing:1,background:'#0b1216cc',padding:'5px 10px',borderRadius:4}}>1875 年实验装置复制品</div>
    </div>
    <div style={{position:'absolute',left:120,top:150,fontSize:22,letterSpacing:7,
      color:chapter.accent}}>{chapter.year}</div>
    <h1 style={{position:'absolute',left:120,top:196,fontSize:72,fontWeight:500,letterSpacing:3,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:330,width:820,fontSize:38,lineHeight:1.7,
      color:'#deded5',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:434,width:820,fontSize:31,lineHeight:1.7,
      color:'#aab9bf',...shadow}}>{chapter.note}</div>
    <TelephoneWave accent={chapter.accent}/>
  </Frame>;
}

/** 飞机：全幅档案横向掠过，文字压在沙地上方的暗部。 */
function Flight({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 8);
  return <Frame>
    <Archive asset={asset} ready={ready} style={{position:'absolute',left:-220 - p * 180,top:-250,
      width:'126%',height:'auto',filter:'saturate(.7) contrast(1.06)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(0deg,rgba(4,8,12,.95) 0%,rgba(4,8,12,.6) 25%,rgba(4,8,12,0) 56%)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(90deg,rgba(4,8,12,.55) 0%,rgba(4,8,12,0) 48%)'}}/>
    <div style={{position:'absolute',left:120,top:586,fontSize:24,letterSpacing:7,
      color:chapter.accent,...shadow}}>{chapter.year} · {chapter.english}</div>
    <h1 style={{position:'absolute',left:120,top:624,fontSize:76,fontWeight:500,letterSpacing:3,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:738,width:940,fontSize:38,lineHeight:1.6,
      color:'#e8e5dc',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:806,width:900,fontSize:27,lineHeight:1.6,
      color:'#b8c1c3',...shadow}}>{chapter.note}</div>
  </Frame>;
}

/** 原子弹：竖幅档案占满右半，左侧留白让说明与警示句分开呼吸。 */
function Trinity({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 4);
  return <Frame>
    <div style={{position:'absolute',inset:0,
      background:'radial-gradient(ellipse at 78% 30%,#2a1a12 0%,#080b10 68%)'}}/>
    <div style={{position:'absolute',right:0,top:0,width:900,height:1080,overflow:'hidden'}}>
      <Archive asset={asset} ready={ready} style={{width:'100%',height:'100%',objectFit:'cover',
        objectPosition:'50% 34%',transform:`scale(${1.04 + p * .07})`,
        filter:'saturate(.82) contrast(1.04)'}}/>
      <div style={{position:'absolute',inset:0,
        background:'linear-gradient(90deg,rgba(8,11,16,1) 0%,rgba(8,11,16,.3) 18%,rgba(8,11,16,0) 40%)'}}/>
    </div>
    <div style={{position:'absolute',left:120,top:140,fontSize:23,letterSpacing:8,
      color:chapter.accent}}>{chapter.year} · 新墨西哥州</div>
    <h1 style={{position:'absolute',left:120,top:190,fontSize:74,fontWeight:500,letterSpacing:3,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:318,width:780,fontSize:38,lineHeight:1.7,
      color:'#e6e1d6',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:420,width:760,fontSize:32,lineHeight:1.7,
      color:'#d2b49a',...shadow}}>{chapter.note}</div>
    <div style={{position:'absolute',left:120,top:560,width:80,height:2,
      background:chapter.accent,opacity:.7}}/>
    <div style={{position:'absolute',left:120,top:592,fontSize:18,letterSpacing:4,
      color:'#8fa0a8'}}>16 JULY 1945 / TRINITY</div>
  </Frame>;
}

/** ENIAC：宽幅档案反向横移，右下角指示灯按帧闪烁，强调机器的持续运转。 */
function Eniac({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 4);
  return <Frame>
    <Archive asset={asset} ready={ready} style={{position:'absolute',left:-180 - p * 240,top:-300,
      width:'126%',height:'auto',filter:'saturate(.66) contrast(1.07)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(0deg,rgba(4,8,12,.96) 0%,rgba(4,8,12,.55) 28%,rgba(4,8,12,0) 58%)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(90deg,rgba(4,8,12,.5) 0%,rgba(4,8,12,0) 46%)'}}/>
    <div style={{position:'absolute',right:130,top:590,display:'flex',gap:12}}>
      {Array.from({length:10},(_,i)=><div key={i} style={{width:7,height:7,borderRadius:'50%',
        background:chapter.accent,opacity:.25 + .7 * Math.sin(t * 3 + i * .9) ** 2,
        boxShadow:`0 0 12px ${chapter.accent}`}}/>)}
    </div>
    <div style={{position:'absolute',left:120,top:590,fontSize:23,letterSpacing:7,
      color:chapter.accent,...shadow}}>{chapter.year} · {chapter.english}</div>
    <h1 style={{position:'absolute',left:120,top:628,fontSize:74,fontWeight:500,letterSpacing:3,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:738,width:960,fontSize:38,lineHeight:1.6,
      color:'#e8e5dc',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:812,width:920,fontSize:31,lineHeight:1.6,
      color:'#b8c1c3',...shadow}}>{chapter.note}</div>
  </Frame>;
}

/** 晶体管：实物面板与截面示意并置，文字收在面板下方。 */
function Transistor({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 4);
  return <Frame>
    <div style={{position:'absolute',inset:0,
      background:'radial-gradient(ellipse at 26% 32%,#152528 0%,#070b0f 66%)'}}/>
    <div style={{position:'absolute',left:110,top:110,width:820,height:615,overflow:'hidden',
      border:'1px solid #ffffff18',boxShadow:'0 40px 110px rgba(0,0,0,.55)'}}>
      <Archive asset={asset} ready={ready} style={{width:'100%',height:'100%',objectFit:'cover',
        transform:`scale(${1.03 + p * .05})`,filter:'saturate(.68) contrast(1.06)'}}/>
      <div style={{position:'absolute',left:14,bottom:12,fontSize:20,color:'#e2dccbcc',
        letterSpacing:1,background:'#0b1216cc',padding:'5px 10px',borderRadius:4}}>博物馆实物照</div>
    </div>
    <TransistorDiagram t={t} accent={chapter.accent}/>
    <div style={{position:'absolute',left:1060,top:664,width:700,fontSize:26,lineHeight:1.6,
      color:'#aab9bf'}}>{chapter.note}</div>
    <div style={{position:'absolute',left:120,top:748,fontSize:58,fontWeight:500,lineHeight:1.1,
      letterSpacing:2,...shadow}}>
      <span style={{fontSize:24,letterSpacing:6,color:chapter.accent,marginRight:22,
        verticalAlign:'middle'}}>{chapter.year}</span>{chapter.title}
    </div>
    <div style={{position:'absolute',left:124,top:834,width:940,fontSize:32,lineHeight:1.35,
      color:'#deded5',...shadow}}>{chapter.caption}</div>
  </Frame>;
}

/** 登月：NASA 连续影像原速播放，不再叠加二次运动。 */
function Moon({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 8);
  return <Frame>
    <Archive asset={asset} ready={ready} style={{position:'absolute',inset:0,width:'100%',
      height:'100%',objectFit:'cover',transform:`scale(${1.01 + p * .025})`,
      filter:'saturate(.72) contrast(1.05)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(0deg,rgba(3,6,9,.94) 0%,rgba(3,6,9,.55) 26%,rgba(3,6,9,0) 56%)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(90deg,rgba(3,6,9,.48) 0%,rgba(3,6,9,0) 46%)'}}/>
    <div style={{position:'absolute',right:110,top:78,textAlign:'right'}}>
      <div style={{fontSize:18,letterSpacing:8,color:'#c8d9dc'}}>APOLLO 11</div>
      <div style={{fontSize:15,letterSpacing:4,color:'#8fa0a8',marginTop:8}}>07.20.1969 / LUNAR SURFACE</div>
      <div style={{width:150,height:1,background:'#c8d9dc55',marginTop:14,marginLeft:'auto'}}/>
    </div>
    <div style={{position:'absolute',left:120,top:586,fontSize:23,letterSpacing:7,
      color:chapter.accent,...shadow}}>{chapter.year} · 月面</div>
    <h1 style={{position:'absolute',left:120,top:624,fontSize:78,fontWeight:500,letterSpacing:3,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:744,width:940,fontSize:38,lineHeight:1.6,
      color:'#e8e5dc',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:812,width:900,fontSize:31,lineHeight:1.6,
      color:'#b8c1c3',...shadow}}>{chapter.note}</div>
  </Frame>;
}

/** ARPANET：档案图保留原画框，四节点与报文点作为叠加层单独说明。 */
function Arpanet({chapter, asset, t, ready}: SceneProps) {
  return <Frame>
    <div style={{position:'absolute',inset:0,
      background:'radial-gradient(ellipse at 74% 44%,#12222a 0%,#070b0f 66%)'}}/>
    <div style={{position:'absolute',right:100,top:150,width:820,height:560,
      border:'1px solid #ffffff16',background:'#0b1216'}}>
      <div style={{position:'absolute',left:10,top:9,width:800,height:542,overflow:'hidden'}}>
        <Archive asset={asset} ready={ready} style={{width:'100%',height:'100%',objectFit:'contain',
          filter:'saturate(.55) contrast(1.1) brightness(.86)'}}/>
      </div>
    </div>
    <div style={{position:'absolute',left:120,top:150,fontSize:22,letterSpacing:7,
      color:chapter.accent}}>{chapter.year}</div>
    <h1 style={{position:'absolute',left:120,top:196,fontSize:72,fontWeight:500,letterSpacing:4,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:310,fontSize:19,letterSpacing:6,
      color:'#9eabb0'}}>{chapter.english}</div>
    <div style={{position:'absolute',left:124,top:358,width:760,fontSize:38,lineHeight:1.7,
      color:'#deded5',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:466,width:760,fontSize:31,lineHeight:1.7,
      color:'#aab9bf',...shadow}}>{chapter.note}</div>
    <ArpanetNodes t={t} accent={chapter.accent}/>
  </Frame>;
}

/** 基因组：真实工作照保持全幅，双螺旋只作结构示意叠在右侧。 */
function Genome({chapter, asset, t, ready}: SceneProps) {
  const p = clamp(t / 4);
  return <Frame>
    <Archive asset={asset} ready={ready} style={{position:'absolute',inset:0,width:'100%',
      height:'100%',objectFit:'cover',objectPosition:'44% 50%',
      transform:`scale(${1.03 + p * .02}) translateY(${-8 + p * 16}px)`,
      filter:'saturate(.64) contrast(1.06)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(90deg,rgba(4,8,12,.94) 0%,rgba(4,8,12,.6) 34%,rgba(4,8,12,.05) 66%)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(0deg,rgba(4,8,12,.7) 0%,rgba(4,8,12,0) 40%)'}}/>
    <div style={{position:'absolute',inset:0,
      background:'linear-gradient(270deg,rgba(4,8,12,.58) 0%,rgba(4,8,12,.16) 28%,rgba(4,8,12,0) 52%)'}}/>
    <GenomeHelix t={t} accent={chapter.accent}/>
    <div style={{position:'absolute',left:120,top:168,fontSize:22,letterSpacing:7,
      color:chapter.accent}}>{chapter.year}</div>
    <h1 style={{position:'absolute',left:120,top:214,fontSize:72,fontWeight:500,letterSpacing:2,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:346,width:800,fontSize:38,lineHeight:1.7,
      color:'#deded5',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:462,width:820,fontSize:30,lineHeight:1.7,
      color:'#aab9bf',...shadow}}>{chapter.note}</div>
  </Frame>;
}

/** 大语言模型：抽象网络铺满右侧，左侧保留剪短的贡献边界说明。 */
function LanguageModel({chapter, t, ready}: {chapter: Chapter; t: number; ready: () => void}) {
  useReadyOnce(ready);
  return <Frame>
    <div style={{position:'absolute',inset:0,
      background:'radial-gradient(ellipse at 72% 38%,#10202a 0%,#070b0f 68%)'}}/>
    <LLMNetwork t={t} accent={chapter.accent}/>
    <div style={{position:'absolute',left:120,top:656,fontSize:22,letterSpacing:7,
      color:chapter.accent}}>{chapter.year}</div>
    <h1 style={{position:'absolute',left:120,top:700,fontSize:68,fontWeight:500,letterSpacing:3,
      margin:0,...shadow}}>{chapter.title}</h1>
    <div style={{position:'absolute',left:124,top:780,width:800,fontSize:36,lineHeight:1.5,
      color:'#deded5',...shadow}}>{chapter.caption}</div>
    <div style={{position:'absolute',left:124,top:846,width:820,fontSize:26,lineHeight:1.4,
      color:'#aab9bf',...shadow}}>{chapter.note}</div>
    <div style={{position:'absolute',right:110,top:812,fontSize:24,letterSpacing:1,
      color:'#8fa0a8'}}>原理示意 · 非真实模型运行记录</div>
  </Frame>;
}

/** 片尾：主旨、年代刻度与唯一一份署名共用同一画面。 */
function Closing({chapters, t, ready}: {chapters: Chapter[]; t: number; ready: () => void}) {
  useReadyOnce(ready);
  const p = clamp(t / 5);
  const endYear = (value: string) => {
    const years = value.match(/\d{4}/g);
    return years ? Number(years[years.length - 1]) : 2022;
  };
  return <Frame>
    <div style={{position:'absolute',inset:0,
      background:'radial-gradient(ellipse at 70% 20%,#15242b 0%,#070b0f 62%)'}}/>
    <motion.div initial={{opacity:0}} animate={{opacity:1}} transition={{duration:.5}}
      style={{position:'absolute',left:120,top:86,width:82,height:2,background:'#d3b38a'}}/>
    <div style={{position:'absolute',left:120,top:130,
      opacity:clamp(t / .6),transform:`translateY(${(1 - clamp(t / .6)) * 12}px)`}}>
      <div style={{fontSize:76,fontWeight:500,letterSpacing:2,...shadow}}>每一次突破，都有来路。</div>
      <div style={{fontSize:32,color:'#bdc6c8',marginTop:24,letterSpacing:1,...shadow}}>
        美国主导的代表成果，建立在全球知识与国际合作之上。</div>
    </div>
    <div style={{position:'absolute',left:120,top:400,width:1680,height:1,background:'#ffffff18'}}/>
    <div style={{position:'absolute',left:120,top:399,width:1680 * p,height:2,
      background:'#d3b38a',opacity:.8}}/>
    {chapters.map((chapter, i) => {
      const x = 120 + 1680 * (endYear(chapter.year) - 1776) / (2022 - 1776);
      const lit = clamp(p * 1.1 - i * .02) > 0;
      return <div key={chapter.id} style={{position:'absolute',left:x,top:393,width:1.5,height:15,
        background:lit ? '#d3b38a' : '#ffffff25',opacity:lit ? .9 : .35}}/>;
    })}
    <div style={{position:'absolute',left:120 + 1680 * p - 4,top:396,width:9,height:9,
      borderRadius:'50%',background:'#ffe8b8',boxShadow:'0 0 20px #d3b38a'}}/>
    <div style={{position:'absolute',left:120,top:416,fontSize:15,letterSpacing:3,color:'#7f9199'}}>1776</div>
    <div style={{position:'absolute',left:1760,top:416,fontSize:15,letterSpacing:3,color:'#7f9199'}}>2022</div>
    <div style={{position:'absolute',left:120,top:548}}>
      <div style={{fontSize:18,letterSpacing:5,color:'#8fa0a8',marginBottom:14}}>影像与许可</div>
      <div style={{fontSize:32,lineHeight:1.6,color:'#aeb8bb'}}>
        影像：John T. Daniels · Jack W. Aeby · 美国陆军 · NASA · NHGRI · 佚名</div>
      <div style={{fontSize:32,lineHeight:1.6,color:'#aeb8bb'}}>
        晶体管照片：Unitronic，CC BY-SA 3.0（裁切与调色）</div>
      <div style={{fontSize:32,lineHeight:1.6,color:'#aeb8bb'}}>
        ARPANET 地图：UCLA 与 BBN，CC BY-SA 4.0（调色）</div>
      <div style={{fontSize:32,lineHeight:1.6,color:'#aeb8bb'}}>
        其余档案为公有领域。本片改编部分按 CC BY-SA 4.0 提供。</div>
    </div>
  </Frame>;
}

type SceneProps = {chapter: Chapter; asset: MediaAsset; t: number; ready: () => void};

export default function Film(config: CodeSceneProps) {
  const clock = useSceneContext();
  const archives = useArchives();
  const chapter = config.props.chapter as Chapter;
  const chapters = (config.props.chapters ?? []) as Chapter[];
  const t = clock.elapsedSeconds;
  const asset = chapter.asset ? archives[chapter.asset as keyof typeof archives] : undefined;
  // 图像/视频场景由解码事件就绪；无素材场景在各自组件里声明一次。
  if (chapter.id === 'opening' && asset) return <Opening asset={asset} t={t} ready={clock.ready}/>;
  if (chapter.id === 'closing') return <Closing chapters={chapters} t={t} ready={clock.ready}/>;
  if (chapter.id === 'llm') return <LanguageModel chapter={chapter} t={t} ready={clock.ready}/>;
  if (!asset) return null;
  const props = {chapter, asset, t, ready: clock.ready};
  switch (chapter.id) {
    case 'telegraph': return <Telegraph {...props}/>;
    case 'telephone': return <Telephone {...props}/>;
    case 'flight': return <Flight {...props}/>;
    case 'trinity': return <Trinity {...props}/>;
    case 'eniac': return <Eniac {...props}/>;
    case 'transistor': return <Transistor {...props}/>;
    case 'moon': return <Moon {...props}/>;
    case 'arpanet': return <Arpanet {...props}/>;
    case 'genome': return <Genome {...props}/>;
    default: return null;
  }
}
