import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import {useMediaAsset} from '../src/code-scene/media';
import {clamp01} from './components/kit';

type TelegraphChapter = {id: string; title: string; caption: string; year: string; asset: string};

// 按 1024×357 原扫描的纸缘坐标取景。下边的缺口保留原先的不规则走向。
const paperEdge = [
  [38,116], [42,117], [45,114], [50,116], [56,113], [59,114], [65,109], [85,109],
  [90,112], [93,109], [108,108], [217,108], [220,106], [355,103], [630,102], [1024,105],
  [1024,265], [970,265], [935,263], [900,264], [886,262], [744,263], [587,261],
  [300,262], [293,264], [175,264], [169,263], [162,264], [153,262], [143,259],
  [138,250], [137,244], [132,239], [123,238], [122,235], [118,235], [113,254],
  [110,254], [106,265], [90,268], [80,266], [75,268], [38,268], [35,268],
  [35,256], [38,251], [37,224], [39,219], [39,207], [40,206], [39,197], [40,196],
  [40,186], [37,176], [38,173], [36,170], [37,152], [36,151], [35,120], [36,117],
] as const;
const paperSilhouette = `polygon(${paperEdge
  .map(([x,y])=>`${(100*x/1024).toFixed(2)}% ${(100*y/357).toFixed(2)}%`)
  .join(', ')})`;

export default function Telegraph({props, fps, eventFrames}: CodeSceneProps) {
  const {elapsedSeconds, globalSeconds, ready} = useSceneContext();
  const chapter = props.chapter as TelegraphChapter;
  if (chapter.asset !== 'morse-tape') throw new Error('电报纸带构图需要原件展览扫描');
  const tape = useMediaAsset(chapter.asset);
  const opening = chapter.id === 'opening';
  const drift = globalSeconds * 8;
  const keyFrame = eventFrames?.key;
  const kick = keyFrame === undefined ? 0 : 1-clamp01(Math.abs(elapsedSeconds*fps-keyFrame)/10);

  return <main style={{
    position:'absolute', inset:0, color:'#f7eddb', overflow:'hidden',
    background:'radial-gradient(ellipse at 44% 42%, #3d3527, #161812 82%)',
  }}>
    <div style={{
      position:'absolute', top:247, left:95-drift, width:1965,
      filter:'drop-shadow(0 25px 20px #100e0ca8)',
    }}>
      <img src={tape.src} onLoad={ready} alt="" style={{
        display:'block', width:'100%', clipPath:paperSilhouette,
        filter:`brightness(${1+.035*kick})`,
      }}/>
    </div>
    <div style={{position:'absolute', top:110, left:128}}>
      {!opening && <div style={{fontSize:42, letterSpacing:3, color:'#efd0a5', marginBottom:4}}>{chapter.year}</div>}
      <h1 style={{fontSize:opening?120:91, fontWeight:650, lineHeight:1.1, letterSpacing:2, margin:0}}>{chapter.title}</h1>
    </div>
    <div style={{position:'absolute', bottom:105, left:132, fontSize:opening?44:53, color:'#f3e2c8'}}>{chapter.caption}</div>
    {!opening && <>
      <div style={{
        position:'absolute', left:587-drift, top:759, width:4, height:30, background:'#cba773',
      }}/>
      <div style={{
        position:'absolute', display:'flex', alignItems:'center', gap:20, left:564-drift, top:792, height:54,
      }}>
        <span style={{fontSize:52, fontWeight:640, color:'#f5d7a4', marginRight:8}}>W</span>
        {[22,66,66].map((width,index) => {
          const frame = eventFrames?.[`pulse-${index+1}`];
          const active = frame !== undefined && elapsedSeconds*fps >= frame;
          return <i key={index} style={{width, height:20, borderRadius:4, background:active?'#fbe1ad':'#8d7051'}}/>;
        })}
        <span style={{fontSize:47, fontWeight:550, color:'#f2d8b0', marginLeft:16}}>现行国际摩尔斯码示意</span>
      </div>
    </>}
    <div style={{position:'absolute', right:147, bottom:104, fontSize:38, color:'#e8d1b3'}}>美国国会图书馆</div>
  </main>;
}
