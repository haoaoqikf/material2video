/**
 * 可数点阵：把一组归一化坐标批量画成圆点，按语义色分组。
 *
 * 1000 点规模下每个语义色只生成一条 path，不逐点创建节点，也不使用滤镜；
 * 强调点单独绘制，可带静态光环。组件只接收几何与色名，不知道样本量、均值或
 * 任何题材数字。
 */
import type {CSSProperties} from 'react';
import {T} from './kit';

export type DotTone = 'ivory' | 'gold' | 'ember' | 'muted' | 'line';
export type DotPoint = {x: number; y: number; tone?: DotTone};
export type DotEmphasis = {
  x: number; y: number; radius?: number; tone?: DotTone; halo?: boolean; opacity?: number;
};
export type DotBox = {x: number; y: number; width: number; height: number};

export type DotFieldProps = {
  box: DotBox;
  points: DotPoint[];
  /** 整体不透明度；用于段落溶解，不改变点的语义色。 */
  opacity?: number;
  /** 基础点半径；点阵密集时可降到 tokens 的下限。 */
  radius?: number;
  /** 0–1 揭示比例；按 points 数组顺序显示。 */
  reveal?: number;
  emphasis?: DotEmphasis[];
  /** 强调点单独的不透明度；不跟随基础点阵的整体淡化。 */
  emphasisOpacity?: number;
  style?: CSSProperties;
};

const TONE_COLORS: Record<DotTone, string> = {
  ivory: T.colors.ivory,
  gold: T.colors.gold,
  ember: T.colors.ember,
  muted: T.colors.muted,
  line: T.colors.line,
};

function fixed(value: number): string {
  return value.toFixed(2);
}

/** 用两段圆弧拼出圆点；比逐点 <circle> 更少的节点，也便于整色绘制。 */
function ring(cx: number, cy: number, radius: number): string {
  return `M${fixed(cx - radius)} ${fixed(cy)}`
    + `a${fixed(radius)} ${fixed(radius)} 0 1 0 ${fixed(radius * 2)} 0`
    + `a${fixed(radius)} ${fixed(radius)} 0 1 0 ${fixed(radius * -2)} 0`;
}

export default function DotField({
  box, points, opacity = 1, radius = T.dots.radius, reveal = 1, emphasis = [], emphasisOpacity = 1, style,
}: DotFieldProps) {
  const visible = Math.max(0, Math.min(points.length, Math.ceil(points.length * Math.max(0, Math.min(1, reveal)))));
  const groups = new Map<DotTone, string[]>();
  for (const point of points.slice(0, visible)) {
    const tone = point.tone ?? 'muted';
    const x = box.x + point.x * box.width;
    const y = box.y + point.y * box.height;
    const list = groups.get(tone) ?? [];
    list.push(ring(x, y, radius));
    groups.set(tone, list);
  }
  return (
    <svg
      width={box.x + box.width}
      height={box.y + box.height}
      viewBox={`0 0 ${Math.max(1, box.x + box.width)} ${Math.max(1, box.y + box.height)}`}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none', ...style}}
      aria-hidden
    >
      <g opacity={opacity}>
        {[...groups.entries()].map(([tone, paths]) => (
          <path key={tone} d={paths.join('')} fill={TONE_COLORS[tone]}/>
        ))}
      </g>
      <g opacity={emphasisOpacity}>
        {emphasis.map((dot, index) => {
          const x = box.x + dot.x * box.width;
          const y = box.y + dot.y * box.height;
          const dotRadius = dot.radius ?? T.dots.highlightRadius;
          const dotColor = TONE_COLORS[dot.tone ?? 'gold'];
          return (
            <g key={index} opacity={dot.opacity ?? 1}>
              {dot.halo ? (
                <circle cx={x} cy={y} r={dotRadius * 1.9} fill="none" stroke={dotColor}
                  strokeWidth={1.5} opacity={0.3}/>
              ) : null}
              <circle cx={x} cy={y} r={dotRadius} fill={dotColor}/>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

export {TONE_COLORS};
