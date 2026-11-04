import {useSceneContext,type CodeSceneProps} from 'm2v/code-scene';
import Burst from 'm2v/style/components/burst';
import {Frame,Tree,Seed,Soil,Text,GOLD,type Props} from './visual';
import {MOTHER,progress,arrive,groveState,pulse,mix} from './model';
export default function Opening(config:CodeSceneProps){
  const {globalFrame}=useSceneContext();const f=Math.round(globalFrame);const {beats:b}=config.props as unknown as Props;
  const drop=progress(f,b['seed-drop'],b['seed-land']),bounce=progress(f,b['seed-land'],b['seed-land']+22);
  const y=f<b['seed-land']?mix(220,755,drop*drop):755-Math.sin(Math.PI*bounce)*24;
  const state=groveState(f,b),label=1-arrive(progress(f,b['mother-grow']-15,b['mother-grow']+15));
  return <Frame config={config}><g style={{willChange:'transform'}}>
    <Soil/>
    {f<b['mother-grow']+10?<Seed x={MOTHER.x} y={y} scale={1.35} angle={mix(-20,25,drop)}
      opacity={1-progress(f,b['mother-grow'],b['mother-grow']+10)} role="opening-seed"/>:null}
    <Burst origin={{x:MOTHER.x,y:770}} progress={progress(f,b['seed-land'],b['seed-land']+28)} count={20} distance={90} size={3} rings={0} seed="first-contact"/>
    <g opacity={label} transform={`translate(1150 450) scale(${pulse(f,b['seed-land'])}) translate(-1150 -450)`}>
      <Text x={1100} y={430} size={265} latin role="opening-number">1</Text><Text x={1295} y={485} size={90}>粒</Text>
    </g>
    <Tree {...MOTHER} grow={state.mother} role="mother-tree"/>
    <Text x={1310} y={395} size={68} color={GOLD} opacity={arrive(progress(f,270,300))}>先，长成一棵树</Text>
  </g></Frame>;
}
