import { useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import type { Scene, SceneNode } from '@/schema/storyboard';
import { stylePackDefinition } from '@/registry';
import { EMPTY_BEAT_CONTEXT, nodeBeatState, type BeatContext, type BeatTimeline, type NodeBeatState } from '@/runtime/beats';
import { continuityNodeStyle, continuityVisibleIds, type ContinuityRenderState } from '@/runtime/continuity';
import { channelStyle, motionProgress, sceneMotionPlan, visualMix } from '@/runtime/motionPlan';
import { IconGlyph } from './iconSet';

const GAP = { none: 0, xs: 8, sm: 16, md: 28, lg: 44, xl: 64 } as const;
const ROLE_CLASS: Record<string, string> = { hero: 'a2v-hero', headline: 'a2v-headline', title: 'a2v-title', body: 'a2v-body', label: 'a2v-label', caption: 'a2v-caption' };
/** 字号档位从大到小。预设取档时沿这条阶梯向下找第一个放得下的档位。 */
export const ROLE_LADDER = ['hero', 'headline', 'title', 'body', 'label', 'caption'] as const;
const CONNECTOR_TURN: Record<string, string> = { ltr: 'none', rtl: 'scaleX(-1)', ttb: 'rotate(90deg)', btt: 'rotate(-90deg)' };

/**
 * 方向轴：`flow` 与 `timeline` 共用的一组确定性映射。
 *
 * 方向只影响**排列顺序**与**进度填充的起点**，不改变子节点数量、内容或基础几何：
 * 同一份场景树在任何一帧都得到同一组尺寸与位置。
 */
const AXIS: Record<string, { flex: 'row' | 'row-reverse' | 'column' | 'column-reverse'; origin: string; scale: 'scaleX' | 'scaleY' }> = {
  ltr: { flex: 'row', origin: 'left center', scale: 'scaleX' },
  rtl: { flex: 'row-reverse', origin: 'right center', scale: 'scaleX' },
  ttb: { flex: 'column', origin: 'center top', scale: 'scaleY' },
  btt: { flex: 'column-reverse', origin: 'center bottom', scale: 'scaleY' },
};
const axisOf = (direction?: string) => AXIS[direction ?? 'ltr'] ?? AXIS.ltr!;

/** 中层原语：读取共享 beat 状态、自己不做时间计算的布局容器。 */
const STAGE_CONTAINERS = new Set(['flow', 'cycle', 'timeline']);

/** 内容引用解析：支持 "data.a.b" 与 "data.list[0]"，与 Python 校验器同一语义。 */
export function resolveContent(data: Record<string, unknown>, ref?: string): unknown {
  if (!ref?.startsWith('data.')) return undefined;
  let current: unknown = data;
  for (const segment of ref.slice(5).split('.')) {
    const match = /^([^\[\]]+)(?:\[(\d+)\])?$/.exec(segment);
    if (!match) return undefined;
    const name = match[1]!;
    const index = match[2];
    if (!current || typeof current !== 'object' || !(name in (current as Record<string, unknown>))) return undefined;
    current = (current as Record<string, unknown>)[name];
    if (index !== undefined) {
      if (!Array.isArray(current) || Number(index) >= current.length) return undefined;
      current = current[Number(index)];
    }
  }
  return current;
}

export function motionStyle(scene: Scene, nodeId: string, frame: number, baseTransform = '', stylePack?: string, beats: BeatContext = EMPTY_BEAT_CONTEXT): CSSProperties {
  const motion = sceneMotionPlan(scene, beats.timeline).motions.find((item) => item.target === nodeId);
  if (!motion) return baseTransform ? { transform: baseTransform } : {};
  const eased = motionProgress(motion, frame);
  const common: CSSProperties = { opacity: eased };
  const riseDistance = stylePackDefinition(stylePack).riseDistance;
  if (motion.recipe === 'rise') return { ...common, transform: `${baseTransform} translateY(${(1 - eased) * riseDistance}px) scale(${0.96 + eased * 0.04})`.trim() };
  if (motion.recipe === 'reveal') return baseTransform ? { ...common, transform: baseTransform, clipPath: `inset(0 ${(1 - eased) * 100}% 0 0)` } : { ...common, clipPath: `inset(0 ${(1 - eased) * 100}% 0 0)` };
  if (motion.recipe === 'draw') return { ...common, transform: `${baseTransform} scaleX(${eased})`.trim(), transformOrigin: 'left center' };
  if (baseTransform) return { ...common, transform: baseTransform };
  return common;
}

/**
 * 预设取档的纯函数核：从声明档位开始，沿阶梯向下找第一个「放得下」的档位。
 * `fits` 由调用方用实测宽度实现；全部放不下时落到最小档并如实报告已实测。
 */
export function fitRoleDown(declared: string, fits: (role: string) => boolean): { role: string; measured: boolean } {
  if (fits(declared)) return { role: declared, measured: true };
  const start = ROLE_LADDER.indexOf(declared as (typeof ROLE_LADDER)[number]);
  for (let index = Math.max(start, 0) + 1; index < ROLE_LADDER.length; index += 1) {
    const candidate = ROLE_LADDER[index]!;
    if (fits(candidate)) return { role: candidate, measured: true };
  }
  return { role: ROLE_LADDER[ROLE_LADDER.length - 1]!, measured: true };
}

function textValue(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map((item) => typeof item === 'object' && item ? String((item as Record<string, unknown>).label ?? (item as Record<string, unknown>).id ?? '') : String(item)).join(' · ');
  return '';
}

export function layoutStyle(node: SceneNode): CSSProperties {
  const gap = GAP[node.gap ?? 'md']; const alignItems = node.align === 'start' ? 'flex-start' : node.align === 'end' ? 'flex-end' : node.align === 'stretch' ? 'stretch' : 'center';
  if (node.type === 'row' || node.type === 'column' || node.type === 'stack' || node.type === 'group') return { display: 'flex', flexDirection: node.type === 'row' || node.direction === 'horizontal' ? 'row' : 'column', alignItems, justifyContent: 'center', gap, width: '100%' };
  if (node.type === 'split') { const columns = { '1:1': '1fr 1fr', '1:2': '1fr 2fr', '2:1': '2fr 1fr', '2:3': '2fr 3fr', '3:2': '3fr 2fr' }[node.ratio ?? '1:1']; return { display: 'grid', gridTemplateColumns: columns, alignItems, gap, width: '100%' }; }
  if (node.type === 'grid') return { display: 'grid', gridTemplateColumns: `repeat(${node.columns ?? 2}, minmax(0, 1fr))`, gap, width: '100%' };
  if (node.type === 'overlay') return { display: 'grid', placeItems: 'center', width: '100%' };
  if (node.type === 'radial') return { position: 'relative', display: 'block', width: '100%', height: 520 };
  // flow 与 timeline 都沿方向轴排列；timeline 额外把轴与进度画在容器上（见下）
  if (node.type === 'flow') return { display: 'flex', flexDirection: axisOf(node.direction).flex, alignItems, justifyContent: 'center', gap, width: '100%' };
  if (node.type === 'timeline') return { position: 'relative', display: 'flex', flexDirection: axisOf(node.direction).flex, alignItems, justifyContent: 'space-between', gap, width: '100%' };
  if (node.type === 'cycle') return { position: 'relative', display: 'block', width: '100%', height: 560 };
  return {};
}

/**
 * radial 子节点的确定性圆周布局：角度只由「第几个 / 共几个」决定，
 * 相同输入永远得到相同几何（纯函数，无测量、无随机）。
 * 首个节点从正上方开始，沿顺时针均匀分布。
 */
export function radialChildStyle(index: number, total: number): CSSProperties {
  const angle = ((-90 + (360 / Math.max(total, 1)) * index) * Math.PI) / 180;
  return {
    position: 'absolute',
    // max-content：绝对定位的收缩适应会被容器边缘压窄，导致文字竖排
    width: 'max-content',
    maxWidth: 'none',
    left: `${50 + 40 * Math.cos(angle)}%`,
    top: `${50 + 38 * Math.sin(angle)}%`,
    transform: 'translate(-50%, -50%)',
  };
}

/** 图表数据点：label/value 全部来自分镜内容，缺数值的点不参与几何。 */
function chartPoints(value: unknown): Array<{ label: string; value: number }> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (item && typeof item === 'object' ? (item as Record<string, unknown>) : {}))
    .filter((point) => typeof point.value === 'number' && Number.isFinite(point.value))
    .map((point) => ({ label: String(point.label ?? ''), value: point.value as number }));
}

