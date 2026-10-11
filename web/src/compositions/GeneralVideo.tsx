import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame } from 'remotion';
import { FinancialTimeSeries, type FinancialTimeSeriesProps } from './FinancialTimeSeries';
import { M2VCompositionV4, type M2VCompositionV4Props } from './M2VCompositionV4';
import type { M2VCodeScene } from '@/code-scene';
import { createSceneRandom } from '@/code-scene';
import { ACTIVE_CODE_SCENES } from '../../.gen/active-scenes';

export type GeneralScene = {
  id: string; type: 'graphic'|'financial-timeseries'|'article-narrative'|'code';
  data?: Record<string, unknown>; durationInFrames: number; startFrame: number; endFrame: number;
  transitionFrames: number; narration?: string; subtitleCues?: Array<{startFrame:number;endFrame:number;text:string}>;
  renderer?: {kind:'code';module:string}; embeddedProps?: Record<string, unknown>; embeddedComposition?: string;
};
export type GeneralVideoProps = {schemaVersion:1;fps:30;width:1080;height:1920;durationInFrames:number;compiledScenes:GeneralScene[];title?:string;subtitleCues?:Array<{startFrame:number;endFrame:number;text:string}>};

/** Incoming scene fades over the still-visible outgoing scene. */
export function sceneOpacityAtFrame(scene: GeneralScene, frame: number): number {
  const localFrame = frame - scene.startFrame;
  const overlap = scene.transitionFrames;
  if (!overlap || localFrame >= overlap) return 1;
  if (overlap <= 1) return 1;
  return Math.max(0, Math.min(1, localFrame / (overlap - 1)));
}

export function activeSubtitleCues(cues: GeneralVideoProps['subtitleCues'], frame: number) {
  return (cues ?? []).filter(cue => cue.startFrame <= frame && frame < cue.endFrame);
}

function GraphicScene({scene}: {scene:GeneralScene}): React.ReactElement {
  const data=scene.data??{};
  const lines=Array.isArray(data.lines)?data.lines:[];
  const nodes=Array.isArray(data.nodes)?data.nodes as Array<{id:string;label:string}>:[];
  const links=Array.isArray(data.links)?data.links as Array<{from:string;to:string;label:string}>:[];
  const values=Array.isArray(data.values)?data.values as Array<{label:string;value:number}>:[];
  const maximum=Math.max(1,...values.map(item=>item.value));
  return <AbsoluteFill style={{justifyContent:'center',padding:'150px 112px',background:'#111720',color:'#f3f4f6',fontFamily:'M2V Sans, sans-serif'}}>
    {typeof data.kicker==='string'&&<div style={{fontSize:30,color:'#f7c85b',marginBottom:36}}>{data.kicker}</div>}
    <div style={{fontSize:72,lineHeight:1.2,fontWeight:700}}>{String(data.title??data.text??'')}</div>
    {typeof data.body==='string'&&<div style={{fontSize:38,lineHeight:1.5,marginTop:48,color:'#c8d0da'}}>{data.body}</div>}
    {lines.map((line,index)=><div key={index} style={{fontSize:36,lineHeight:1.5,marginTop:24,color:'#c8d0da'}}>{String(line)}</div>)}
    {nodes.length>0&&<div style={{display:'flex',flexWrap:'wrap',alignItems:'center',gap:20,marginTop:48}}>
      {nodes.map((node,index)=><React.Fragment key={node.id}>
        {index>0&&<span aria-hidden="true" style={{fontSize:42,color:'#f7c85b'}}>→</span>}
        <div style={{padding:'20px 26px',border:'2px solid #526174',borderRadius:18,background:'#1c2734',fontSize:30,fontWeight:600}}>{node.label}</div>
      </React.Fragment>)}
    </div>}
    {links.map((link,index)=><div key={`${link.from}-${link.to}-${index}`} style={{fontSize:26,color:'#f7c85b',marginTop:16}}>
      {nodes.find(node=>node.id===link.from)?.label} → {nodes.find(node=>node.id===link.to)?.label}：{link.label}
    </div>)}
    {values.length>0&&<div style={{display:'grid',gap:20,marginTop:44}}>
      {values.map((item,index)=><div key={`${item.label}-${index}`} style={{display:'grid',gridTemplateColumns:'220px 1fr 100px',alignItems:'center',gap:18,fontSize:28}}>
        <span>{item.label}</span><div style={{height:22,background:'#263443',borderRadius:12,overflow:'hidden'}}>
          <div style={{width:`${Math.max(0,Math.min(100,item.value/maximum*100))}%`,height:'100%',background:'#f7c85b'}}/>
        </div><span style={{textAlign:'right',fontVariantNumeric:'tabular-nums'}}>{item.value}</span>
      </div>)}
    </div>}
  </AbsoluteFill>;
}

