import {useEffect, useRef} from 'react';
import {gsap, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

const landings = [{x: 605,y: 220,label: '① 记录右上偏差'},{x: 505,y: 305,label: '② 只调整一个动作'},{x: 449,y: 354,label: '③ 复查是否改善'}];
export default function FeedbackDemo({fps,segmentWindows,theme}: CodeSceneProps) {
  const host = useRef<HTMLDivElement>(null);
  const timeline = useRef<gsap.core.Timeline | null>(null);
  const {ready,elapsedSeconds} = useSceneContext();
  const ink = theme === 'light' ? '#172434' : '#edf4fc';
  useEffect(() => {
    // 暂停时间轴并按录制时钟 seek，落点绑定实际旁白段起点。
    const context = gsap.context(() => {
      const animation = gsap.timeline({paused: true});
      Object.values(segmentWindows).sort((a,b)=>a.startFrame-b.startFrame).forEach((w,i) => {
        animation.fromTo(`.landing-${i}`,{opacity: 0,x: -100,y: 70,scale: 0.3},
          {opacity: 1,x: 0,y: 0,scale: 1,duration: 1,ease: 'power2.out'},w.startFrame/fps+0.5);
        animation.fromTo(`.record-${i}`,{opacity: 0},{opacity: 1,duration: 0.5},w.startFrame/fps+1.5);
      });
      timeline.current = animation;
    },host);
    ready();
    return () => {timeline.current = null; context.revert();};
  }, [fps,segmentWindows]);
  useEffect(() => {timeline.current?.seek(elapsedSeconds);}, [elapsedSeconds]);
  return <div ref={host} style={{height: 920,color: ink,fontFamily: 'Noto Sans SC'}}>
    <svg width="864" height="620" viewBox="0 0 864 620">
      {[235,175,115,55].map((r,i)=><circle key={r} cx="432" cy="370" r={r} fill={i%2 ? '#243b50' : '#193045'} stroke="#7290aa" strokeWidth="3"/>)}
      <path d="M432 120V610M180 370H684" stroke="#7290aa" strokeWidth="2"/>
      <circle cx="432" cy="370" r="15" fill="#f7c85b"/>
      {landings.map((p,i)=><g key={i} className={`landing-${i}`} style={{opacity: 0,transformOrigin: `${p.x}px ${p.y}px`}}>
        <path d={`M${p.x} ${p.y}l36 -45`} stroke="#f7c85b" strokeWidth="8"/>
        <circle cx={p.x} cy={p.y} r="17" fill={['#5aafff','#68cdb5','#f7c85b'][i]}/>
        <text x={p.x+22} y={p.y-12} fill={ink} fontSize="34">{i+1}</text>
      </g>)}
      <text x="432" y="75" textAnchor="middle" fill={ink} fontSize="35">观察结果，才能讨论修正</text>
    </svg>
    {landings.map((p,i)=><div className={`record-${i}`} key={p.label} style={{opacity: 0,margin: '12px 80px',fontSize: 32}}>{p.label}</div>)}
    <div style={{margin: '24px 80px',fontSize: 26,color: '#91a8be'}}>落点为示意 · 不保证每次都会更好</div>
  </div>;
}
