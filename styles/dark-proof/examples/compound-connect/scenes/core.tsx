import {useSceneContext,type CodeSceneProps} from 'm2v/code-scene';
import Burst from 'm2v/style/components/burst';
import Impact from 'm2v/style/components/impact';
import {mixColor} from 'm2v/style/components/kit';
import {Frame,Tree,Seed,Soil,Text,GOLD,WHITE,type Props} from './visual';
import {MOTHER,CHILD,THIRD,podAt,flight,groveState,progress,arrive,pulse} from './model';
/** 完整试制：母株结种→同一颗种子落地成树→新增树再次结种。 */
export default function Core(config:CodeSceneProps){
  const {globalFrame}=useSceneContext();const f=Math.round(globalFrame);
  const {beats:b}=config.props as unknown as Props;const s=groveState(f,b);
  const first=flight(f,b['first-release'],b['first-land'],podAt(MOTHER),CHILD);
  const second=flight(f,b['second-release'],b['second-land'],podAt(CHILD),THIRD);
  const impactStart=b['child-fruit']+22;
  return <Frame config={config} impact={f>=impactStart&&f<impactStart+66?<Impact frame={f} width={1920} height={1080} totalFrames={2040}
    maskBottom={830} events={[{id:'new-source',preset:'reveal',origin:podAt(CHILD),startFrame:impactStart}]}/>:null}>
    <Soil/>
    <Tree {...MOTHER} grow={1} fruit={arrive(progress(f,b['mother-fruit'],b['mother-fruit']+22))} departed={f>=b['first-release']} role="mother-tree"/>
    <Tree {...CHILD} grow={s.child} tone={mixColor(GOLD,WHITE,progress(f,b['child-ready'],b['child-fruit']))}
      fruit={arrive(progress(f,b['child-fruit'],b['child-fruit']+22))} departed={f>=b['second-release']} role="child-tree"/>
    <Tree {...THIRD} grow={s.third} gold role="third-tree"/>
    {f>=b['first-release']&&f<b['child-grow']+24?<Seed {...first}
      scale={.8*(1-progress(f,b['child-grow'],b['child-grow']+24))}
      angle={progress(f,b['first-release'],b['first-land'])*110} role="first-seed"/>:null}
    {f>=b['second-release']&&f<b['third-grow']+24?<Seed {...second}
      scale={CHILD.scale*.8*(1-progress(f,b['third-grow'],b['third-grow']+24))}
      angle={progress(f,b['second-release'],b['second-land'])*130} role="second-seed"/>:null}
    {[{event:'first-land',at:CHILD},{event:'second-land',at:THIRD}].map(({event,at})=><Burst key={event} origin={at}
      progress={progress(f,b[event],b[event]+24)} count={22} distance={90} size={3} rings={0} seed={event}/>)}
    <g transform={`translate(1360 195) scale(${pulse(f,b['child-fruit']+22)}) translate(-1360 -195)`}
      opacity={arrive(progress(f,b['child-fruit'],b['child-fruit']+15))*(1-progress(f,b['second-land']-45,b['second-land']-25))}>
      <Text x={1360} y={180} size={70} color={GOLD}>它，也结出了种子</Text>
    </g>
    <Text x={540} y={825} size={36} color={WHITE}>原来的树</Text>
    <Text x={1130} y={825} size={36} color={GOLD} opacity={s.child}>新长出的树</Text>
  </Frame>;
}
