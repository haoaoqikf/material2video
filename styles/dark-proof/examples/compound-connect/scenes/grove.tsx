import {useSceneContext,type CodeSceneProps} from 'm2v/code-scene';
import Impact from 'm2v/style/components/impact';
import {mixColor} from 'm2v/style/components/kit';
import {Frame,Tree,Seed,Soil,GOLD,WHITE,type Props} from './visual';
import {MOTHER,CHILD,THIRD,arrive,progress,mix,flight,growth,type Beats} from './model';

const offspring=[{x:1850,y:770,scale:.48,delay:0,pod:[220,-335]},
  {x:2260,y:770,scale:.52,delay:16,pod:[-164,-292]},
  {x:2680,y:770,scale:.43,delay:32,pod:[91,-397]}];

/** 从已验证的第三株延续三个可见来源，拉远只改变取景，不重置主体。 */
export function GroveVisual({f,b}:{f:number;b:Beats}){
  const reveal=arrive(progress(f,1140,1230)),zoom=mix(1,.60,reveal),cx=mix(960,1280,reveal);
  return <g transform={`translate(960 770) scale(${zoom}) translate(${-cx} -770)`}>
    <Soil x={1500} width={3000}/>
    <Tree {...MOTHER} fruit={1} departed role="grove-mother-tree"/>
    <Tree {...CHILD} fruit={1} departed/>
    <Tree {...THIRD} tone={mixColor(GOLD,WHITE,progress(f,b['third-ready'],b['third-fruit']))}/>
    {offspring.map((tree,i)=>{
      const start=b['third-fruit']+22+tree.delay,land=start+30;
      const from={x:THIRD.x+tree.pod[0]*THIRD.scale,y:THIRD.y+tree.pod[1]*THIRD.scale};
      const point=flight(f,start,land,from,tree);
      return <g key={i}>
        {f<start?<Seed {...from} scale={THIRD.scale*.8} opacity={arrive(progress(f,b['third-fruit'],b['third-fruit']+20))}/>:null}
        {f>=start&&f<land+20?<Seed {...point} scale={THIRD.scale*.8*(1-progress(f,land+6,land+20))}
          angle={progress(f,start,land)*100}/>:null}
        <Tree {...tree} grow={growth(f,land+6,1302)} gold/>
      </g>;
    })}
  </g>;
}
export default function Grove(config:CodeSceneProps){
  const {globalFrame}=useSceneContext();const f=Math.round(globalFrame);const {beats:b}=config.props as unknown as Props;
  return <Frame config={config} impact={f>=b['grove-reveal']&&f<b['grove-reveal']+66?
    <Impact frame={f} width={1920} height={1080} maskBottom={830} totalFrames={2040}
      events={[{id:'grove',preset:'reveal',origin:{x:1160,y:625},startFrame:b['grove-reveal']}]}/>:null}>
    <GroveVisual f={f} b={b}/>
  </Frame>;
}
