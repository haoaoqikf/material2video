import {useSceneContext,type CodeSceneProps} from 'm2v/code-scene';
import Burst from 'm2v/style/components/burst';
import {Frame,Tree,Seed,Soil,Text,GOLD,type Props} from './visual';
import {progress,arrive,growth,flight,pulse,podAt} from './model';
import {LearningDiagram} from './learning';

export default function Closing(config:CodeSceneProps){
  const {globalFrame}=useSceneContext();const f=Math.round(globalFrame);const {beats:b}=config.props as unknown as Props;
  const enter=arrive(progress(f,1688,1696));
  const seed=flight(f,1710,1770,{x:960,y:265},{x:480,y:770});
  const tree=growth(f,1788,1855),title=arrive(progress(f,b['title-arrive'],b['title-arrive']+28));
  const next=flight(f,1950,1990,podAt({x:480,y:770,scale:.65}),{x:1080,y:770});
  return <Frame config={config}><g data-m2v-role="closing-content" style={{willChange:'transform'}}>
    {f<1690?<g opacity={1-arrive(progress(f,1680,1688))}><LearningDiagram f={1679} b={b}/></g>:null}
    <g opacity={enter}>
      <Soil/>
      {f<1810?<Seed {...seed} scale={1-progress(f,1788,1810)} angle={progress(f,1710,1770)*90}/>:null}
      <Tree x={480} y={770} scale={.65} grow={tree} fruit={arrive(progress(f,1880,1900))} departed={f>=1950}/>
      {f>=1950&&f<2005?<Seed {...next} scale={.52*(1-progress(f,1990,2005))} angle={progress(f,1950,1990)*100}/>:null}
      <Tree x={1080} y={770} scale={.4} grow={growth(f,1990,2035)} gold/>
      <Burst origin={{x:480,y:770}} progress={progress(f,1770,1796)} count={20} distance={90} rings={0} seed="closing-contact"/>
      <g opacity={title} transform={`translate(960 240) scale(${.94+.06*title+(pulse(f,b['title-arrive']+28)-1)}) translate(-960 -240)`}>
        <Text x={960} y={240} size={170} color={GOLD} weight={750} role="closing-title">复利效应</Text>
      </g>
    </g>
  </g></Frame>;
}
