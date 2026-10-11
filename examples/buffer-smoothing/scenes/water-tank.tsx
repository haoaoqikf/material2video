import { compilePath, probe, type M2VCodeScene } from '@m2v/scene';

interface Data {
  headline: string;
  note: string;
  /** 本阶段演示哪一种输入条件：脉冲直通、开始蓄水、存储循环、持续超载、收尾稳定。 */
  flow: 'pulse' | 'fill' | 'cycle' | 'surge' | 'settle';
}

/* 全片同一个世界的几何：入口管道、水箱、出口管道，以及一条绕开水箱的直通旁路。 */
const inletPath = compilePath([{ x: 60, y: 120 }, { x: 420, y: 120 }, { x: 420, y: 250 }]);
const outletPath = compilePath([{ x: 420, y: 630 }, { x: 420, y: 780 }, { x: 828, y: 780 }]);
const bypassPath = compilePath([{ x: 420, y: 120 }, { x: 828, y: 120 }, { x: 828, y: 780 }]);
const inletDots = [0, 1, 2, 3, 4, 5, 6, 7];
const outletDots = [0, 1, 2, 3, 4, 5];
const drops = [0, 1, 2, 3, 4];

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));
const frac = (value: number): number => value - Math.floor(value);
const readNumber = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null);

/**
 * 持续缓冲系统：入口脉冲、水箱水位、出口水流和溢出口始终在同一个世界里，
 * 阶段只改变输入条件与可观察状态。水位、水滴与溢出都由帧号纯函数得出，
 * 不使用挂钟或随机，随机寻帧与顺序播放得到同一画面。
 */
