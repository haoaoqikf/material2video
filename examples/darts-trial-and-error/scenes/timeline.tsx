import {useEffect, useRef} from 'react';
import {gsap, useSceneContext} from 'm2v/code-scene';

export default function Timeline() {
  const host = useRef<HTMLDivElement>(null);
  const {ready, running} = useSceneContext();
  useEffect(() => {ready();}, []);
  useEffect(() => {
    if (!running) return;
    const context = gsap.context(() => {
      gsap.timeline().fromTo('.step', {opacity: 0, x: -120}, {opacity: 1, x: 0, stagger: .5, duration: .6})
        .to('.target', {scale: 1.25, rotation: 180, duration: .8});
    }, host);
    return () => context.revert();
  }, [running]);
  return <div ref={host} style={{padding: 60, fontSize: 56}}>
    {['尝试', '观察偏差', '调整方向'].map(text => <p className="step" key={text} style={{opacity: 0}}>{text}</p>)}
    <svg className="target" width="300" height="300" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="44" fill="none" stroke="#f7c85b" strokeWidth="5"/>
      <circle cx="50" cy="50" r="15" fill="#f7c85b"/>
    </svg>
  </div>;
}
