/** 圆片、柱/架/丘布局与画面文字：颜色只表示资金状态，不表示材质。 */
export const BG = '#090B10';
export const OFF_WHITE = '#F1ECDD';
export const GOLD = '#EBC668';
export const DARK_GOLD = '#8A6E38';
export const MUTED = '#AAA99E';
export const LINE = '#36383D';
export const FONT = 'M2V Sans, sans-serif';
export const RADIUS = 21;

export type DiscState = 'white' | 'gold' | 'dark';
export type Point = {x: number; y: number};

const FILL: Record<DiscState, string> = {white: OFF_WHITE, gold: GOLD, dark: DARK_GOLD};

export function mixColor(from: string, to: string, p: number) {
  const a = parseInt(from.slice(1), 16), b = parseInt(to.slice(1), 16);
  const t = Math.max(0, Math.min(1, p));
  const channel = (shift: number) => Math.round(((a >> shift) & 255) * (1 - t) + ((b >> shift) & 255) * t);
  return `rgb(${channel(16)},${channel(8)},${channel(0)})`;
}

export function Text({x, y, size = 40, color = OFF_WHITE, children, opacity = 1,
                      anchor = 'start', weight = 500}: {
  x: number; y: number; size?: number; color?: string; children: React.ReactNode;
  opacity?: number; anchor?: 'start' | 'middle' | 'end'; weight?: number;
}) {
  return <text data-m2v-role="body" x={x} y={y} fontSize={size} fill={color} opacity={opacity} textAnchor={anchor}
    fontWeight={weight} style={{fontFamily: FONT, fontVariantNumeric: 'tabular-nums'}}>{children}</text>;
}

/** 一枚圆片：平面圆 + 顶部高光弧 + 偏移暗影；不使用 filter，保证大量圆片逐帧可渲染。 */
export function Disc({x, y, r = RADIUS, state, opacity = 1, color, rim}: {
  x: number; y: number; r?: number; state?: DiscState; opacity?: number;
  color?: string; rim?: string;
}) {
  const fill = color ?? FILL[state ?? 'white'];
  const visibleState = discStateOf(fill);
  const highlight = `M${x - r * .64} ${y - r * .44}a${r * .74} ${r * .74} 0 0 1 ${r * .92} ${-r * .16}`;
  return <g opacity={opacity}>
    <ellipse cx={x + r * .10} cy={y + r * .26} rx={r * .94} ry={r * .86} fill="#030407" opacity={.55}/>
    <circle data-m2v-role="disc" data-m2v-state={visibleState} cx={x} cy={y} r={r} fill={fill}/>
    <path d={highlight} fill="none" stroke="#FFFFFF" strokeOpacity={.42} strokeWidth={Math.max(1, r * .05)}/>
    {rim && <circle cx={x} cy={y} r={Math.max(1, r - 1.2)} fill="none" stroke={rim}
      strokeWidth={Math.max(1, r * .05)} opacity={.55}/>}
  </g>;
}

function discStateOf(fill: string) {
  const normalized = fill.replace(/\s/g, '').toLowerCase();
  return normalized === OFF_WHITE.toLowerCase() || normalized === 'rgb(241,236,221)' ? 'white'
    : normalized === GOLD.toLowerCase() || normalized === 'rgb(235,198,104)' ? 'gold'
    : normalized === DARK_GOLD.toLowerCase() || normalized === 'rgb(138,110,56)' ? 'dark' : 'changing';
}

/** 柱：从底向上叠放，间距小于直径，像一摞硬币。 */
export function columnPositions(x: number, baseY: number, count: number, pitch = 28): Point[] {
  return Array.from({length: count}, (_, i) => ({x, y: baseY - i * pitch}));
}

/** 一行圆片：从左到右等距。 */
export function rowPositions(count: number, x0: number, y: number, gap = 42): Point[] {
  return Array.from({length: count}, (_, i) => ({x: x0 + i * gap, y}));
}

/**
 * S5 取出组：10 枚米白本金作底排，30 枚暗金分三排叠在其上，
 * 合起来是可数的 40 枚整块，而不是“柱 + 架”两个分离对象。
 */
export function withdrawBlockPositions(x0 = 300, baseY = 536, gap = 42) {
  return {
    white: rowPositions(10, x0, baseY, gap),
    dark: Array.from({length: 30}, (_, i) => ({
      x: x0 + (i % 10) * gap,
      y: baseY - (Math.floor(i / 10) + 1) * gap,
    })),
  };
}

/** 左侧留存架：3 行 × 10 列，按年份从左到右、从下到上填充。 */
export function shelfPositions(count: number, x0 = 100, y0 = 300, cols = 10, gap = 42): Point[] {
  return Array.from({length: count}, (_, i) => ({
    x: x0 + (i % cols) * gap, y: y0 + Math.floor(i / cols) * gap,
  }));
}

const HILL_ROWS = [26, 25, 24, 22, 20, 18, 16, 8];

/** 米白丘：8 行阶梯堆叠 + 确定性微抖，顶部一行中央留给第一年那枚。
 * 末行 8 枚包含 0.631 的分数圆片，使 158.631 个单位不被四舍五入掉。 */
export function hillPositions(count = 158, centerX = 1360, baseY = 940, pitch = 34, gap = 40): Point[] {
  const points: Point[] = [];
  for (let row = 0; row < HILL_ROWS.length; row++) {
    const n = HILL_ROWS[row];
    for (let i = 0; i < n; i++) {
      if (points.length >= count) return points;
      const jitterX = row === HILL_ROWS.length - 1 && i === 3 ? 0 : ((Math.sin((row * 31 + i) * 12.9898) * 43758.5453) % 1) * 3 - 1.5;
      const jitterY = row === HILL_ROWS.length - 1 && i === 3 ? 0 : ((Math.sin((row * 17 + i) * 78.233) * 12345.6789) % 1) * 2 - 1;
      points.push({x: centerX + (i - (n - 1) / 2) * gap + jitterX, y: baseY - row * pitch + jitterY});
    }
  }
  return points;
}

export const FIRST_DISC_INDEX = HILL_ROWS.slice(0, -1).reduce((a, b) => a + b, 0) + 3;
