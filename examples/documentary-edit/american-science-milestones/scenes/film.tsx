import {useEffect, type CSSProperties} from 'react';
import {Chart} from '../src/code-scene/chart';
import {useMediaAsset} from '../src/code-scene/media';
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import ArchiveFrame from './components/archive-frame';
import ChapterText from './components/chapter-text';
import CreditBlock from './components/credit-block';
import {clamp01, ease, type ChapterPosition} from './components/kit';
import {BaseSequence, Network} from './mechanisms';

type Chapter = {id: string; year: string; title: string; caption: string; alias?: string; asset?: string; accent: string};
const full: CSSProperties = {position:'absolute', inset:0};
const archiveLayouts: Record<string, {
  image?: CSSProperties;
  media?: CSSProperties;
  shade?: string;
  background?: string;
  textColor?: string;
  position: ChapterPosition;
  copy?: CSSProperties;
}> = {
  'telephone': {
    image:{
      position:'absolute', inset:'85px 690px 85px 42px', mixBlendMode:'multiply',
      maskImage:'linear-gradient(90deg,transparent,#000 9%,#000 90%,transparent),linear-gradient(180deg,transparent,#000 3%,#000 96%,transparent)',
      maskComposite:'intersect',
    },
    media:{objectFit:'contain', filter:'grayscale(1) contrast(1.09) brightness(1.10)', transform:'none'},
    background:'radial-gradient(ellipse at 39% 44%,#f5ead8 0%,#e8d3b5 69%,#c3a179 100%)',
    textColor:'#30221a',
    position:'right', copy:{top:246, right:112, width:653, textShadow:'none'},
  },
  'flight': {
    media:{objectPosition:'50% 58%', filter:'sepia(.12) contrast(1.05)'},
    shade:'linear-gradient(0deg,#181611e3 0%,#1816119d 16%,transparent 51%)',
    position:'lower', copy:{bottom:102},
  },
  'trinity': {
    image:{position:'absolute', inset:'0 0 0 280px'},
    media:{objectPosition:'56% 100%', filter:'saturate(.75) contrast(1.02)', transform:'none'},
    shade:'linear-gradient(90deg,#201817 18%,#201817d9 30%,#20181755 46%,transparent 64%),linear-gradient(0deg,#201817,transparent 21%)',
    position:'upper', copy:{top:386, maxWidth:900},
  },
  'eniac': {
    media:{objectPosition:'50% 46%', filter:'sepia(.19) contrast(1.10)'},
    shade:'radial-gradient(ellipse 38% 36% at 16% 20%,#121510f0 24%,#121510a9 64%,transparent),linear-gradient(310deg,#11120d70,transparent 36%),linear-gradient(180deg,#1516127d,transparent 45%)',
    position:'upper', copy:{top:111},
  },
  'transistor': {
    image:{position:'absolute', inset:'0 625px 0 0'},
    media:{
      objectPosition:'50% 50%', filter:'saturate(.78) contrast(1.03)',
      transform:'scale(1.44)', transformOrigin:'43% 63%',
    },
    shade:'linear-gradient(90deg,transparent 48%,#211b1688 59%,#211b16 67%),radial-gradient(ellipse 32% 55% at 39% 60%,transparent 36%,#211b16ad 100%)',
    position:'right', copy:{top:416, right:101, width:606},
  },
  'moon-walk': {
    image:{position:'absolute', left:480, top:0, width:1440, height:1080},
    media:{
      objectFit:'contain', filter:'saturate(.88)', transform:'none',
      maskImage:'linear-gradient(90deg,transparent,#000 17%)',
    },
    shade:'linear-gradient(90deg,#121713 25%,#12171395 36%,transparent 53%),linear-gradient(180deg,#1217139e,transparent 24%)',
    position:'upper', copy:{top:134},
  },
  'genome': {
    image:{position:'absolute', inset:'0 0 0 500px'},
    media:{objectPosition:'57% 42%', filter:'saturate(.71) contrast(1.02)'},
    shade:'radial-gradient(ellipse 57% 48% at 86% 0%,#111b1dc9 10%,#111b1da3 57%,transparent),radial-gradient(ellipse 52% 105% at 5% 24%,#191e1b 49%,#191e1bee 67%,#191e1b90 83%,transparent),linear-gradient(90deg,#191e1b 22%,#191e1be0 34%,#191e1b6b 48%,transparent 61%)',
    position:'upper', copy:{top:208, maxWidth:760},
  },
};
const telephoneWaveValues = Array.from({length:80},(_,i)=>Math.sin(i*.37)*(.26+Math.sin(i*.11)**2*.64)*ease((79-i)/13));
const telephoneWave = {
  animation:false,
  grid:{left:0, right:0, top:10, bottom:10},
  xAxis:{show:false, type:'category' as const, data:Array.from({length:80},(_,i)=>i)},
  yAxis:{show:false, type:'value' as const, min:-1, max:1},
  series:[{width:13, color:'#ead0a4'}, {width:7, color:'#6c3d24'}].map((lineStyle)=>({
    type:'line' as const, smooth:true, symbol:'none',
    data:telephoneWaveValues,
    lineStyle,
  })),
};

