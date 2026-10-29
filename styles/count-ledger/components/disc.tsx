/** 一枚可数圆片：平面圆 + 顶部高光弧 + 偏移暗影；不使用 filter，保证大量圆片逐帧可渲染。 */
import {T, discFill, type DiscState} from './kit';

export type DiscProps = {
  x: number;
  y: number;
  r?: number;
  state?: DiscState;
  opacity?: number;
  color?: string;
  rim?: string;
};

const STATE_NAMES: Record<string, DiscState> = {
  [T.colors.offWhite.toLowerCase()]: 'white',
  [T.colors.gold.toLowerCase()]: 'gold',
  [T.colors.darkGold.toLowerCase()]: 'dark',
};

function stateOf(fill: string, declared?: DiscState): DiscState | 'changing' {
  if (declared) return declared;
  const normalized = fill.replace(/\s/g, '').toLowerCase();
  return STATE_NAMES[normalized] ?? 'changing';
}

export default function Disc({x, y, r = T.disc.radius, state, opacity = 1, color, rim}: DiscProps) {
  const fill = color ?? discFill(state ?? 'white');
  const visibleState = stateOf(fill, state);
  const highlight = `M${x - r * 0.64} ${y - r * 0.44}a${r * 0.74} ${r * 0.74} 0 0 1 ${r * 0.92} ${-r * 0.16}`;
  return (
    <g opacity={opacity}>
      <ellipse
        cx={x + r * T.disc.shadowOffsetX}
        cy={y + r * T.disc.shadowOffsetY}
        rx={r * 0.94}
        ry={r * 0.86}
        fill={T.canvas.shadow}
        opacity={T.disc.shadowOpacity}
      />
      <circle data-m2v-role="disc" data-m2v-state={visibleState} cx={x} cy={y} r={r} fill={fill}/>
      <path
        d={highlight}
        fill="none"
        stroke="#FFFFFF"
        strokeOpacity={0.42}
        strokeWidth={Math.max(1, r * T.disc.highlightWidthRatio)}
      />
      {rim && (
        <circle
          cx={x}
          cy={y}
          r={Math.max(1, r - 1.2)}
          fill="none"
          stroke={rim}
          strokeWidth={Math.max(1, r * T.disc.highlightWidthRatio)}
          opacity={0.55}
        />
      )}
    </g>
  );
}
