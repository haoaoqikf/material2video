import {useSceneContext,type CodeSceneProps} from 'm2v/code-scene';
import {Frame,Text,WHITE,GOLD,MUTED,type Props} from './visual';
import {progress,arrive,ease,mix,pulse,type Beats} from './model';

const questions=[{a:8,b:5,event:'learning-first'},{a:9,b:6,event:'learning-reuse'},
  {a:19,b:6,event:'learning-extend'}];
const leftSlot=(i:number)=>({x:455+(i%10)*48,y:540+Math.floor(i/10)*64});
const rightSlot=(i:number)=>({x:1215+i*48,y:540});

/** 同一方法保留在场，换题时继续调用；珠子守恒，移出的不重复计数。 */
export function LearningDiagram({f,b}:{f:number;b:Beats}){
  const which=f>=b['learning-extend']?2:f>=b['learning-reuse']?1:0;
  const q=questions[which],start=b[q.event],need=Math.ceil(q.a/10)*10-q.a;
  const complete=arrive(progress(f,start+46,start+57));
  const previous=which>0?arrive(progress(f,start,start+10)):1;
  return <g opacity={previous}>
    <Text x={960} y={205} size={64} color={GOLD} role="reusable-method">先凑整十，再算剩下</Text>
    <path d="M620 264 Q960 277 1300 264" stroke={GOLD} strokeWidth={4} fill="none"/>
    <Text x={960} y={380} size={150} latin role="problem-value">{q.a} ＋ {q.b}</Text>
    <g>
      {Array.from({length:q.a},(_,i)=>{const p=leftSlot(i);return <circle key={`left-${i}`} cx={p.x} cy={p.y} r={16} fill={WHITE}/>;})}
      {Array.from({length:q.b},(_,i)=>{
        const p=ease(progress(f,start+16+i*2,start+40+i*2));
        const a=rightSlot(i),z=leftSlot(q.a+i),moving=i<need;
        return <circle key={`right-${i}`} cx={moving?mix(a.x,z.x,p):a.x}
          cy={moving?mix(a.y,z.y,p)-Math.sin(Math.PI*p)*125:a.y} r={16} fill={moving?GOLD:WHITE}/>;
      })}
    </g>
    <Text x={670} y={which===2?675:615} size={38} color={MUTED} opacity={complete}>{which===2?'凑成20':'凑成10'}</Text>
    <g opacity={complete} transform={`translate(960 752) scale(${pulse(f,start+57,18)}) translate(-960 -752)`}>
      <Text x={960} y={752} size={92} latin color={GOLD} role="answer-value">
        {q.a+need} ＋ {q.b-need} ＝ {q.a+q.b}
      </Text>
    </g>
  </g>;
}
export default function Learning(config:CodeSceneProps){
  const {globalFrame}=useSceneContext();const {beats:b}=config.props as unknown as Props;
  return <Frame config={config}><LearningDiagram f={Math.round(globalFrame)} b={b}/></Frame>;
}