function PhotoOrVideo({id, progress, style}: {id:string; progress:number; style?:CSSProperties}) {
  const {ready} = useSceneContext();
  const media = useMediaAsset(id);
  return <ArchiveFrame src={media.src} kind={media.kind} progress={progress} style={style} ready={ready}/>;
}

export default function Film(config: CodeSceneProps) {
  const {elapsedSeconds, ready} = useSceneContext();
  const chapter = config.props.chapter as Chapter;
  const hasMedia = chapter.asset !== undefined;

  useEffect(() => {
    if (!hasMedia) ready();
  }, [hasMedia, ready]);

  const progress = clamp01(elapsedSeconds*config.fps/config.durationInFrames);
  if (chapter.id === 'closing') {
    return <CreditBlock lines={config.props.creditLines as string[]}/>;
  }
  if (chapter.id === 'arpanet') {
    return <Network chapter={chapter} frame={elapsedSeconds*config.fps} events={config.eventFrames}/>;
  }
  if (!chapter.asset || !archiveLayouts[chapter.asset]) {
    throw new Error(`档案场 ${chapter.id} 缺少素材或构图`);
  }
  const layout = archiveLayouts[chapter.asset];
  const background = layout.background ?? (chapter.id === 'moon' ? '#121713' : chapter.id === 'genome' ? '#191e1b' : '#211b16');
  return <main style={{...full, overflow:'hidden', background}}>
    <div style={{...(layout.image ?? full), overflow:'hidden'}}>
      <PhotoOrVideo id={chapter.asset} progress={progress} style={layout.media}/>
    </div>
    {layout.shade && <div style={{...full, background:layout.shade}}/>}
    {chapter.id === 'telephone' && <>
      <div style={{
        position:'absolute', top:567, left:896, width:893, height:190,
        clipPath:`inset(0 ${100*(1-ease((elapsedSeconds-.20)/.72))}% 0 0)`,
      }}>
        <Chart option={telephoneWave} width={893} height={190}/>
      </div>
      <div style={{
        position:'absolute', left:884, top:651, width:18, height:18, borderRadius:'50%',
        background:'#deb683', border:'3px solid #654027', opacity:ease((elapsedSeconds-.13)/.18),
      }}/>
      <div style={{
        position:'absolute', left:1155, top:872, fontSize:36, color:'#684837',
      }}>早期装置复制品</div>
    </>}
    {chapter.id === 'moon' && <div style={{
      position:'absolute', left:124, bottom:104, fontSize:40, letterSpacing:3, color:'#fae9cc', textShadow:'0 2px 16px #000',
    }}>NASA</div>}
    <ChapterText {...chapter} position={layout.position} style={layout.copy} textColor={layout.textColor}/>
    {chapter.id === 'genome' && <BaseSequence progress={ease((elapsedSeconds-1.05)/.40)}/>}
  </main>;
}