function CodeScene({scene,fps,width,height}: {scene:GeneralScene;fps:number;width:number;height:number}): React.ReactElement {
  const module=scene.renderer?.module??'';
  const Component=ACTIVE_CODE_SCENES[module] as M2VCodeScene<Record<string,unknown>>|undefined;
  if(!Component) throw new Error(`通用场景 ${scene.id} 的代码模块未注册：${module}`);
  const frame=useCurrentFrame();
  const progress=scene.durationInFrames<=1?1:frame/(scene.durationInFrames-1);
  return <Component world={{id:scene.id,claim:String(scene.data?.claim??''),metaphor:'',objects:[]}}
    stage={{id:scene.id,data:scene.data??{},startFrame:0,endFrame:scene.durationInFrames,progress}}
    objectStates={{}} scene={{id:scene.id,type:'code',data:scene.data??{},durationInFrames:scene.durationInFrames}}
    frame={frame} localFrame={frame} progress={progress} fps={fps} canvas={{width,height}} theme={{theme:'dark'}}
    beats={{current:null,progress:0,completed:[],estimated:true,active:null,plan:[]}}
    motion={{phase:progress<1?'change':'settle',camera:{kind:'none',progress:1,focus:'',x:0,y:0,scale:1,velocity:0},continuity:null}}
    random={createSceneRandom(scene.id)}/>;
}

function SceneContent({scene,fps,width,height}: {scene:GeneralScene;fps:number;width:number;height:number}): React.ReactElement {
  if(scene.type==='financial-timeseries') return <FinancialTimeSeries {...(scene.embeddedProps as FinancialTimeSeriesProps)}/>;
  if(scene.type==='article-narrative') return <M2VCompositionV4 {...(scene.embeddedProps as M2VCompositionV4Props)}/>;
  if(scene.type==='code') return <CodeScene scene={scene} fps={fps} width={width} height={height}/>;
  return <GraphicScene scene={scene}/>;
}

export const GeneralVideo: React.FC<GeneralVideoProps> = (props) => {
  const frame=useCurrentFrame();
  const cues=activeSubtitleCues(props.subtitleCues, frame);
  return <AbsoluteFill style={{background:'#111720'}}>
    {props.compiledScenes.map(scene=><Sequence key={scene.id} from={scene.startFrame} durationInFrames={scene.durationInFrames} layout="none">
      <AbsoluteFill style={{opacity:sceneOpacityAtFrame(scene,frame)}}>
        <SceneContent scene={scene} fps={props.fps} width={props.width} height={props.height}/>
      </AbsoluteFill>
    </Sequence>)}
    {cues.length>0&&<div style={{position:'absolute',left:100,right:100,bottom:260,textAlign:'center',fontSize:46,fontWeight:600,color:'#fff',textShadow:'0 2px 8px #000',pointerEvents:'none'}}>
      {cues.map((cue,index)=><div key={`${cue.startFrame}-${index}`}>{cue.text}</div>)}
    </div>}
  </AbsoluteFill>;
};