/* ------------------------------------------------------------------ */
/* 中层原语：阶段状态与量级比例                                          */
/* ------------------------------------------------------------------ */

/** 阶段容器的阶段状态：只由子节点顺序与共享 beat 时间轴决定。 */
export interface StageState {
  /** 当前阶段的子节点下标；当前帧没有活动 beat 时为 -1。 */
  active: number;
  /** 每个阶段是否已经结束（曾经被某个已结束的 beat 引用过）。 */
  done: boolean[];
}

/**
 * 求某一帧的阶段状态。
 *
 * 阶段就是子节点的顺序：当前 beat 指向哪个子节点，哪个就是当前阶段。
 * 求值只读 `timeline` 与 `frame`，不看 DOM、不测尺寸、不累积状态，
 * 因此同一帧重复求值结果一致，节点数量与基础几何也不会随帧变化。
 */
export function stageState(children: SceneNode[], timeline: BeatTimeline, frame: number): StageState {
  const done = children.map((child) => timeline.beats.some((beat) => beat.endFrame <= frame && beat.targets.includes(child.id)));
  const activeBeat = timeline.beats.find((beat) => beat.startFrame <= frame && frame < beat.endFrame);
  const active = activeBeat ? children.findIndex((child) => activeBeat.targets.includes(child.id)) : -1;
  return { active, done };
}

