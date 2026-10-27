/**
 * 二维绘制原语：把作品给的数值画到 Canvas 2D 上，并同时记下量测所需的几何。
 *
 * 三条硬约束（与 `primitives.ts` 一致）：
 *
 * 1. 不读挂钟、随机源、上一帧状态或组件计时器。画面只由调用方给出的帧号或
 *    受控时间决定，因此逐帧录制、跳帧采样与重录结果一致。
 * 2. 不内置颜色、字体或主题。默认值是中性白与无衬线，由调用方覆盖。
 * 3. 所有绘制都记入一份清单（`marks`）。量测代理读的就是这份清单——视觉与
 *    量测共用同一次布局计算，不靠另写一套估算。
 *
 * 坐标一律是逻辑坐标；画布后备缓冲的像素密度由 `Painter` 统一换算。
 */

export type Point = [number, number];

/** 一次绘制的记录，供量测代理转成 `data-m2v-role` 元素。 */
export type Mark = {
  role: string;
  state: string;
  /** 逻辑坐标下的包围盒。 */
  x: number;
  y: number;
  width: number;
  height: number;
  text?: string;
  fontSize?: number;
  color?: string;
};

export type TextOptions = {
  font?: string;
  size?: number;
  color?: string;
  alpha?: number;
  align?: 'left' | 'center' | 'right';
  baseline?: CanvasTextBaseline;
  track?: number;
  glow?: number;
  glowColor?: string;
  /** 记入量测清单时的角色；不填则不记。 */
  role?: string;
  state?: string;
  /** 量测用的可见性开关：传 false 时不进清单。 */
  measurable?: boolean;
};

export type ShapeOptions = {
  color?: string;
  fill?: string;
  width?: number;
  alpha?: number;
  glow?: number;
  glowColor?: string;
  dash?: number[];
};

export type GroupOptions = {
  alpha?: number;
  at?: Point;
  rotate?: number;
  scale?: number | Point;
  blur?: number;
  clip?: [number, number, number, number];
  additive?: boolean;
};

const DEFAULT_TEXT: Required<Pick<TextOptions, 'font' | 'size' | 'color' | 'alpha' |
  'align' | 'baseline' | 'track' | 'glow'>> = {
  font: 'sans-serif', size: 48, color: '#F8F9F8', alpha: 1,
  align: 'center', baseline: 'middle', track: 0, glow: 0,
};

