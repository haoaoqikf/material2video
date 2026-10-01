import { probe, type A2VCodeScene } from '@a2v/scene';

const throws = [
  { id: 'dart-1', x: 720, y: 610, label: '01' },
  { id: 'dart-2', x: 660, y: 555, label: '02' },
  { id: 'dart-3', x: 625, y: 520, label: '03' },
] as const;
const easeOut = (value: number): number => 1 - (1 - Math.max(0, Math.min(1, value))) ** 3;

interface StageData { headline?: string }

const DartsTrialAndError: A2VCodeScene<StageData> = ({ frame, beats, stage, canvas }) => {
  const hit = beats.plan.find((beat) => beat.id === 'beat-3');
  const repeat = beats.plan.find((beat) => beat.id === 'beat-4');
  const learn = beats.plan.find((beat) => beat.id === 'beat-5');
  const phase = (beat: typeof hit): number => beat
    ? easeOut((frame - beat.startFrame) / Math.max(1, beat.endFrame - beat.startFrame)) : 0;
  const first = phase(hit);
  const learned = phase(learn);
  const firstVisible = hit ? frame >= hit.startFrame : false;
  const throwsVisible = throws.map((_, index) => index === 0
    ? firstVisible
    : repeat ? frame >= repeat.startFrame + index * 34 : false);
  const visibleCount = throwsVisible.filter(Boolean).length;
  const activeThrow = repeat && frame >= repeat.startFrame && frame < repeat.endFrame
    ? Math.min(throws.length - 1, Math.floor((frame - repeat.startFrame) / 34)) : -1;
  const current = activeThrow >= 0 ? throws[activeThrow] : null;
  const isClosing = stage.id === 'learn';
  const flyingX = current ? 312 + (current.x - 312) * phase(repeat) : 0;
  const flyingY = current ? 468 + (current.y - 468) * phase(repeat) : 0;
  const headline = String(stage.data.headline ?? '每次行动都留下反馈');
  const textColor = 'var(--a2v-text-1)';
  const muted = 'var(--a2v-text-2)';
  const accent = 'var(--a2v-accent)';

  return <div style={{ position: 'relative', width: canvas.width, height: canvas.height, overflow: 'hidden', fontFamily: 'var(--a2v-font)', color: textColor }}>
    <div {...probe({ node: 'stage-headline', role: 'headline' })} style={{ position: 'absolute', top: 220, left: 90, width: 900, textAlign: 'center', fontSize: 54, fontWeight: 700 }}>
      {headline}
    </div>
    <div {...probe({ node: 'arena', schematic: true })} style={{ position: 'absolute', left: 90, top: 300, width: 900, height: 940 }}>
      <svg viewBox="0 0 900 940" width="100%" height="100%" aria-label="同一人物向持续存在的飞镖靶投掷">
        <path d="M305 482 Q420 420 536 430" fill="none" stroke="var(--fig-line-soft)" strokeWidth="5" strokeDasharray="10 16" />
        <g {...probe({ node: 'target', schematic: true })}>
          <circle cx="650" cy="465" r="188" fill="var(--a2v-bg-1)" stroke="var(--fig-line)" strokeWidth="8" />
          <circle cx="650" cy="465" r="142" fill="none" stroke="var(--fig-line-soft)" strokeWidth="5" />
          <circle cx="650" cy="465" r="94" fill="none" stroke="var(--fig-line-soft)" strokeWidth="5" />
          <circle cx="650" cy="465" r="46" fill="none" stroke={accent} strokeOpacity=".7" strokeWidth="6" />
          <circle cx="650" cy="465" r="10" fill={accent} />
        </g>
        <g {...probe({ node: 'player', schematic: true })}>
          <circle cx="205" cy="318" r="54" fill="var(--a2v-bg-2)" stroke={textColor} strokeWidth="6" />
          <path d="M205 374 L205 590 M205 430 L312 468 M205 590 L140 720 M205 590 L272 720" fill="none" stroke={textColor} strokeWidth="24" strokeLinecap="round" />
          <path d="M292 450 L326 468 L292 486" fill="none" stroke={accent} strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        <g {...probe({ node: 'dart', schematic: true })}>
          {throwsVisible.map((visible, index) => {
            if (!visible) return null;
            const item = throws[index]!;
            const active = index === 0 ? first > 0 && first < 1 : activeThrow === index;
            return <g key={item.id} {...probe({ node: item.id, schematic: true })} opacity={active ? 0.45 : 1}>
              <path d={`M${item.x - 22} ${item.y + 20} L${item.x + 22} ${item.y - 20}`} stroke={index === 0 ? 'var(--fig-line)' : accent} strokeWidth="12" strokeLinecap="round" />
              <path d={`M${item.x + 18} ${item.y - 16} L${item.x + 39} ${item.y - 24} L${item.x + 30} ${item.y - 4} Z`} fill={index === 0 ? 'var(--fig-line)' : accent} />
            </g>;
          })}
          {first > 0 && first < 0.97 && <path d={`M312 468 L${312 + (throws[0].x - 312) * first} ${468 + (throws[0].y - 468) * first}`} stroke={accent} strokeWidth="5" strokeDasharray="8 12" opacity=".8" />}
          {current && phase(repeat) < 0.96 && <g {...probe({ node: 'dart-flight', schematic: true })}>
            <path d={`M${flyingX - 19} ${flyingY + 19} L${flyingX + 19} ${flyingY - 19}`} stroke={accent} strokeWidth="12" strokeLinecap="round" />
          </g>}
        </g>
        <path d="M650 465 L625 520" stroke={accent} strokeOpacity={learned * 0.75} strokeWidth="3" strokeDasharray="6 10" />
      </svg>
    </div>
    <div {...probe({ node: 'throw-count', role: 'hero' })} style={{ position: 'absolute', top: 1250, left: 110, width: 860, textAlign: 'center', fontSize: 48, fontWeight: 700 }}>
      {`已投 ${Math.max(visibleCount, 1)} 次 · 示意`}
    </div>
    <div {...probe({ node: 'feedback-label', role: 'body' })} style={{ position: 'absolute', top: 1340, left: 120, width: 840, textAlign: 'center', fontSize: 34, color: muted }}>
      {isClosing ? '保留偏差，调整下一次方向' : stage.id === 'hesitate' ? '高估成本，迟迟没有行动' : stage.id === 'no-feedback' ? '没有落点，也就没有反馈' : stage.id === 'first-throw' ? `第一枚飞镖留下偏差 ${Math.round(first * 100)}%` : '同一张靶上，落点逐次累积'}
    </div>
    <div {...probe({ node: 'target-note', role: 'caption' })} style={{ position: 'absolute', top: 1435, left: 120, width: 840, textAlign: 'center', fontSize: 28, color: muted }}>
      {`投掷者与目标保持不变${learned > 0 ? ' · 结果用于调整，不代表必然命中' : ''}`}
    </div>
  </div>;
};

export default DartsTrialAndError;