/**
 * 闭环轨道上的阶段位置：逆时针只是把同一个确定性圆周布局的顺序倒过来，
 * 位置集合完全相同——几何仍然只由「第几个 / 共几个」决定。
 */
export function cycleChildStyle(index: number, total: number, direction?: string): CSSProperties {
  return radialChildStyle(direction === 'ccw' ? (total - index) % total : index, total);
}

/**
 * 量级类原语在当前帧显示的比例（0..1）。
 *
 * 由 beat 的**动作**与**局部进度**决定：累积类从 0 推到满值，消耗类从满值
 * 退到 0，其余动作保持满值。没有被任何 beat 引用时恒为 1（旧分镜行为不变）。
 * 函数是纯的——不读挂钟、不累积上一帧的状态。
 */
export function quantityFactor(beat: NodeBeatState): number {
  if (!beat.targeted) return 1;
  const active = beat.active;
  if (active) {
    if (active.action === 'deplete' || active.action === 'break') return 1 - beat.progress;
    if (active.action === 'accumulate' || active.action === 'transfer' || active.action === 'restore') return beat.progress;
    return 1;
  }
  const last = beat.done[beat.done.length - 1];
  // 还没轮到它时起点为零，而不是先显示终值再倒着演一遍
  if (!last) return 0;
  return last.action === 'deplete' || last.action === 'break' ? 0 : 1;
}

/** 量级内容：0–100 的数值，非法或越界时取边界值而不是 NaN。 */
export function quantityValue(scene: Scene, node: SceneNode): number {
  const raw = Number(resolveContent(scene.data, node.contentRef));
  return Number.isFinite(raw) ? Math.min(100, Math.max(0, raw)) : 0;
}

/** 阶段推进比例：当前阶段含在内，供轨道与轴线显示「走到哪了」。 */
export function stageProgress(stage: StageState, total: number): number {
  if (total <= 0) return 0;
  const reached = stage.active >= 0 ? stage.active + 1 : stage.done.filter(Boolean).length;
  return Math.min(1, reached / total);
}

/* ------------------------------------------------------------------ */
/* 中层原语：方向连接与阶段指示                                          */
/* ------------------------------------------------------------------ */

