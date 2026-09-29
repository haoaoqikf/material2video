import { useMemo } from 'react';
import { beatActionProgress, compilePath, compileReservoir, decomposeObjects, probe, type A2VCodeScene, type FlowInterval } from '@a2v/scene';

interface Data { title: string; note: string; mode: string; capacity: number; initial: number; intervals: FlowInterval[] }
const inlet = compilePath([{ x: 180, y: 150 }, { x: 180, y: 270 }, { x: 330, y: 270 }, { x: 330, y: 390 }]);
const outlet = compilePath([{ x: 560, y: 690 }, { x: 710, y: 690 }, { x: 710, y: 850 }]);
const particles = Array.from({ length: 8 }, (_, i) => i);
const poses = [{ id: 'inlet', from: { x: 0, y: 0 }, to: { x: -55, y: -40 } }, { id: 'tank', from: { x: 0, y: 0 }, to: { x: 0, y: 30 } }, { id: 'outlet', from: { x: 0, y: 0 }, to: { x: 55, y: 50 } }];

const WaterTank: A2VCodeScene<Data> = ({ scene, localFrame, beats }) => {
  const d = scene.data;
  const reservoir = useMemo(() => compileReservoir(d.capacity, d.initial, d.intervals), [d]);
  const b1 = beatActionProgress(beats.plan, 'b1', localFrame, .8);
  const b2 = beatActionProgress(beats.plan, 'b2', localFrame, .8);
  const b3 = beats.plan.some((b) => b.id === 'b3') ? beatActionProgress(beats.plan, 'b3', localFrame, .8) : b2;
  const time = d.mode === 'smooth' ? b1 * 4 + b2 * 4 : b1 * 3 + b2 * 5;
  const state = reservoir(time);
  const direct = d.mode === 'direct' || d.mode === 'opening';
  const level = direct ? 0 : d.mode === 'structure' ? .3 : d.mode === 'conclusion' ? .45 : state.level / d.capacity;
  const layout = decomposeObjects(poses, d.mode === 'structure' ? b2 : d.mode === 'conclusion' ? b1 : 0, d.mode === 'conclusion');
  const movement = b1 + b2;
  const flowing = !direct || b2 < .65;
  const accent = 'var(--a2v-accent)'; const text = 'var(--a2v-text-1)'; const line = 'var(--a2v-text-2)';
  return <div style={{ width: '100%', height: '100%', position: 'relative', fontFamily: 'var(--a2v-font)' }}>
    <div {...probe({ node: 'title', role: 'headline' })} style={{ fontSize: 64, fontWeight: 700, textAlign: 'center', color: text, paddingTop: 30 }}>{d.title}</div>
    <svg viewBox="0 0 888 980" width="100%" height="850" style={{ position: 'absolute', top: 110, left: 0 }} {...probe({ node: 'diagram', schematic: true })}>
      <g transform={`translate(${layout[0]!.x} ${layout[0]!.y})`}>
        <path d="M180 150V270H330V390" fill="none" stroke={line} strokeWidth="8" />
        {particles.map((i) => { const point = inlet(movement * .7, (i + 1) / 9); return <circle key={i} cx={point.x} cy={point.y} r="9" fill={accent} opacity={flowing ? 1 : .15} />; })}
        <text x="180" y="105" textAnchor="middle" fontSize="40" fill={text} {...probe({ node: 'input-label', role: 'label' })}>输入</text>
      </g>
      <g transform={`translate(${layout[1]!.x} ${layout[1]!.y})`} {...probe({ node: 'tank', schematic: true })}>
        {direct ? <path d="M330 390V530H560V690" fill="none" stroke={text} strokeWidth="8" /> : <>
          <rect x="280" y="390" width="310" height="350" rx="24" fill="var(--a2v-bg)" stroke={text} strokeWidth="8" />
          <rect x="290" y={730 - 330 * level} width="290" height={330 * level} rx="12" fill={accent} opacity=".7" {...probe({ node: 'water', schematic: true })} />
        </>}
        <text x="435" y="790" textAnchor="middle" fontSize="40" fill={text} {...probe({ node: 'tank-label', role: 'label' })}>{direct ? '直接传递波动' : '有限容量'}</text>
        {d.mode === 'overload' && <path d={`M590 410 Q${650 + state.overflow * 5} 460 660 730`} stroke={accent} fill="none" strokeWidth="14" opacity={Math.min(1, state.overflow / 2)} {...probe({ node: 'overflow', schematic: true })} />}
      </g>
      <g transform={`translate(${layout[2]!.x} ${layout[2]!.y})`}>
        <path d="M560 690H710V850" fill="none" stroke={line} strokeWidth="8" />
        {particles.map((i) => { const point = outlet(movement * .5, (i + 1) / 9); return <circle key={i} cx={point.x} cy={point.y} r="8" fill={accent} opacity={flowing ? 1 : .15} />; })}
        <text x="710" y="915" textAnchor="middle" fontSize="40" fill={text} {...probe({ node: 'output-label', role: 'label' })}>{direct ? '输出随之停' : '限流输出'}</text>
      </g>
      {d.mode === 'smooth' && <g opacity={b3}><path d="M100 950H780" stroke={accent} strokeWidth="8" /><text x="440" y="885" textAnchor="middle" fontSize="40" fill={text} {...probe({ node: 'stable-label', role: 'label' })}>高峰存储 · 低谷补充</text></g>}
    </svg>
    <div {...probe({ node: 'note', role: 'body' })} style={{ position: 'absolute', top: 1000, width: '100%', textAlign: 'center', fontSize: 48, color: text }}>{d.note}</div>
  </div>;
};
export default WaterTank;
