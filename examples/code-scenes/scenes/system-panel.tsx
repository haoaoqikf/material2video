// 只从受控图标白名单里取图标（web/src/primitives/iconSet.tsx）：
// 打包产物里只会多出这四个图标，不会把整本 Lucide 词典塞进 bundle。
import { CircleDollarSign, Clock, Link, Target } from 'lucide-react';
import { frameStroke, FrameIcon, layoutGraph, probe, useFrameChart, type A2VCodeScene } from '@a2v/scene';

/**
 * 统一系统面板：全片只有一个面板，四个模块（总览、分布、调用链、错误预算）
 * 始终在同一个世界里，阶段只改变哪个模块被点亮、以及模块里的读数。
 *
 * 库技术覆盖：Tailwind 类名（完整字符串，见 `panelTone`）、Lucide 图标
 * （`FrameIcon`，透明度只由帧号驱动）、ECharts（`useFrameChart`，逐帧 option）、
 * Dagre（`layoutGraph`，坐标只由输入集合决定）与定制 SVG（`frameStroke` 画预算环）。
 *
 * 全部读数取自剧本声明的对象状态（`objectStates.<id>.value/state`），
 * 组件不另算一套时间线，也不用挂钟或随机。
 */
interface SystemPanelData {
  headline: string;
  note: string;
  buckets: string[];
  hops: { id: string; label: string }[];
  /** 本阶段把注意力放在哪个模块上，用于面板的明暗基调。 */
  focus: 'overview' | 'tail' | 'chain' | 'budget';
}

const panelTone = {
  card: 'rounded-3xl border-2 shadow-2xl',
  row: 'rounded-2xl border',
} as const;

type ModuleState = 'rest' | 'focus' | 'muted' | 'done';

const readNumber = (value: unknown, fallback: number): number =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback;
const readNumbers = (value: unknown, fallback: number[]): number[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'number' && Number.isFinite(item))
    ? (value as number[])
    : fallback;
const readState = (value: unknown): ModuleState =>
  value === 'focus' || value === 'muted' || value === 'done' ? value : 'rest';

const ACCENT = 'var(--a2v-accent)';
const TEXT = 'var(--a2v-text-1)';
const LINE = 'var(--a2v-line)';