/** 相邻阶段之间的方向连接：箭头朝向只由 `direction` 决定，与帧号无关。 */
function FlowArrow({ direction }: { direction?: string }): ReactNode {
  return (
    <span className="a2v-flow-arrow" data-a2v-relation="flow" data-a2v-direction={direction ?? 'ltr'} aria-hidden="true">
      <svg viewBox="0 0 24 24" width="30" height="30" style={{ transform: CONNECTOR_TURN[direction ?? 'ltr'] ?? 'none' }}>
        <path d="M3 12h14M12 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

/** 在相邻阶段之间插入方向连接：`flow` 与「只是排成一行」的区别就在这里。 */
function withFlowArrows(children: ReactNode[], direction?: string): ReactNode[] {
  return children.flatMap((child, index) => (index === 0 ? [child] : [<FlowArrow key={`flow-arrow-${index}`} direction={direction} />, child]));
}

const CYCLE_RADIUS = 42;
const CYCLE_CIRCUMFERENCE = 2 * Math.PI * CYCLE_RADIUS;

/**
 * 闭环轨道：底圈 + 按当前阶段推进的高亮弧 + 切向箭头。
 * 箭头画在轨道正上方并沿切线指向行进方向，因此 `cw` / `ccw` 一眼可辨。
 */
function CycleRing({ direction, progress }: { direction?: string; progress: number }): ReactNode {
  const counter = direction === 'ccw';
  return (
    <svg className="a2v-cycle-ring" viewBox="0 0 100 100" aria-hidden="true">
      <circle className="a2v-cycle-track" cx="50" cy="50" r={CYCLE_RADIUS} fill="none" strokeWidth="0.7" />
      <circle className="a2v-cycle-fill" cx="50" cy="50" r={CYCLE_RADIUS} fill="none" strokeWidth="1.4"
        strokeDasharray={`${CYCLE_CIRCUMFERENCE * progress} ${CYCLE_CIRCUMFERENCE}`}
        transform={counter ? 'rotate(-90 50 50) scale(-1 1) translate(-100 0)' : 'rotate(-90 50 50)'} />
      <polygon className="a2v-cycle-head" points={counter ? '56,3.5 56,16.5 45,10' : '44,3.5 44,16.5 55,10'} />
    </svg>
  );
}

/** 时间轴：轴线 + 按当前阶段推进的进度条。轴绝对定位，不参与子节点排版。 */
function TimelineAxis({ direction, progress }: { direction?: string; progress: number }): ReactNode {
  const axis = axisOf(direction);
  return (
    <span className="a2v-timeline-axis" data-a2v-relation="timeline" aria-hidden="true">
      <span className="a2v-timeline-fill" style={{ transform: `${axis.scale}(${progress})`, transformOrigin: axis.origin }} />
    </span>
  );
}

const GAUGE_TICKS = [0, 25, 50, 75, 100] as const;

/** 极坐标：0° 指向上方，顺时针为正。仪表盘的弧与指针都按它算。 */
function polar(angle: number, radius: number): [number, number] {
  const radians = ((angle - 90) * Math.PI) / 180;
  return [180 + radius * Math.cos(radians), 180 + radius * Math.sin(radians)];
}

function arcPath(from: number, to: number, radius: number): string {
  const [x1, y1] = polar(from, radius);
  const [x2, y2] = polar(to, radius);
  return `M ${x1} ${y1} A ${radius} ${radius} 0 ${Math.abs(to - from) > 180 ? 1 : 0} 1 ${x2} ${y2}`;
}

/**
 * 仪表盘：240° 刻度弧 + 填充弧 + 指针。
 *
 * 几何（viewBox、半径、刻度位置）在帧间完全固定，只有填充弧的角度与指针
 * 随 `factor` 变化，因此推进时容器与标签布局不重排。
 */
function GaugePrimitive({ scene, node, factor }: { scene: Scene; node: SceneNode; factor: number }): ReactNode {
  const value = quantityValue(scene, node);
  const shown = value * factor;
  const angle = -120 + (240 * shown) / 100;
  const [needleX, needleY] = polar(angle, 104);
  return (
    <div className="a2v-gauge" data-a2v-value={value} data-a2v-shown={Math.round(shown)}>
      <svg viewBox="0 0 360 320" role="img" aria-hidden="true">
        <path className="a2v-connector a2v-gauge-track" d={arcPath(-120, 120, 120)} strokeWidth="14" />
        {shown > 0 ? <path className="a2v-gauge-fill" d={arcPath(-120, angle, 120)} strokeWidth="14" /> : null}
        {GAUGE_TICKS.map((tick) => {
          const at = -120 + (240 * tick) / 100;
          const [x1, y1] = polar(at, 132);
          const [x2, y2] = polar(at, 146);
          return <line key={tick} className="a2v-connector a2v-gauge-tick" x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth="4" />;
        })}
        <line className="a2v-gauge-needle" x1="180" y1="180" x2={needleX} y2={needleY} strokeWidth="7" />
        <circle className="a2v-gauge-hub" cx="180" cy="180" r="12" />
      </svg>
      <div className="a2v-gauge-readout">
        <span className="a2v-numeric a2v-gauge-value">{Math.round(shown)}</span>
        <span className="a2v-caption">%</span>
        {node.schematic ? <span className="a2v-caption a2v-gauge-note">示意</span> : null}
      </div>
    </div>
  );
}

/** 象形图的单位数固定：帧间只改变填满几个，不改变总格数与网格。 */
const PICTOGRAM_UNITS = 10;

/** 象形图：固定 10 个受控图标单位，按比例填满。 */
function PictogramPrimitive({ scene, node, factor }: { scene: Scene; node: SceneNode; factor: number }): ReactNode {
  const value = quantityValue(scene, node);
  const filled = Math.round((value * factor * PICTOGRAM_UNITS) / 100);
  return (
    <div className="a2v-pictogram" data-a2v-units={PICTOGRAM_UNITS} data-a2v-filled={filled}>
      <div className="a2v-pictogram-units">
        {Array.from({ length: PICTOGRAM_UNITS }, (_, index) => (
          <span key={index} className="a2v-pictogram-unit" data-a2v-state={index < filled ? 'focus' : 'rest'} aria-hidden="true">
            <IconGlyph name={node.icon ?? 'check'} size={52} />
          </span>
        ))}
      </div>
      <div className="a2v-pictogram-readout">
        <span className="a2v-numeric a2v-pictogram-value">{Math.round(value * factor)}</span>
        <span className="a2v-caption">%</span>
        {node.schematic ? <span className="a2v-caption a2v-pictogram-note">示意</span> : null}
      </div>
    </div>
  );
}

/** 段落颜色：同一强调色的确定性明度阶梯，索引相同的输入永远得到相同颜色。 */
function segmentColor(index: number): string {
  const share = 100 - ((index % 6) * 16);
  return `color-mix(in srgb, var(--a2v-accent, #7aa2ff) ${share}%, transparent)`;
}

function BarChart({ points, schematic }: { points: Array<{ label: string; value: number }>; schematic?: boolean }): ReactNode {
  const max = Math.max(...points.map((point) => Math.abs(point.value)), 1);
  return (
    <div className="a2v-primitive-chart a2v-chart-bar">
      {points.map((point, index) => (
        <div key={index} className="a2v-primitive-bar" style={{ height: `${Math.max(8, (Math.abs(point.value) / max) * 100)}%` }}>
          <span>{point.label}</span>
        </div>
      ))}
      {schematic ? <small className="a2v-schematic">示意</small> : null}
    </div>
  );
}

function LineChart({ points, schematic }: { points: Array<{ label: string; value: number }>; schematic?: boolean }): ReactNode {
  const width = 720; const height = 360; const pad = 56;
  const values = points.map((point) => point.value);
  const min = Math.min(...values); const max = Math.max(...values); const span = max - min || 1;
  const step = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0;
  const coords = points.map((point, index) => ({ x: pad + index * step, y: height - pad - ((point.value - min) / span) * (height - pad * 2), label: point.label }));
  return (
    <div className="a2v-primitive-chart a2v-chart-line">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-hidden="true">
        <polyline points={coords.map((point) => `${point.x},${point.y}`).join(' ')} fill="none" stroke="var(--a2v-accent, #7aa2ff)" strokeWidth="6" strokeLinejoin="round" strokeLinecap="round" />
        {coords.map((point, index) => (
          <g key={index}>
            <circle cx={point.x} cy={point.y} r="10" fill="var(--a2v-accent, #7aa2ff)" />
            <text x={point.x} y={height - 18} textAnchor="middle" fontSize="22" fill="var(--a2v-text-1, currentColor)">{point.label}</text>
          </g>
        ))}
      </svg>
      {schematic ? <small className="a2v-schematic">示意</small> : null}
    </div>
  );
}

function PieChart({ points, schematic }: { points: Array<{ label: string; value: number }>; schematic?: boolean }): ReactNode {
  const total = points.reduce((sum, point) => sum + Math.abs(point.value), 0) || 1;
  const radius = 130; const circumference = 2 * Math.PI * radius;
  let consumed = 0;
  const segments = points.map((point, index) => {
    const fraction = Math.abs(point.value) / total;
    const segment = { dash: fraction * circumference, offset: consumed, color: segmentColor(index), label: point.label };
    consumed += fraction * circumference;
    return segment;
  });
  return (
    <div className="a2v-primitive-chart a2v-chart-pie">
      <svg viewBox="0 0 360 360" role="img" aria-hidden="true">
        {segments.map((segment, index) => (
          <circle key={index} cx="180" cy="180" r={radius} fill="none" stroke={segment.color} strokeWidth="56"
            strokeDasharray={`${segment.dash} ${circumference - segment.dash}`} strokeDashoffset={-segment.offset}
            transform="rotate(-90 180 180)" />
        ))}
      </svg>
      <div className="a2v-chart-legend">
        {segments.map((segment, index) => (
          <span key={index} className="a2v-chart-legend-item">
            <i style={{ background: segment.color }} />{segment.label}
          </span>
        ))}
      </div>
      {schematic ? <small className="a2v-schematic">示意</small> : null}
    </div>
  );
}

/** 文字原语：预设启用且节点声明了字号档（role）时，按实测宽度向下取档。 */
function TextPrimitive({ node, scene, preset }: { node: SceneNode; scene: Scene; preset: boolean }): ReactNode {
  const text = textValue(resolveContent(scene.data, node.contentRef));
  const declared = node.role ?? 'body';
  const spanRef = useRef<HTMLSpanElement | null>(null);
  const [role, setRole] = useState<string>(declared);
  useLayoutEffect(() => {
    const span = spanRef.current;
    // 宿主就是包裹本原语的 .a2v-primitive 容器（span 的父元素）
    const host = span?.parentElement;
    if (!preset || !node.role || !span || !host) return;
    const fits = (candidate: string): boolean => {
      span.className = ROLE_CLASS[candidate] ?? ROLE_CLASS.body!;
      return span.scrollWidth <= host.clientWidth;
    };
    const result = fitRoleDown(node.role, fits);
    setRole(result.role);
    // 档位与是否实测记录在节点上，契约探针据此检查取档行为
    host.dataset.a2vFitRole = result.role;
    host.dataset.a2vFitMeasured = String(result.measured);
  }, [preset, node.role, text]);
  return <span ref={spanRef} className={ROLE_CLASS[role] ?? ROLE_CLASS.body}>{text}</span>;
}

function PrimitiveBody({ node, scene, frame, preset, beats }: { node: SceneNode; scene: Scene; frame: number; preset: boolean; beats: BeatContext }): ReactNode {
  if (node.type === 'text') return <TextPrimitive node={node} scene={scene} preset={preset} />;
  if (node.type === 'number') {
    const raw = Number(resolveContent(scene.data, node.contentRef));
    const planned = sceneMotionPlan(scene, beats.timeline).motions.find((item) => item.target === node.id && item.recipe === 'count');
    const p = planned ? motionProgress(planned, frame) : 1;
    return <><span className="a2v-numeric">{Number.isFinite(raw) ? Math.round(raw * p) : textValue(resolveContent(scene.data, node.contentRef))}</span>{node.schematic ? <span className="a2v-caption">示意</span> : null}</>;
  }
  if (node.type === 'image') return <img src={textValue(resolveContent(scene.data, node.sourceRef))} alt="" />;
  if (node.type === 'icon') return <IconGlyph name={node.icon} size={96} />;
  if (node.type === 'gauge' || node.type === 'pictogram') {
    // 量级由 beat 的局部进度驱动：同帧重复求值结果一致，也不读挂钟。
    const factor = quantityFactor(nodeBeatState(beats.timeline, frame, node.id));
    return node.type === 'gauge' ? <GaugePrimitive scene={scene} node={node} factor={factor} /> : <PictogramPrimitive scene={scene} node={node} factor={factor} />;
  }
  if (node.type === 'shape') return null;
  if (node.type === 'connector') {
    const turn = CONNECTOR_TURN[node.direction ?? 'ltr'] ?? 'none';
    return (
      <svg viewBox="0 0 160 32" width="160" height="32" aria-hidden="true" style={{ transform: turn }}>
        <line x1="4" y1="16" x2="132" y2="16" stroke="var(--a2v-accent, #7aa2ff)" strokeWidth="4" strokeLinecap="round" />
        <polygon points="132,6 154,16 132,26" fill="var(--a2v-accent, #7aa2ff)" />
      </svg>
    );
  }
  if (node.type === 'chart') {
    const points = chartPoints(resolveContent(scene.data, node.contentRef));
    if (node.chart === 'line') return <LineChart points={points} schematic={node.schematic} />;
    if (node.chart === 'pie') return <PieChart points={points} schematic={node.schematic} />;
    return <BarChart points={points} schematic={node.schematic} />;
  }
  return null;
}

interface PrimitiveProps { node: SceneNode; scene: Scene; frame: number; preset: boolean; beats: BeatContext; stylePack?: string; continuity?: ContinuityRenderState; continuityVisible?: ReadonlySet<string> | null; place?: CSSProperties; baseTransform?: string; stage?: 'active' | 'done' | 'pending' }

function Primitive({ node, scene, frame, preset, beats, stylePack, continuity, continuityVisible, place, baseTransform = '', stage }: PrimitiveProps): React.ReactElement {
  // 阶段容器自己算阶段：子节点的顺序就是阶段顺序，当前 beat 指向哪个就走哪一步。
  const stages = node.children && STAGE_CONTAINERS.has(node.type) ? stageState(node.children, beats.timeline, frame) : null;
  const total = node.children?.length ?? 0;
  const children = node.children?.map((child, index) => (
    <Primitive
      key={child.id}
      node={child}
      scene={scene}
      frame={frame}
      preset={preset}
      beats={beats}
      stylePack={stylePack}
      continuity={continuity}
      continuityVisible={continuityVisible}
      place={node.type === 'radial' ? radialChildStyle(index, total)
        : node.type === 'cycle' ? cycleChildStyle(index, total, node.direction)
        : undefined}
      baseTransform={node.type === 'radial' || node.type === 'cycle' ? 'translate(-50%, -50%)' : ''}
      stage={stages ? (stages.active === index ? 'active' : stages.done[index] ? 'done' : 'pending') : undefined}
    />
  ));
  // 节点级节拍状态：视觉混合与探针必须读取同一份逐帧结果。
  const beat = nodeBeatState(beats.timeline, frame, node.id);
  const nodeMotion = motionStyle(scene, node.id, frame, baseTransform, stylePack, beats);
  const continuityStyle = continuityNodeStyle(node.id, continuity);
  const mix = visualMix(node.state ?? (stage === 'active' ? 'focus' : stage === 'done' ? 'done' : 'rest'), beat.active ? beat.progress : 1);
  // 变换通道只拼「动效 + 连续性」：基础变换已经由 motionStyle 带进 nodeMotion
  // （它拿到 baseTransform 后会原样保留，再叠加位移动效）。这里不能再把
  // place/layoutStyle 的 transform 作为 base 传一次——radial 与 cycle 的子节点
  // 靠 `translate(-50%,-50%)` 居中，重复叠加会把它们整体再上移、左移半个身位，
  // 表现为圆环上的卡片脱环、顶部卡片压住标题。
  const layered = channelStyle({ motion: typeof nodeMotion.transform === 'string' ? nodeMotion.transform : undefined, continuity: typeof continuityStyle.transform === 'string' ? continuityStyle.transform : undefined, opacity: Number(nodeMotion.opacity ?? 1) * Number(continuityStyle.opacity ?? 1), mix });
  const style = {
    ...(place ?? layoutStyle(node)),
    ...nodeMotion,
    ...(continuityVisible && !continuityVisible.has(node.id) ? { visibility: 'hidden' as const } : {}),
    ...continuityNodeStyle(node.id, continuity),
    ...layered,
  };
  // 同一状态写进 DOM，让契约探针量到真实画面而不是另算一遍分镜。
  const beatState = !beat.targeted ? undefined : beat.active ? 'active' : beat.done.length > 0 ? 'done' : 'pending';
  // 阶段容器把当前阶段映射到注册表已有的可视状态：不改注册表、不新造状态。
  const stageAttr = stage === 'active' ? 'focus' : stage === 'done' ? 'done' : undefined;
  const attrs = {
    'data-a2v-node-id': node.id, 'data-a2v-primitive': node.type,
    'data-a2v-inside': node.type === 'surface' ? '' : undefined,
    'data-a2v-motion': scene.motions.some((item) => item.target === node.id || item.targets?.includes(node.id)) ? '' : undefined,
    'data-a2v-focus-mix': mix.focus.toFixed(4),
    'data-a2v-muted-mix': mix.muted.toFixed(4),
    'data-a2v-done-mix': mix.done.toFixed(4),
    'data-a2v-continuity-phase': continuity && (continuity.relation.sourceIds.includes(node.id) || continuity.relation.targetIds.includes(node.id)) ? continuity.phase : undefined,
    'data-a2v-beat-state': beatState,
    'data-a2v-beat-action': beat.active?.action,
    'data-a2v-beat-progress': beat.active ? beat.progress.toFixed(4) : undefined,
    // 注意：**不能**写成 `data-a2v-stage`——那是画布容器的属性（`[data-a2v-stage]`
    // 在 base.css 里声明 1080×1920 与 overflow:hidden）。同名会让每个阶段子节点
    // 撑成整块画布并把标题挤出安全区，这里用 `-state` 保持两个命名空间互不干扰。
    'data-a2v-stage-state': stage,
    style,
  };
  const shapeClass = node.type === 'shape' ? ` a2v-shape-${node.shape ?? 'circle'}` : '';
  const body = node.children
    ? node.type === 'flow' ? withFlowArrows(children!, node.direction)
      : node.type === 'cycle' ? [<CycleRing key="cycle-ring" direction={node.direction} progress={stageProgress(stages!, total)} />, ...children!]
      : node.type === 'timeline' ? [<TimelineAxis key="timeline-axis" direction={node.direction} progress={stageProgress(stages!, total)} />, ...children!]
      : children
    : <PrimitiveBody node={node} scene={scene} frame={frame} preset={preset} beats={beats} />;
  return <div {...attrs} data-a2v-state={node.state ?? stageAttr ?? 'rest'} className={`a2v-primitive a2v-primitive-${node.type}${shapeClass}`}>{body}</div>;
}

export function SceneTree({ scene, frame, preset = false, beats = EMPTY_BEAT_CONTEXT, stylePack, continuity }: { scene: Scene; frame: number; preset?: boolean; beats?: BeatContext; stylePack?: string; continuity?: ContinuityRenderState }): React.ReactElement {
  // code 场景由共享 composition 的代码包装器承载，不会走到这里；
  // 缺少场景树说明分镜绕过了 schema 校验，这里直接报错而不是渲染 undefined。
  const tree = scene.sceneTree;
  if (!tree) throw new Error(`场景 ${scene.id} 缺少场景树：tree 场景必须声明 sceneTree`);
  const continuityVisible = continuityVisibleIds(tree, continuity);
  return <Primitive node={tree} scene={scene} frame={frame} preset={preset} beats={beats} stylePack={stylePack} continuity={continuity} continuityVisible={continuityVisible} />;
}