const WaterTank: M2VCodeScene<Data> = ({ stage, objectStates, frame }) => {
  const flow = String(stage.data.flow ?? 'settle') as Data['flow'];
  const headline = String(stage.data.headline ?? '缓冲区如何吸收波动');
  const note = String(stage.data.note ?? '');

  // 水位是剧本声明的对象状态（`tank.value` 轨道），组件只负责把它画出来，
  // 不在组件里另算一套时间线。
  const level = clamp01(readNumber(objectStates.tank?.value) ?? 0);
  const tankState = String(objectStates.tank?.state ?? 'rest');
  const overflowVisible = objectStates.overflow?.visible === true;
  const outletSteady = objectStates.outlet?.state === 'focus';
  const direct = flow === 'pulse';

  const burst = 0.5 + 0.5 * Math.sin(frame / 8);
  const inletCount = direct ? Math.round(inletDots.length * burst) : inletDots.length;
  const outletCount = direct ? Math.round(outletDots.length * burst) : 4;
  const inletSpeed = flow === 'surge' ? 0.022 : 0.012;

  const accent = 'var(--m2v-accent)';
  const text = 'var(--m2v-text-1)';
  const line = 'var(--m2v-text-2)';
  const tankStroke = direct ? line : tankState === 'focus' ? accent : text;
  const bypassStroke = direct ? accent : line;
  const waterTop = 618 - 356 * level;

  return <div style={{
    width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: 18, fontFamily: 'var(--m2v-font)',
  }}>
    <div {...probe({ node: 'title', role: 'headline' })} style={{
      fontSize: 56, fontWeight: 700, textAlign: 'center', color: text, maxWidth: 888, lineHeight: 1.2,
    }}>{headline}</div>
    <svg viewBox="0 0 888 960" width="888" height="900" {...probe({ node: 'diagram', schematic: true })}>
      {/* 直通旁路：脉冲阶段高亮，其余阶段置灰，表示水流改走水箱。 */}
      <path d="M420 120H828V780" fill="none" stroke={bypassStroke} strokeWidth={direct ? 12 : 6}
        strokeDasharray={direct ? undefined : '16 18'} opacity={direct ? 0.95 : 0.45} />
      {direct ? inletDots.slice(0, 6).map((i) => {
        const point = bypassPath(frac(frame * inletSpeed + i / 6));
        return <circle key={`bypass-${i}`} cx={point.x} cy={point.y} r="10" fill={accent} />;
      }) : null}

      {/* 入口管道与水滴：世界对象 inlet 的探针容器始终存在，内容随阶段变化。 */}
      <g {...probe({ node: 'inlet', schematic: true })}>
        <path d="M60 120H420V250" fill="none" stroke={line} strokeWidth="10" strokeLinejoin="round" />
        <text x="150" y="86" textAnchor="middle" fontSize="34" fill={text}
          {...probe({ node: 'inlet-label', role: 'label' })}>输入</text>
        {inletDots.slice(0, inletCount).map((i) => {
          const point = inletPath(frac(frame * inletSpeed + i / 8));
          return <circle key={`inlet-${i}`} cx={point.x} cy={point.y} r={direct ? 9 : 11} fill={accent} opacity={direct ? 0.55 + 0.45 * burst : 1} />;
        })}
      </g>

      {/* 水箱：水位是唯一的容量证据 */}
      <g {...probe({ node: 'tank', schematic: true })}>
        <rect x="250" y="250" width="340" height="380" rx="24" fill="var(--m2v-bg)" stroke={tankStroke} strokeWidth={direct ? 6 : 10} opacity={direct ? 0.5 : 1} />
        {level > 0 ? <rect x="262" y={waterTop} width="316" height={618 - waterTop} rx="14" fill={accent} opacity="0.55"
          {...probe({ node: 'water', schematic: true })} /> : null}
        <line x1="250" y1="262" x2="590" y2="262" stroke={line} strokeWidth="4" strokeDasharray="10 12" opacity="0.7" />
        <text x="300" y="226" textAnchor="middle" fontSize="34" fill={text}
          {...probe({ node: 'tank-label', role: 'label' })}>存储</text>
        <text x="190" y="700" textAnchor="middle" fontSize="30" fill={line}
          {...probe({ node: 'capacity-label', role: 'label' })}>有限容量</text>
      </g>

      {/* 溢出口：探针容器始终存在，只在容量被突破后画出内容。 */}
      <g {...probe({ node: 'overflow', schematic: true })} opacity={overflowVisible ? 1 : 0}>
        <path d="M588 280Q690 246 706 400" fill="none" stroke={accent} strokeWidth="12" opacity="0.9" />
        {drops.map((i) => {
          const t = frac(frame / 26 + i / drops.length);
          return <circle key={`drop-${i}`} cx={706 + 18 * t} cy={400 + 220 * t} r={8 - 3 * t} fill={accent} opacity={0.9 - 0.6 * t} />;
        })}
        <text x="782" y="392" textAnchor="middle" fontSize="30" fill={accent}
          {...probe({ node: 'overflow-label', role: 'label' })}>溢出</text>
      </g>

      {/* 出口管道与水滴：经缓冲后间隔一致 */}
      <g {...probe({ node: 'outlet', schematic: true })}>
        <path d="M420 630V780H828" fill="none" stroke={line} strokeWidth="10" strokeLinejoin="round" />
        <path d="M828 780l-30-16v32z" fill={line} />
        <text x="700" y="836" textAnchor="middle" fontSize="34" fill={text}
          {...probe({ node: 'outlet-label', role: 'label' })}>出口</text>
        {outletDots.slice(0, outletCount).map((i) => {
          const point = outletPath(frac(frame * 0.01 + i / (direct ? 5 : 4)));
          return <circle key={`outlet-${i}`} cx={point.x} cy={point.y} r="10" fill={accent}
            opacity={direct ? 0.5 + 0.5 * burst : 1} />;
        })}
        {outletSteady ? <g opacity="0.85">
          <line x1="470" y1="900" x2="828" y2="900" stroke={accent} strokeWidth="6" />
          <text x="649" y="944" textAnchor="middle" fontSize="30" fill={text}
            {...probe({ node: 'steady-label', role: 'label' })}>输出保持平稳</text>
        </g> : null}
      </g>
    </svg>
    <div {...probe({ node: 'note', role: 'body' })} style={{
      fontSize: 38, textAlign: 'center', color: text, maxWidth: 888, lineHeight: 1.35,
    }}>{note}</div>
  </div>;
};

export default WaterTank;