const SystemPanel: A2VCodeScene<SystemPanelData> = ({ scene, stage, objectStates }) => {
  const data = scene.data as unknown as SystemPanelData;
  const headline = String(data?.headline ?? '一个数字看不出系统健康');
  const note = String(data?.note ?? '');
  const buckets = Array.isArray(data?.buckets) ? data.buckets : [];
  const hops = Array.isArray(data?.hops) ? data.hops : [];

  const statusState = readState(objectStates.status?.state);
  const chartState = readState(objectStates.chart?.state);
  const graphState = readState(objectStates.graph?.state);
  const budgetState = readState(objectStates.budget?.state);
  const panelState = readState(objectStates.panel?.state);

  const availability = readNumber(objectStates.status?.value, 99.2);
  const distribution = readNumbers(objectStates.chart?.value, [0, 0, 0, 0, 0]);
  const hopCosts = readNumbers(objectStates.graph?.value, [4, 3, 4, 5]);
  const budgetLeft = readNumber(objectStates.budget?.value, 100);

  // 每个模块的强调程度：focus 用强调色，done/muted 依次变暗，rest 用普通文字色。
  const toneFor = (state: ModuleState, active: boolean): { stroke: string; opacity: number; label: string } => {
    if (active || state === 'focus') return { stroke: ACCENT, opacity: 1, label: ACCENT };
    if (state === 'done') return { stroke: LINE, opacity: 0.78, label: TEXT };
    if (state === 'muted') return { stroke: LINE, opacity: 0.45, label: TEXT };
    return { stroke: LINE, opacity: 0.9, label: TEXT };
  };
  const active = String(stage.data?.focus ?? 'overview');
  const statusTone = toneFor(statusState, active === 'overview');
  const chartTone = toneFor(chartState, active === 'tail');
  const graphTone = toneFor(graphState, active === 'chain');
  const budgetTone = toneFor(budgetState, active === 'budget');

  // ---------------------------------------------------------------- ECharts
  // `useFrameChart` 内部强制关闭图表动画：柱体长度只跟帧号走。
  const chart = useFrameChart(
    () => ({
      grid: { left: 64, right: 24, top: 28, bottom: 34 },
      xAxis: {
        type: 'category', data: buckets,
        axisLine: { lineStyle: { color: LINE } },
        axisTick: { show: false },
        axisLabel: { color: TEXT, fontSize: 26, fontFamily: 'var(--a2v-font)' },
      },
      yAxis: { type: 'value', max: 300, splitLine: { show: false }, axisLabel: { show: false } },
      series: [{
        type: 'bar',
        data: distribution.map((value, index) => ({
          value: Math.round(value),
          itemStyle: {
            color: index === distribution.length - 2 ? ACCENT : 'rgba(148,163,184,0.55)',
            borderRadius: [8, 8, 0, 0],
          },
        })),
        barWidth: 84,
        label: { show: true, position: 'top', color: TEXT, fontSize: 28, fontFamily: 'var(--a2v-font)' },
      }],
    }),
    [buckets, distribution],
  );

  // ---------------------------------------------------------------- Dagre 链路
  const layout = layoutGraph(
    hops.map((hop) => ({ id: hop.id, label: hop.label, width: 148, height: 76 })),
    hops.slice(0, -1).map((hop, index) => ({ from: hop.id, to: hops[index + 1]!.id })),
    { rankdir: 'LR', nodesep: 28, ranksep: 96 },
  );
  const toSvg = (x: number, y: number) => ({ x: x + 429 - layout.width / 2, y: y + 86 - layout.height / 2 });
  const maxCost = Math.max(1, ...hopCosts);

  // ---------------------------------------------------------------- 预算环
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const ring = frameStroke(budgetLeft / 100, circumference);

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 22, fontFamily: 'var(--a2v-font)',
    }}>
      <div {...probe({ node: 'headline', role: 'headline' })} style={{
        fontSize: 56, fontWeight: 700, color: TEXT, textAlign: 'center', maxWidth: 900, lineHeight: 1.2,
      }}>{headline}</div>

      <div
        className={`${panelTone.card} flex flex-col`}
        {...probe({ node: 'panel', role: 'body' })}
        style={{
          width: 930, padding: 24, gap: 14,
          backgroundColor: 'rgba(255,255,255,0.045)', borderColor: panelState === 'focus' ? ACCENT : LINE,
          boxSizing: 'border-box',
        }}
      >
        {/* 模块一：总览数字（Lucide 图标 + 可用率） */}
        <div
          className={`${panelTone.row} flex items-center`}
          {...probe({ node: 'status', role: 'label' })}
          style={{
            height: 136, padding: '0 24px', gap: 20, borderColor: statusTone.stroke,
            opacity: statusTone.opacity, backgroundColor: 'rgba(255,255,255,0.03)',
          }}
        >
          <FrameIcon icon={Target} size={54} color={statusTone.label} progress={1} aria-label="系统总览" />
          <div style={{ fontSize: 34, color: statusTone.label }}>系统总览</div>
          <div style={{ flex: 1 }} />
          <div style={{ fontSize: 74, fontWeight: 700, color: statusTone.label }}>
            {availability.toFixed(1)}
            <span style={{ fontSize: 38, marginLeft: 6 }}>%</span>
          </div>
          <div style={{
            fontSize: 30, padding: '8px 18px', borderRadius: 999,
            color: statusState === 'focus' ? '#0b1120' : TEXT,
            backgroundColor: statusState === 'focus' ? ACCENT : 'rgba(148,163,184,0.18)',
          }}>正常</div>
        </div>

        {/* 模块二：延迟分布（ECharts） */}
        <div
          className={`${panelTone.row} flex flex-col`}
          {...probe({ node: 'chart', role: 'body' })}
          style={{
            height: 300, padding: '16px 24px 10px', gap: 6, borderColor: chartTone.stroke,
            opacity: chartTone.opacity, backgroundColor: 'rgba(255,255,255,0.03)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <FrameIcon icon={Clock} size={44} color={chartTone.label} progress={1} aria-label="延迟分布" />
            <div style={{ fontSize: 32, color: chartTone.label }}>延迟分布 · 毫秒</div>
            <div style={{ flex: 1 }} />
            <div {...probe({ node: 'chart-tail', role: 'label' })} style={{ fontSize: 28, color: chartTone.label }}>
              尾巴决定体验
            </div>
          </div>
          <div ref={chart.ref} style={{ width: 858, height: 214 }} />
        </div>

        {/* 模块三：调用链（Dagre 稳定布局 + 定制 SVG） */}
        <div
          className={`${panelTone.row} flex flex-col`}
          {...probe({ node: 'graph', role: 'body' })}
          style={{
            height: 252, padding: '16px 24px 6px', gap: 4, borderColor: graphTone.stroke,
            opacity: graphTone.opacity, backgroundColor: 'rgba(255,255,255,0.03)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <FrameIcon icon={Link} size={44} color={graphTone.label} progress={1} aria-label="调用链" />
            <div style={{ fontSize: 32, color: graphTone.label }}>调用链 · 每跳耗时</div>
          </div>
          <svg width={858} height={168} {...probe({ node: 'graph-canvas', schematic: true })}>
            {layout.edges.map((edge, index) => {
              const from = layout.nodes.find((node) => node.id === edge.from);
              const to = layout.nodes.find((node) => node.id === edge.to);
              if (!from || !to) return null;
              const start = toSvg(from.x + from.width / 2, from.y);
              const end = toSvg(to.x - to.width / 2, to.y);
              const cost = hopCosts[index] ?? 0;
              const weight = 6 + 26 * (cost / maxCost);
              const hot = cost >= maxCost;
              return (
                <g key={`${edge.from}-${edge.to}`}>
                  <line x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke={hot ? ACCENT : LINE}
                    strokeWidth={weight} strokeLinecap="round" opacity={hot ? 0.95 : 0.6} />
                  <text x={(start.x + end.x) / 2} y={(start.y + end.y) / 2 - 14} textAnchor="middle"
                    fontFamily="var(--a2v-font)" fontSize={30} fill={hot ? ACCENT : TEXT}
                    {...probe({ node: `graph-hop-${index}`, role: 'label' })}>{Math.round(cost)}ms</text>
                </g>
              );
            })}
            {layout.nodes.map((node) => {
              const point = toSvg(node.x, node.y);
              return (
                <g key={node.id}>
                  <rect x={point.x - node.width / 2} y={point.y - node.height / 2}
                    width={node.width} height={node.height} rx={20}
                    fill="rgba(255,255,255,0.05)" stroke={graphTone.stroke} strokeWidth={4} />
                  <text x={point.x} y={point.y + 13} textAnchor="middle" fontFamily="var(--a2v-font)"
                    fontSize={34} fill={TEXT}
                    {...probe({ node: `graph-node-${node.id}`, role: 'label' })}>{node.label}</text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* 模块四：错误预算（定制 SVG 环，描边只跟帧号走） */}
        <div
          className={`${panelTone.row} flex items-center`}
          {...probe({ node: 'budget', role: 'body' })}
          style={{
            height: 196, padding: '0 24px', gap: 24, borderColor: budgetTone.stroke,
            opacity: budgetTone.opacity, backgroundColor: 'rgba(255,255,255,0.03)',
          }}
        >
          <FrameIcon icon={CircleDollarSign} size={44} color={budgetTone.label} progress={1} aria-label="错误预算" />
          <svg width={168} height={168} {...probe({ node: 'budget-ring', schematic: true })}>
            <circle cx={84} cy={84} r={radius} fill="none" stroke="rgba(148,163,184,0.22)" strokeWidth={18} />
            <circle cx={84} cy={84} r={radius} fill="none" stroke={budgetTone.label} strokeWidth={18}
              strokeLinecap="round" pathLength={circumference}
              strokeDasharray={ring.dasharray} strokeDashoffset={ring.offset}
              transform="rotate(-90 84 84)" />
            <text x={84} y={96} textAnchor="middle" fontFamily="var(--a2v-font)" fontSize={40} fontWeight={700}
              fill={TEXT} {...probe({ node: 'budget-value', role: 'hero' })}>{Math.round(budgetLeft)}%</text>
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 34, color: budgetTone.label }}>错误预算 · 剩余 {Math.round(budgetLeft)}%</div>
            <div {...probe({ node: 'budget-note', role: 'caption' })} style={{ fontSize: 30, color: LINE }}>
              还能承受多少，是一条看得见的线
            </div>
          </div>
        </div>
      </div>

      <div {...probe({ node: 'note', role: 'body' })} style={{
        fontSize: 36, color: TEXT, textAlign: 'center', maxWidth: 900, lineHeight: 1.35,
      }}>{note}</div>
    </div>
  );
};

export default SystemPanel;
