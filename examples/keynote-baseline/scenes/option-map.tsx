import { probe, type M2VCodeScene } from '@m2v/scene';

interface OptionMapData { headline: string; note: string; count: number }

/** 单一持续场景：分叉路线逐步收束，所有位置始终属于同一张地图。 */
const OptionMap: M2VCodeScene<OptionMapData> = ({ stage, objectStates, frame }) => {
  const data = stage.data as unknown as OptionMapData;
  const countValue = objectStates.routes?.value;
  const count = typeof countValue === 'number' ? countValue : data.count;
  const routeCount = Math.max(1, Math.min(10, Math.round(count)));
  const focus = stage.progress;
  const ink = 'var(--m2v-text-1)';
  const muted = 'var(--m2v-text-2)';
  const accent = 'var(--m2v-accent)';
  const line = 'var(--m2v-line)';
  const choices = Array.from({ length: 10 }, (_, index) => index);
  const centerX = 540;
  const spread = 430;
  return (
    <div style={{ width: '100%', height: '100%', background: 'var(--m2v-bg-1)', color: ink, fontFamily: 'var(--m2v-font)', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 90, boxSizing: 'border-box' }}>
      <div {...probe({ node: 'map', role: 'headline', geometry: { x: 70, y: 250, width: 940, height: 300 } })} style={{ fontSize: 72, lineHeight: 1.2, fontWeight: 700, textAlign: 'center' }}>{data.headline}</div>
      <div style={{ position: 'relative', height: 700, marginTop: 80 }}>
        <svg viewBox="0 0 1080 700" width="100%" height="100%" aria-label="持续存在的分叉选项地图">
          {choices.map((index) => {
            const ratio = index / 9 - 0.5;
            const x = centerX + ratio * spread;
            const selected = index === 4;
            const routeRank = Math.abs(index - 4) * 2 + 1;
            const retained = Math.min(1, Math.max(0, (count - routeRank + 2) / 2));
            const opacity = retained * (0.35 + Math.min(1, focus * 1.2) * 0.65);
            return <g key={index} opacity={opacity}>
              <path d={`M540 570 Q${x} 420 ${x} 230`} fill="none" stroke={selected ? accent : line} strokeWidth={selected ? 8 : 4} strokeDasharray={selected ? undefined : '12 14'} />
              <circle cx={x} cy="210" r={selected ? 34 : 20} fill={selected ? accent : 'var(--m2v-bg-2)'} stroke={selected ? accent : line} strokeWidth="4" />
              {selected ? <text x={x} y="145" textAnchor="middle" fill={accent} fontSize="24">足够</text> : null}
            </g>;
          })}
          <circle cx="540" cy="570" r="42" fill="var(--m2v-bg-2)" stroke={accent} strokeWidth="6" />
          <text x="540" y="650" textAnchor="middle" fill={ink} fontSize="30">现在的选择</text>
        </svg>
        <div {...probe({ node: 'routes', role: 'label', geometry: { x: 400, y: 650, width: 280, height: 100 }, schematic: true })} style={{ position: 'absolute', top: 10, right: 0, color: accent, fontSize: 36, fontWeight: 600 }}>{routeCount} 条路线{frame >= 0 ? '' : ''}</div>
      </div>
      <div style={{ textAlign: 'center', color: muted, fontSize: 36, marginTop: 20 }}>{data.note}</div>
    </div>
  );
};

export default OptionMap;
