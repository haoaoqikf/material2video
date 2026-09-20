import { useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import type { Scene, SceneNode } from '@/schema/storyboard';

const GAP = { none: 0, xs: 8, sm: 16, md: 28, lg: 44, xl: 64 } as const;
const ROLE_CLASS: Record<string, string> = { hero: 'a2v-hero', headline: 'a2v-headline', title: 'a2v-title', body: 'a2v-body', label: 'a2v-label', caption: 'a2v-caption' };
/** 字号档位从大到小。预设取档时沿这条阶梯向下找第一个放得下的档位。 */
export const ROLE_LADDER = ['hero', 'headline', 'title', 'body', 'label', 'caption'] as const;
const ICON_GLYPH: Record<string, string> = { arrow: '→', check: '✓', cross: '×', spark: '✦' };
const CONNECTOR_TURN: Record<string, string> = { ltr: 'none', rtl: 'scaleX(-1)', ttb: 'rotate(90deg)', btt: 'rotate(-90deg)' };

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

export function motionStyle(scene: Scene, nodeId: string, frame: number, baseTransform = ''): CSSProperties {
  const motion = scene.motions.find((item) => item.target === nodeId);
  if (!motion) return baseTransform ? { transform: baseTransform } : {};
  const duration = motion.durationFrames ?? 24;
  const progress = Math.min(1, Math.max(0, (frame - motion.startFrame) / duration));
  const eased = 1 - (1 - progress) ** 3;
  const common: CSSProperties = { opacity: eased };
  if (motion.recipe === 'rise') return { ...common, transform: `${baseTransform} translateY(${(1 - eased) * 36}px)`.trim() };
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

/** 段落颜色：同一强调色的确定性明度阶梯，索引相同的输入永远得到相同颜色。 */
function segmentColor(index: number): string {
  const share = 100 - ((index % 6) * 16);
  return `color-mix(in srgb, var(--a2v-accent, #7aa2ff) ${share}%, transparent)`;
}

function BarChart({ points, schematic }: { points: Array<{ label: string; value: number }>; schematic?: boolean }): ReactNode {
  const max = Math.max(...points.map((point) => Math.abs(point.value)), 1);
  return (
    <div className="a2v-primitive-chart">
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
            <text x={point.x} y={height - 18} textAnchor="middle" fontSize="22" fill="currentColor">{point.label}</text>
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

function PrimitiveBody({ node, scene, frame, preset }: { node: SceneNode; scene: Scene; frame: number; preset: boolean }): ReactNode {
  if (node.type === 'text') return <TextPrimitive node={node} scene={scene} preset={preset} />;
  if (node.type === 'number') {
    const raw = Number(resolveContent(scene.data, node.contentRef));
    const motion = scene.motions.find((item) => item.target === node.id && item.recipe === 'count');
    const p = motion ? Math.min(1, Math.max(0, (frame - motion.startFrame) / (motion.durationFrames ?? 30))) : 1;
    return <><span className="a2v-numeric">{Number.isFinite(raw) ? Math.round(raw * p) : textValue(resolveContent(scene.data, node.contentRef))}</span>{node.schematic ? <span className="a2v-caption">示意</span> : null}</>;
  }
  if (node.type === 'image') return <img src={textValue(resolveContent(scene.data, node.sourceRef))} alt="" />;
  if (node.type === 'icon') return <span aria-hidden="true">{ICON_GLYPH[node.icon ?? 'spark']}</span>;
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

interface PrimitiveProps { node: SceneNode; scene: Scene; frame: number; preset: boolean; place?: CSSProperties; baseTransform?: string }

function Primitive({ node, scene, frame, preset, place, baseTransform = '' }: PrimitiveProps): React.ReactElement {
  const children = node.children?.map((child, index) => (
    <Primitive
      key={child.id}
      node={child}
      scene={scene}
      frame={frame}
      preset={preset}
      place={node.type === 'radial' ? radialChildStyle(index, node.children!.length) : undefined}
      baseTransform={node.type === 'radial' ? 'translate(-50%, -50%)' : ''}
    />
  ));
  const style = { ...(place ?? layoutStyle(node)), ...motionStyle(scene, node.id, frame, baseTransform) };
  const attrs = { 'data-a2v-node-id': node.id, 'data-a2v-primitive': node.type, 'data-a2v-inside': node.type === 'surface' ? '' : undefined, 'data-a2v-motion': scene.motions.some((item) => item.target === node.id) ? '' : undefined, style };
  const shapeClass = node.type === 'shape' ? ` a2v-shape-${node.shape ?? 'circle'}` : '';
  const body = node.children ? children : <PrimitiveBody node={node} scene={scene} frame={frame} preset={preset} />;
  return <div {...attrs} data-a2v-state={node.state ?? 'rest'} className={`a2v-primitive a2v-primitive-${node.type}${shapeClass}`}>{body}</div>;
}

export function SceneTree({ scene, frame, preset = false }: { scene: Scene; frame: number; preset?: boolean }): React.ReactElement {
  return <Primitive node={scene.sceneTree} scene={scene} frame={frame} preset={preset} />;
}