function rgba(color: string, alpha: number): string {
  if (!color.startsWith('#')) return color;
  const hex = color.slice(1);
  const full = hex.length === 3 ? hex.split('').map(c => c + c).join('') : hex;
  if (full.length !== 6) return color;
  const r = parseInt(full.slice(0, 2), 16), g = parseInt(full.slice(2, 4), 16), b = parseInt(full.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, alpha))})`;
}

/**
 * 一帧的绘制上下文。
 *
 * 每个场景每帧新建一个实例：清单是新的，不跨帧累积。
 */
export class Painter {
  readonly ctx: CanvasRenderingContext2D;
  /** 逻辑尺寸；后备缓冲是它的 `scale` 倍。 */
  readonly width: number;
  readonly height: number;
  readonly scale: number;
  /** 本帧绘制清单，按绘制顺序排列。 */
  readonly marks: Mark[] = [];

  constructor(ctx: CanvasRenderingContext2D, width: number, height: number, scale = 1) {
    if (!Number.isFinite(scale) || scale <= 0) throw new RangeError('采集像素密度必须是正数');
    this.ctx = ctx;
    this.width = width;
    this.height = height;
    this.scale = scale;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.textBaseline = DEFAULT_TEXT.baseline;
  }

  /** 清空并铺一层不透明底；作品必须在 `ready()` 前铺满画布。 */
  clear(color = '#000000'): void {
    const {ctx} = this;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, this.width * this.scale, this.height * this.scale);
    ctx.restore();
  }

  /** 记录一个可量测对象；`measurable: false` 时跳过。 */
  mark(mark: Mark, measurable = true): void {
    if (measurable) this.marks.push(mark);
  }

  /** 在一组变换、透明度、混合或裁剪里画。 */
  group(options: GroupOptions, draw: () => void): void {
    const {ctx} = this;
    ctx.save();
    if (options.alpha != null) ctx.globalAlpha *= Math.max(0, Math.min(1, options.alpha));
    if (options.additive) ctx.globalCompositeOperation = 'lighter';
    if (options.at) ctx.translate(options.at[0], options.at[1]);
    if (options.rotate) ctx.rotate(options.rotate);
    if (options.scale != null) {
      const value = Array.isArray(options.scale) ? options.scale : [options.scale, options.scale];
      ctx.scale(value[0], value[1]);
    }
    if (options.blur) ctx.filter = `blur(${options.blur}px)`;
    if (options.clip) {
      ctx.beginPath();
      ctx.rect(options.clip[0], options.clip[1], options.clip[2], options.clip[3]);
      ctx.clip();
    }
    draw();
    ctx.restore();
  }

  /** 径向柔光，加法混合。越亮的物体光晕越大是这套出帧的自然结果。 */
  glow(x: number, y: number, radius: number, color = '#FFFFFF', alpha = 1): void {
    if (alpha <= 0 || radius <= 0) return;
    const {ctx} = this;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, rgba(color, alpha));
    gradient.addColorStop(.25, rgba(color, alpha * .55));
    gradient.addColorStop(.6, rgba(color, alpha * .12));
    gradient.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = gradient;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
    ctx.restore();
  }

  /** 光点：小白核 + 两层色晕。 */
  spark(x: number, y: number, radius: number, color = '#F8D893', alpha = 1): void {
    this.glow(x, y, radius * 4.2, color, alpha * .34);
    this.glow(x, y, radius * 1.6, color, alpha * .8);
    this.glow(x, y, radius * .8, '#FFFFFF', alpha);
  }

  /** 带渐隐尾迹的光点；`angle` 是运动方向，尾巴拖在身后。 */
  comet(x: number, y: number, length: number, radius: number, color = '#DCEBFF',
        alpha = 1, angle = 0): void {
    const {ctx} = this;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.translate(x, y);
    ctx.rotate(angle);
    const gradient = ctx.createLinearGradient(-length, 0, 0, 0);
    gradient.addColorStop(0, rgba(color, 0));
    gradient.addColorStop(.7, rgba(color, alpha * .35));
    gradient.addColorStop(1, rgba('#FFFFFF', alpha));
    ctx.strokeStyle = gradient;
    ctx.lineWidth = radius * .62;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(-length, 0);
    ctx.lineTo(0, 0);
    ctx.stroke();
    ctx.restore();
    this.spark(x, y, radius, color, alpha);
  }

  line(x1: number, y1: number, x2: number, y2: number, options: ShapeOptions = {}): void {
    const {ctx} = this;
    ctx.save();
    this.applyStroke(options);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.restore();
  }

  /**
   * 折线；`options.k`（0–1）只画前 k 这么长——线"长出来"就靠它。
   */
  poly(points: Point[], options: ShapeOptions & {k?: number; close?: boolean} = {}): void {
    if (points.length < 2) return;
    const {ctx} = this;
    ctx.save();
    this.applyStroke(options);
    const k = options.k == null ? 1 : Math.max(0, Math.min(1, options.k));
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    if (k < 1) {
      const position = k * (points.length - 1);
      const index = Math.floor(position);
      const ratio = position - index;
      for (let step = 1; step <= index; step++) ctx.lineTo(points[step][0], points[step][1]);
      if (index < points.length - 1) {
        ctx.lineTo(points[index][0] + (points[index + 1][0] - points[index][0]) * ratio,
                   points[index][1] + (points[index + 1][1] - points[index][1]) * ratio);
      }
    } else {
      for (let step = 1; step < points.length; step++) ctx.lineTo(points[step][0], points[step][1]);
      if (options.close) ctx.closePath();
    }
    this.applyFill(options);
    if (options.fill) ctx.fill();
    if (options.color || options.width != null) ctx.stroke();
    ctx.restore();
  }

  /** 沿折线走到 k 处的坐标与切向角，用来给线头安一个光点。 */
  along(points: Point[], k: number): [number, number, number] {
    if (points.length < 2) return [points[0]?.[0] ?? 0, points[0]?.[1] ?? 0, 0];
    const position = Math.max(0, Math.min(1, k)) * (points.length - 1);
    const index = Math.min(points.length - 2, Math.floor(position));
    const ratio = position - index;
    const [x1, y1] = points[index], [x2, y2] = points[index + 1];
    return [x1 + (x2 - x1) * ratio, y1 + (y2 - y1) * ratio, Math.atan2(y2 - y1, x2 - x1)];
  }

  circle(cx: number, cy: number, radius: number, options: ShapeOptions = {}): void {
    this.ellipse(cx, cy, radius, radius, options);
  }

  ellipse(cx: number, cy: number, rx: number, ry: number,
          options: ShapeOptions & {rotate?: number} = {}): void {
    if (rx <= 0 || ry <= 0) return;
    const {ctx} = this;
    ctx.save();
    this.applyStroke(options);
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, options.rotate ?? 0, 0, Math.PI * 2);
    this.applyFill(options);
    if (options.fill) ctx.fill();
    if (options.color || options.width != null) ctx.stroke();
    ctx.restore();
  }

  rect(x: number, y: number, width: number, height: number,
       options: ShapeOptions & {radius?: number} = {}): void {
    const {ctx} = this;
    ctx.save();
    this.applyStroke(options);
    ctx.beginPath();
    if (options.radius) ctx.roundRect(x, y, width, height, options.radius);
    else ctx.rect(x, y, width, height);
    this.applyFill(options);
    if (options.fill) ctx.fill();
    if (options.color || options.width != null) ctx.stroke();
    ctx.restore();
  }

  /** SVG 路径字符串；摆放由 `at`/`rotate`/`scale` 控制。 */
  path(d: string, options: ShapeOptions & {at?: Point; rotate?: number; scale?: number} = {}): void {
    const {ctx} = this;
    ctx.save();
    if (options.at) ctx.translate(options.at[0], options.at[1]);
    if (options.rotate) ctx.rotate(options.rotate);
    if (options.scale != null) ctx.scale(options.scale, options.scale);
    this.applyStroke(options);
    const path = new Path2D(d);
    if (options.fill) {
      ctx.fillStyle = rgba(options.fill, options.alpha ?? 1);
      ctx.fill(path);
    }
    if (options.color) ctx.stroke(path);
    ctx.restore();
  }

  private applyStroke(options: ShapeOptions): void {
    const {ctx} = this;
    ctx.lineWidth = options.width ?? 2;
    ctx.strokeStyle = rgba(options.color ?? '#FFFFFF', options.alpha ?? 1);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.setLineDash(options.dash ?? []);
    if (options.glow) {
      ctx.shadowColor = rgba(options.glowColor ?? options.color ?? '#FFFFFF', .9);
      ctx.shadowBlur = options.glow;
    }
  }

  private applyFill(options: ShapeOptions): void {
    if (!options.fill) return;
    const {ctx} = this;
    ctx.fillStyle = rgba(options.fill, options.alpha ?? 1);
  }

  /** 文字宽度，用于排版与定稿前量最长的一句。 */
  measure(text: string, options: TextOptions = {}): number {
    const {ctx} = this;
    ctx.save();
    this.applyFont(options);
    const width = ctx.measureText(text).width;
    ctx.restore();
    return width;
  }

  /** 画一行字，返回宽度；给了 `role` 就记入量测清单。 */
  text(content: string, x: number, y: number, options: TextOptions = {}): number {
    const {ctx} = this;
    const settings = {...DEFAULT_TEXT, ...options};
    ctx.save();
    this.applyFont(settings, options.track ?? 0);
    const width = ctx.measureText(content).width;
    const left = settings.align === 'center' ? x - width / 2
      : settings.align === 'right' ? x - width : x;
    ctx.globalAlpha *= settings.alpha;
    if (settings.glow) {
      ctx.shadowColor = rgba(settings.glowColor ?? settings.color, .85);
      ctx.shadowBlur = settings.glow;
    }
    ctx.fillStyle = rgba(settings.color, 1);
    ctx.textAlign = 'left';
    ctx.fillText(content, left, y);
    ctx.restore();
    if (options.role) {
      const size = settings.size;
      this.mark({role: options.role, state: options.state ?? '',
                 x: left, y: y - size * .62, width, height: size * 1.24,
                 text: content, fontSize: size, color: settings.color},
                options.measurable !== false);
    }
    return width;
  }

  /**
   * 逐字画；`per` 返回每个字的覆盖样式——逐字显影、打字、单字变色都用它。
   * 记入清单时仍是整行一条，与 `text()` 一致，避免被当成多个对象。
   */
  chars(content: string, x: number, y: number, options: TextOptions = {},
        per?: (index: number, char: string) => Partial<TextOptions> | undefined): number {
    const {ctx} = this;
    const settings = {...DEFAULT_TEXT, ...options};
    const characters = Array.from(content);
    const track = settings.track;
    const widths = characters.map(char => {
      ctx.save();
      this.applyFont(settings, 0);
      const width = ctx.measureText(char).width;
      ctx.restore();
      return width;
    });
    const total = widths.reduce((sum, value) => sum + value, 0) + track * (characters.length - 1);
    let cursor = settings.align === 'center' ? x - total / 2
      : settings.align === 'right' ? x - total : x;
    const start = cursor;
    characters.forEach((char, index) => {
      const override = (per && per(index, char)) || {};
      const alpha = (override.alpha ?? 1) * settings.alpha;
      const color = override.color ?? settings.color;
      if (alpha > .003) {
        ctx.save();
        this.applyFont(settings, 0);
        ctx.globalAlpha *= Math.max(0, Math.min(1, alpha));
        const glow = override.glow ?? settings.glow;
        if (glow) {
          ctx.shadowColor = rgba(override.glowColor ?? color, .85);
          ctx.shadowBlur = glow;
        }
        ctx.fillStyle = rgba(color, 1);
        ctx.textAlign = 'left';
        ctx.fillText(char, cursor, y);
        ctx.restore();
      }
      cursor += widths[index] + track;
    });
    if (options.role) {
      const size = settings.size;
      this.mark({role: options.role, state: options.state ?? '',
                 x: start, y: y - size * .62, width: total, height: size * 1.24,
                 text: content, fontSize: size, color: settings.color},
                options.measurable !== false);
    }
    return total;
  }

  private applyFont(options: TextOptions, track?: number): void {
    const {ctx} = this;
    const size = options.size ?? DEFAULT_TEXT.size;
    ctx.font = `${size}px ${options.font ?? DEFAULT_TEXT.font}`;
    // `letterSpacing` 不是所有运行时都有；缺失时退化为无字距，位置仍由 layout 决定。
    if (track != null && 'letterSpacing' in ctx) {
      (ctx as unknown as {letterSpacing: string}).letterSpacing = `${track}px`;
    }
    ctx.textAlign = 'left';
  }

  linearGradient(x0: number, y0: number, x1: number, y1: number,
                 stops: [number, string, number?][]): CanvasGradient {
    const gradient = this.ctx.createLinearGradient(x0, y0, x1, y1);
    stops.forEach(([offset, color, alpha]) => gradient.addColorStop(offset, rgba(color, alpha ?? 1)));
    return gradient;
  }

  radialGradient(cx: number, cy: number, r0: number, r1: number,
                 stops: [number, string, number?][]): CanvasGradient {
    const gradient = this.ctx.createRadialGradient(cx, cy, r0, cx, cy, r1);
    stops.forEach(([offset, color, alpha]) => gradient.addColorStop(offset, rgba(color, alpha ?? 1)));
    return gradient;
  }
}
