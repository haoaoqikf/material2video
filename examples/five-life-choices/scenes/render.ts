/**
 * 人生五选择的 Canvas 绘制层。
 *
 * 只做一件事：给定 elapsedSeconds，把 geometry.ts 的世界画成一帧。
 * 不读挂钟、不累积状态、不用 CSS 动画；同一帧重复绘制结果一致。
 * 主造型是自发光细线；只在行业高度差、学习断头与结尾一级分支上使用窄光带承托。
 */
import {
  AGE_MARKS,
  CHART_Z,
  CITY_BUILDINGS,
  CITY_LANES,
  CITY_NETWORK,
  DECISION_AGES,
  INDUSTRY_LANES,
  INVEST_FLAT,
  INVEST_STEADY,
  LEARNING_BRIDGE,
  LEARNING_NODES,
  LEARNING_THREAD,
  MAIN_BEFORE,
  NEAR,
  NEW_PATH,
  PARTNER_LIFT,
  PARTNER_TRACKS,
  REALIZED,
  TREE_NODES,
  TREE_PATHS,
  YOUTH_BRANCHES,
  actAlpha,
  add,
  ageAt,
  ageX,
  cameraAt,
  cameraFrame,
  chartAgeAt,
  chartSubjectAt,
  chartY,
  clamp,
  curvePointAt,
  fogAlpha,
  industryDistance,
  lifeMarkPoint,
  mainPoint,
  projectPoint,
  projectView,
  seeded,
  span,
  subjectAt,
  subjectDistance,
  viewOf,
  type CameraFrame,
  type Projected,
  type Vec3,
  type Viewport,
} from './geometry';

// ------------------------------------------------------------------ 类型与配色

export type CopyItem = {
  id: string;
  text: string;
  from: number;
  to: number;
  size: number;
  weight: number;
  spacing: number;
  x: number;
  y: number;
  width: number;
  align: 'left' | 'center' | 'right';
  tone: 'primary' | 'secondary' | 'accent';
};

export type Labels = {
  ages: number[];
  cities: string[];
  cityNodes: string[];
  industries: string[];
  partnerLeft: string[];
  partnerRight: string[];
  learningUpper: string;
  learningLower: string;
  learningNodes: string[];
  choices: string[];
};

export type LifeProps = {copy: CopyItem[]; labels: Labels; shots?: unknown; stillT?: number};

const BG_TOP = '#05070a';
const BG_BOTTOM = '#020304';
const CREAM = '#f2f6fb';
const GRAY = '#9aa7b4';
const BLUE = '#9cc8ff';
const PALE = '#dbe9ff';
const INK = '#020407';
const RIDGE = '#0d1724';
const RIDGE_EDGE = '#6f9fc8';

const rgba = (hex: string, alpha: number) => {
  const value = hex.replace('#', '');
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${clamp(alpha)})`;
};

// ------------------------------------------------------------------ 投影与描边

const projection = (frame: CameraFrame, point: Vec3): Projected =>
  projectPoint(frame, point);

function clipProject(frame: CameraFrame, a: Vec3, b: Vec3): {a: Projected; b: Projected} | null {
  let va = viewOf(frame, a);
  let vb = viewOf(frame, b);
  if (va.z <= NEAR && vb.z <= NEAR) return null;
  if (va.z <= NEAR) {
    const u = (NEAR - va.z) / (vb.z - va.z);
    va = {x: va.x + (vb.x - va.x) * u, y: va.y + (vb.y - va.y) * u, z: NEAR};
  } else if (vb.z <= NEAR) {
    const u = (NEAR - vb.z) / (va.z - vb.z);
    vb = {x: vb.x + (va.x - vb.x) * u, y: vb.y + (va.y - vb.y) * u, z: NEAR};
  }
  return {a: projectView(frame, va), b: projectView(frame, vb)};
}

type StrokeStyle = {
  color: string;
  width: number;
  alpha?: number;
  glow?: number;
  dash?: number[];
  cap?: boolean;
};

/** 逐段投影描边：每段按深度调整透明度与线宽，近平面处插值裁剪。 */
function strokeWorld(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  points: Vec3[],
  style: StrokeStyle,
) {
  const base = style.alpha ?? 1;
  if (base <= 0.003) return;
  ctx.lineCap = style.cap === false ? 'butt' : 'round';
  ctx.lineJoin = 'round';
  for (let i = 0; i < points.length - 1; i += 1) {
    const clipped = clipProject(frame, points[i], points[i + 1]);
    if (!clipped) continue;
    const {a, b} = clipped;
    if (!a.visible || !b.visible) continue;
    const depth = (a.z + b.z) / 2;
    const alpha = base * fogAlpha(depth);
    if (alpha <= 0.004) continue;
    const rel = (a.rel + b.rel) / 2;
    const width = Math.max(0.45, Math.min(8, style.width * rel));
    if (style.glow) {
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = rgba(style.color, alpha * style.glow);
      ctx.lineWidth = width * 3.2;
      ctx.stroke();
    }
    if (style.dash) ctx.setLineDash(style.dash);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = rgba(style.color, alpha);
    ctx.lineWidth = width;
    ctx.stroke();
    if (style.dash) ctx.setLineDash([]);
  }
}

/** 整条路径一次描边；用于远景、树与不需要逐段变化的线。 */
function strokeWorldBatch(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  points: Vec3[],
  style: StrokeStyle,
) {
  if (points.length < 2) return;
  let sum = 0;
  let count = 0;
  let lastRel = 1;
  ctx.beginPath();
  let drawing = false;
  for (let i = 0; i < points.length - 1; i += 1) {
    const clipped = clipProject(frame, points[i], points[i + 1]);
    if (!clipped) {
      drawing = false;
      continue;
    }
    const {a, b} = clipped;
    if (!a.visible || !b.visible) continue;
    if (!drawing) {
      ctx.moveTo(a.x, a.y);
      drawing = true;
    }
    ctx.lineTo(b.x, b.y);
    sum += (a.z + b.z) / 2;
    lastRel = (a.rel + b.rel) / 2;
    count += 1;
  }
  if (!count) return;
  const alpha = (style.alpha ?? 1) * fogAlpha(sum / count);
  if (alpha <= 0.004) return;
  const width = Math.max(0.4, Math.min(7, style.width * lastRel));
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (style.glow) {
    ctx.strokeStyle = rgba(style.color, alpha * style.glow);
    ctx.lineWidth = width * 2.8;
    ctx.stroke();
  }
  if (style.dash) ctx.setLineDash(style.dash);
  ctx.strokeStyle = rgba(style.color, alpha);
  ctx.lineWidth = width;
  ctx.stroke();
  if (style.dash) ctx.setLineDash([]);
}

function fillQuad(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  a: Vec3,
  b: Vec3,
  c: Vec3,
  d: Vec3,
  color: string,
  alpha: number,
) {
  const pa = projection(frame, a);
  const pb = projection(frame, b);
  const pc = projection(frame, c);
  const pd = projection(frame, d);
  if (!pa.visible || !pb.visible || !pc.visible || !pd.visible) return;
  const depth = (pa.z + pb.z + pc.z + pd.z) / 4;
  const a2 = alpha * fogAlpha(depth);
  if (a2 <= 0.004) return;
  ctx.beginPath();
  ctx.moveTo(pa.x, pa.y);
  ctx.lineTo(pb.x, pb.y);
  ctx.lineTo(pc.x, pc.y);
  ctx.lineTo(pd.x, pd.y);
  ctx.closePath();
  ctx.fillStyle = rgba(color, a2);
  ctx.fill();
}

/** 窄光带：只在需要“实体跑道/断头/一级分支”时承托线条。 */
function fillRibbon(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  points: Vec3[],
  halfWidth: number,
  color: string,
  alpha: number,
  drop = 42,
) {
  const step = Math.max(1, Math.floor(points.length / 48));
  for (let i = 0; i < points.length - step; i += step) {
    const a = points[i];
    const b = points[Math.min(points.length - 1, i + step)];
    const a0: Vec3 = [a[0], a[1] - drop, a[2] - halfWidth];
    const a1: Vec3 = [a[0], a[1] - drop, a[2] + halfWidth];
    const b0: Vec3 = [b[0], b[1] - drop, b[2] - halfWidth];
    const b1: Vec3 = [b[0], b[1] - drop, b[2] + halfWidth];
    fillQuad(ctx, frame, a0, b0, b1, a1, color, alpha);
    fillQuad(ctx, frame, a, b, b1, a1, color, alpha * 0.42);
  }
}

/** 带体积感的线：窄带 + 宽光晕 + 亮芯。 */
function strokeRidge(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  points: Vec3[],
  style: {
    color: string;
    width: number;
    alpha: number;
    glow?: number;
    ribbon?: number;
    ribbonAlpha?: number;
    dash?: number[];
  },
) {
  if (style.ribbon) {
    fillRibbon(ctx, frame, points, style.ribbon, RIDGE, style.ribbonAlpha ?? style.alpha * 0.24);
  }
  strokeWorldBatch(ctx, frame, points, {
    color: style.color, width: style.width * 2.6, alpha: style.alpha * 0.18,
  });
  strokeWorldBatch(ctx, frame, points, {
    color: style.color, width: style.width * 1.35, alpha: style.alpha * 0.55,
    dash: style.dash,
  });
  strokeWorldBatch(ctx, frame, points, {
    color: style.color, width: style.width, alpha: style.alpha, glow: style.glow,
    dash: style.dash,
  });
}

function slice(points: Vec3[], progress: number): Vec3[] {
  if (progress >= 1) return points;
  const count = Math.max(2, Math.floor(points.length * clamp(progress)));
  return points.slice(0, count);
}

function dot3(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  point: Vec3,
  radius: number,
  color: string,
  alpha = 1,
) {
  const p = projection(frame, point);
  if (!p.visible) return;
  const r = clamp(radius * Math.max(0.5, p.rel), 1.4, radius * 3);
  const a = alpha * fogAlpha(p.z);
  if (a <= 0.01) return;
  ctx.fillStyle = rgba(color, a * 0.08);
  ctx.beginPath();
  ctx.arc(p.x, p.y, r * 3.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = rgba(color, a * 0.2);
  ctx.beginPath();
  ctx.arc(p.x, p.y, r * 2.0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = rgba(color, a);
  ctx.beginPath();
  ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
  ctx.fill();
}

function subjectGlow(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  point: Vec3,
  radius: number,
  alpha: number,
) {
  const p = projection(frame, point);
  if (!p.visible) return;
  const r = clamp(radius * Math.max(0.6, p.rel), 3, radius * 2.4);
  const a = alpha * fogAlpha(p.z);
  if (a <= 0.01) return;
  const halo = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 9);
  halo.addColorStop(0, rgba(BLUE, 0.22 * a));
  halo.addColorStop(0.35, rgba(BLUE, 0.08 * a));
  halo.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(p.x, p.y, r * 9, 0, Math.PI * 2);
  ctx.fill();
  // 地面光池：只是屏幕空间中的柔光，不宣称真实投影。
  const pool = ctx.createRadialGradient(p.x, p.y + r * 2.4, 0, p.x, p.y + r * 2.4, r * 4.2);
  pool.addColorStop(0, rgba(PALE, 0.13 * a));
  pool.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = pool;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y + r * 2.4, r * 4.2, r * 1.5, 0, 0, Math.PI * 2);
  ctx.fill();
  dot3(ctx, frame, point, radius, PALE, alpha);
}

function drawLabel(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  point: Vec3,
  text: string,
  size: number,
  alpha: number,
  color = CREAM,
  align: CanvasTextAlign = 'center',
  lift = 0,
  floor = 0.56,
) {
  const p = projection(frame, point);
  if (!p.visible) return;
  const s = size * clamp(p.rel, floor, 1.9);
  const a = alpha * fogAlpha(p.z) * clamp((p.rel - 0.18) / 0.34);
  if (a <= 0.02 || s < 11) return;
  ctx.font = `400 ${s.toFixed(1)}px "M2V Sans", sans-serif`;
  ctx.textAlign = align;
  ctx.textBaseline = 'middle';
  const textWidth = ctx.measureText(text).width;
  const leftMargin = align === 'right' ? textWidth + 12 : align === 'center' ? textWidth / 2 + 12 : 12;
  const rightMargin = align === 'left' ? textWidth + 12 : align === 'center' ? textWidth / 2 + 12 : 12;
  const x = clamp(p.x, frame.x0 + leftMargin, frame.x0 + frame.width - rightMargin);
  const y = p.y - lift * clamp(p.rel, 0.5, 1.7);
  if (y < 22 || y > 858) return;
  ctx.lineJoin = 'round';
  ctx.strokeStyle = rgba(INK, 0.92 * a);
  ctx.lineWidth = Math.max(4, s * 0.22);
  ctx.strokeText(text, x, y);
  ctx.fillStyle = rgba(color, a);
  ctx.fillText(text, x, y);
}

function drawScreenText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  size: number,
  alpha: number,
  color = CREAM,
  align: CanvasTextAlign = 'center',
) {
  if (alpha <= 0.01) return;
  ctx.font = `400 ${size}px "M2V Sans", sans-serif`;
  ctx.textAlign = align;
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = rgba(INK, 0.9 * alpha);
  ctx.lineWidth = Math.max(4, size * 0.2);
  ctx.strokeText(text, x, y);
  ctx.fillStyle = rgba(color, alpha);
  ctx.fillText(text, x, y);
}

// ------------------------------------------------------------------ 背景与地形

const DUST = (() => {
  const random = seeded(0x13579bdf);
  return Array.from({length: 110}, () => ({
    x: random(),
    y: random(),
    r: 0.5 + random() * 1.5,
    depth: 0.2 + random() * 0.8,
    phase: random() * Math.PI * 2,
  }));
})();

let bgCache: HTMLCanvasElement | null = null;
let bgKey = '';

function drawBackground(ctx: CanvasRenderingContext2D, t: number, w: number, h: number) {
  const key = `${w}x${h}`;
  if (!bgCache || bgKey !== key) {
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const g = canvas.getContext('2d');
    if (g) {
      const bg = g.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, BG_TOP);
      bg.addColorStop(0.58, '#04060a');
      bg.addColorStop(1, BG_BOTTOM);
      g.fillStyle = bg;
      g.fillRect(0, 0, w, h);
      const glow = g.createRadialGradient(w * 0.64, h * 0.48, 0, w * 0.64, h * 0.48, h * 0.86);
      glow.addColorStop(0, 'rgba(54, 92, 138, 0.15)');
      glow.addColorStop(0.42, 'rgba(28, 52, 82, 0.07)');
      glow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      g.fillStyle = glow;
      g.fillRect(0, 0, w, h);
    }
    bgCache = canvas;
    bgKey = key;
  }
  ctx.drawImage(bgCache, 0, 0, w, h);

  const dim = 0.55 + 0.45 * Math.sin(t * 0.12);
  for (const p of DUST) {
    const drift = (p.x * w - (t * 7 + p.depth * 90)) % w;
    const x = drift < 0 ? drift + w : drift;
    const y = p.y * h;
    const alpha = (0.02 + 0.05 * p.depth) * (0.55 + 0.45 * Math.sin(t * 0.5 + p.phase)) * dim;
    ctx.fillStyle = rgba(PALE, alpha);
    ctx.beginPath();
    ctx.arc(x, y, p.r * (0.7 + p.depth * 0.8), 0, Math.PI * 2);
    ctx.fill();
  }
}

let vignetteCache: HTMLCanvasElement | null = null;
let vignetteKey = '';

function drawVignette(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const key = `${w}x${h}`;
  if (!vignetteCache || vignetteKey !== key) {
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const g = canvas.getContext('2d');
    if (g) {
      const vignette = g.createRadialGradient(w / 2, h / 2, h * 0.3, w / 2, h / 2, h * 0.95);
      vignette.addColorStop(0, 'rgba(0,0,0,0)');
      vignette.addColorStop(0.62, 'rgba(0,0,0,0.16)');
      vignette.addColorStop(1, 'rgba(0,0,0,0.62)');
      g.fillStyle = vignette;
      g.fillRect(0, 0, w, h);
    }
    vignetteCache = canvas;
    vignetteKey = key;
  }
  ctx.drawImage(vignetteCache, 0, 0, w, h);
}

/** 极低透明度的地形等高线：给线稿一个空间参照，不抢主体。 */
function drawTerrainGrid(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number) {
  const alpha = 0.055 * actAlpha(t, 0, 60, 1.2);
  if (alpha <= 0.004) return;
  for (let z = -760; z <= 760; z += 152) {
    const points: Vec3[] = [];
    for (let age = 0; age <= 70.01; age += 2.5) {
      const anchor = mainPoint(age);
      points.push([anchor[0], anchor[1] - 150 + 18 * Math.sin(age / 7 + z / 260), z]);
    }
    strokeWorldBatch(ctx, frame, points, {color: RIDGE_EDGE, width: 0.55, alpha});
  }
  for (let age = 0; age <= 70.01; age += 5) {
    const anchor = mainPoint(age);
    const y = anchor[1] - 150;
    strokeWorld(ctx, frame, [
      [anchor[0], y, -760],
      [anchor[0], y, 760],
    ], {color: RIDGE_EDGE, width: 0.45, alpha: alpha * 0.8});
  }
}

// ------------------------------------------------------------------ 时间轴与年龄

function drawTimeline(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number, labels: Labels) {
  const chartDim = 1 - actAlpha(t, 35.2, 43.4, 0.7);
  strokeWorldBatch(ctx, frame, MAIN_BEFORE.points, {color: GRAY, width: 1.4, alpha: 0.24 * chartDim});
  strokeWorldBatch(ctx, frame, NEW_PATH.points, {color: GRAY, width: 1.4, alpha: 0.16 * chartDim});

  const traveled = REALIZED.cut(subjectDistance(t));
  strokeWorldBatch(ctx, frame, traveled, {color: PALE, width: 2.3, alpha: 0.82 * chartDim, glow: 0.18});
  fillRibbon(ctx, frame, traveled, 9, RIDGE, 0.1 * chartDim, 30);

  const age = ageAt(t);
  const marks = labels.ages.length ? labels.ages : [...AGE_MARKS];
  const fade = (1 - span(t, 49.5, 52.0)) * (1 - actAlpha(t, 35.0, 43.4, 0.6));
  if (fade <= 0.01) return;
  for (const mark of marks) {
    const point = lifeMarkPoint(mark);
    const p = projection(frame, point);
    if (!p.visible || p.x < 48 || p.x > frame.width - 48) continue;
    const passed = age >= mark || t >= 46.2;
    const wave = t >= 0.3 + (mark / 80) * 4.5;
    const alpha = (passed ? 0.58 : wave ? 0.34 : 0.12) * fade;
    if (alpha <= 0.01) continue;
    const r = clamp(p.rel, 0.5, 1.5);
    ctx.strokeStyle = rgba(BLUE, alpha * fogAlpha(p.z));
    ctx.lineWidth = clamp(1.2 * p.rel, 0.6, 2.2);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y - 7 * r);
    ctx.lineTo(p.x, p.y + 7 * r);
    ctx.stroke();
    const labelOffset: Vec3 = mark === 47 ? [-46, 22, 0] : [0, 28, 0];
    drawLabel(ctx, frame, add(point, labelOffset), String(mark), 26, alpha, GRAY, 'center', 0, 0.7);
  }
}

// ------------------------------------------------------------------ 开场小岔口

function drawYouth(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number) {
  const alpha = 1 - span(t, 5.2, 6.6);
  if (alpha <= 0.01) return;
  YOUTH_BRANCHES.forEach((branch) => {
    const reveal = span(t, 1.4, 3.4);
    if (reveal <= 0) return;
    strokeWorldBatch(ctx, frame, branch.path.cut(branch.path.length * reveal), {
      color: branch.bright ? PALE : GRAY,
      width: branch.bright ? 2.2 : 1.2,
      alpha: (branch.bright ? 0.7 : 0.3) * alpha * reveal,
      glow: branch.bright ? 0.14 : 0,
      dash: branch.bright ? undefined : [8, 12],
    });
  });
}

// ------------------------------------------------------------------ 城市

function drawCity(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number, labels: Labels) {
  const alpha = actAlpha(t, 6.3, 15.8, 0.65);
  if (alpha <= 0.005) return;
  const branchProgress = span(t, 6.8, 8.4);

  CITY_LANES.forEach((lane) => {
    const points = slice(lane.path.points, branchProgress);
    const ghost = lane.chosen ? 1 : 0.7 - 0.28 * span(t, 10.0, 12.0);
    strokeRidge(ctx, frame, points, {
      color: lane.chosen ? PALE : GRAY,
      width: lane.chosen ? 2.6 : 1.5,
      alpha: (lane.chosen ? 0.92 : 0.5) * ghost * alpha,
      glow: lane.chosen ? 0.2 : 0,
      ribbon: lane.chosen ? 8 : 0,
      ribbonAlpha: 0.14 * alpha,
    });
    if (branchProgress > 0.3) {
      const labelPoint = lane.chosen ? mainPoint(25) : lane.anchor;
      drawLabel(ctx, frame, add(labelPoint, [0, lane.chosen ? 92 : 58, lane.chosen ? -30 : 0]),
        labels.cities[lane.nameIndex] ?? '', lane.chosen ? 32 : 27,
        (lane.chosen ? 0.98 : 0.7) * ghost * alpha,
        lane.chosen ? CREAM : GRAY, 'center', 0, 0.78);
    }
    // 每座城市都有一扇门；只是主体走进了其中一扇，避免把其他城市画成没有机会。
    dot3(ctx, frame, lane.opening, 3.0, lane.chosen ? BLUE : GRAY,
      (lane.chosen ? 0.5 : 0.3) * alpha * branchProgress);
  });

  // 选中城市里新打开的门：环境真正改变了主体可走的路线。
  const chosen = CITY_LANES.find((lane) => lane.chosen);
  if (chosen) {
    const open = span(t, 9.4, 10.6);
    const ringPoints = [
      chosen.anchor,
      add(chosen.anchor, [50, 70, -110]),
      chosen.opening,
      add(chosen.opening, [70, 30, 130]),
      add(chosen.anchor, [120, 10, 60]),
    ];
    if (open > 0) {
      strokeRidge(ctx, frame, slice(ringPoints, open), {
        color: BLUE, width: 2.2, alpha: 0.82 * alpha, glow: 0.2,
      });
      // 一道可穿过的门：两根立柱与横梁，让“新入口”成为路径上的事件。
      const gateL = add(chosen.anchor, [0, -42, -74]);
      const gateR = add(chosen.anchor, [0, -42, 74]);
      const gateLT = add(gateL, [0, 154, 0]);
      const gateRT = add(gateR, [0, 154, 0]);
      strokeWorld(ctx, frame, [gateL, gateLT], {color: PALE, width: 3.4, alpha: 0.95 * open * alpha, glow: 0.18});
      strokeWorld(ctx, frame, [gateR, gateRT], {color: PALE, width: 3.4, alpha: 0.95 * open * alpha, glow: 0.18});
      strokeWorld(ctx, frame, [gateLT, gateRT], {color: PALE, width: 2.6, alpha: 0.8 * open * alpha});
      drawLabel(ctx, frame, add(chosen.anchor, [0, 178, 0]), '新入口', 27,
        0.9 * open * alpha, PALE, 'center', 0, 0.82);
      dot3(ctx, frame, chosen.anchor, 5.0, PALE, open * alpha);
      dot3(ctx, frame, chosen.opening, 3.8, BLUE, open * alpha * 0.9);
    }
  }

  const cityReveal = span(t, 7.6, 9.2) * alpha;
  if (cityReveal <= 0) return;

  for (const building of CITY_BUILDINGS) {
    const base = building.base;
    const top: Vec3 = [base[0], base[1] + building.height * span(t, 7.8, 9.6), base[2]];
    const left: Vec3 = [base[0], base[1], base[2] - building.width / 2];
    const right: Vec3 = [base[0], base[1], base[2] + building.width / 2];
    const topLeft: Vec3 = [top[0], top[1], left[2]];
    const topRight: Vec3 = [top[0], top[1], right[2]];
    const bl = projection(frame, left);
    const br = projection(frame, right);
    const tl = projection(frame, topLeft);
    const tr = projection(frame, topRight);
    if (!bl.visible || !br.visible || !tl.visible || !tr.visible) continue;
    if (bl.x < -300 || bl.x > 2220) continue;
    const a = cityReveal * (0.2 + 0.14 * ((building.phase + 1) / 2)) * fogAlpha(bl.z);
    ctx.beginPath();
    ctx.moveTo(bl.x, bl.y);
    ctx.lineTo(br.x, br.y);
    ctx.lineTo(tr.x, tr.y);
    ctx.lineTo(tl.x, tl.y);
    ctx.closePath();
    ctx.fillStyle = rgba('#111a26', 0.55 * a);
    ctx.fill();
    ctx.strokeStyle = rgba(GRAY, a);
    ctx.lineWidth = clamp(1.5 * bl.rel, 0.6, 2.2);
    ctx.stroke();
    const lit = 0.35 + 0.65 * Math.max(0, Math.sin(t * 0.7 + building.phase)) ** 2;
    if (bl.rel > 0.42) {
      ctx.fillStyle = rgba(BLUE, a * 0.85 * lit);
      const count = Math.min(5, Math.max(1, Math.floor(building.height / 78)));
      for (let i = 0; i < count; i += 1) {
        const yy = tl.y + (bl.y - tl.y) * ((i + 1) / (count + 1));
        ctx.fillRect(bl.x + 2, yy, Math.max(2, Math.abs(br.x - bl.x) * 0.3), 2);
      }
    }
  }

  const network = CITY_NETWORK;
  for (const edge of network.edges) {
    const reveal = span(t, edge.reveal, edge.reveal + 0.45) * alpha;
    if (reveal <= 0) continue;
    strokeWorldBatch(ctx, frame, [network.nodes[edge.a].at, network.nodes[edge.b].at], {
      color: BLUE, width: 1.1, alpha: 0.36 * reveal,
    });
  }
  network.nodes.forEach((node) => {
    const reveal = span(t, node.reveal, node.reveal + 0.4) * alpha;
    if (reveal <= 0) return;
    dot3(ctx, frame, node.at, 4.0, BLUE, 0.9 * reveal);
  });
}

// ------------------------------------------------------------------ 行业

function drawIndustry(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number, labels: Labels) {
  const alpha = actAlpha(t, 15.4, 27.3, 0.5);
  if (alpha <= 0.005) return;
  const distance = industryDistance(t);
  const sweep = span(t, 22.8, 24.4);

  INDUSTRY_LANES.forEach((lane) => {
    const reveal = span(t, 15.5, 17.2);
    const shown = distance + (lane.path.length - distance) * sweep;
    const points = lane.path.cut(shown);
    if (reveal <= 0) return;
    strokeRidge(ctx, frame, slice(points, reveal), {
      color: lane.chosen ? PALE : GRAY,
      width: lane.chosen ? 2.9 : 1.9,
      alpha: (lane.chosen ? 0.95 : 0.58) * alpha,
      glow: lane.chosen ? 0.22 : 0,
      ribbon: lane.chosen ? 11 : 7,
      ribbonAlpha: (lane.chosen ? 0.2 : 0.1) * alpha,
    });

    if (!lane.chosen) {
      const runner = lane.path.atDistance(distance);
      const tail = lane.path.atDistance(Math.max(0, distance - 90));
      strokeWorldBatch(ctx, frame, [tail, runner], {
        color: BLUE, width: 2.2, alpha: 0.4 * alpha, glow: 0,
      });
      dot3(ctx, frame, runner, 4.6, BLUE, 0.8 * alpha);
    }

    // 近景先不报行业名；拉远公开全貌时，名称才在最能看出差距的远端出现。
    const revealNames = span(t, 24.0, 25.2);
    if (revealNames > 0.2) {
      const labelAt = lane.path.atU(0.72 + lane.nameIndex * 0.04);
      drawLabel(ctx, frame, add(labelAt, [0, 26 + (2 - lane.nameIndex) * 20, 0]),
        labels.industries[lane.nameIndex] ?? '', lane.chosen ? 30 : 27,
        (lane.chosen ? 0.94 : 0.68) * alpha * revealNames,
        lane.chosen ? CREAM : GRAY, 'center', 0, 0.86);
    }
  });

  // 拉远后只在远端的落差处补一条极淡的量高参照，不加排名文字。
  if (t > 23.4) {
    const a = span(t, 23.4, 24.6) * alpha * 0.2;
    const high = INDUSTRY_LANES[4].path.points[INDUSTRY_LANES[4].path.points.length - 1];
    const low = INDUSTRY_LANES[0].path.points[INDUSTRY_LANES[0].path.points.length - 1];
    strokeWorld(ctx, frame, [high, low], {color: BLUE, width: 0.8, alpha: a});
  }
}

// ------------------------------------------------------------------ 伴侣

function drawPartner(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number, labels: Labels) {
  const alpha = actAlpha(t, 26.6, 35.8, 0.6);
  if (alpha <= 0.005) return;
  const progress = span(t, 27.2, 31.2);
  const partnerT = span(t, 28.0, 31.0);
  const carry = 1 - span(t, 35.0, 35.8) * 0.45;

  PARTNER_TRACKS.forEach((track) => {
    const selfPoints = track.self.cut(track.self.length * progress);
    const partnerPoints = track.partner.cut(track.partner.length * progress);
    const shaky = !track.support;
    const color = shaky ? '#7d8792' : PALE;
    strokeRidge(ctx, frame, selfPoints, {
      color, width: shaky ? 2.0 : 2.8,
      alpha: (shaky ? 0.55 : 0.94) * alpha,
      glow: shaky ? 0 : 0.22,
      ribbon: track.support ? 8 : 0,
      ribbonAlpha: 0.12 * alpha,
    });
    strokeRidge(ctx, frame, partnerPoints, {
      color: shaky ? '#5f6872' : BLUE,
      width: shaky ? 1.7 : 2.2,
      alpha: (shaky ? 0.44 : 0.8) * alpha,
      glow: shaky ? 0 : 0.16,
      dash: shaky ? [10, 14] : undefined,
    });

    // 两个主体的相互作用：支撑轨有规律地交换位置与交叉栓；牵制轨被拉长、错位。
    const selfRunner = track.self.atDistance(track.self.length * progress);
    const partnerDelay = shaky ? 0.12 : 0.035;
    const partnerRunner = track.partner.atDistance(track.partner.length * Math.max(0, partnerT - partnerDelay));
    dot3(ctx, frame, selfRunner, shaky ? 4.2 : 6.2, color, alpha * (shaky ? 0.7 : 1));
    dot3(ctx, frame, partnerRunner, shaky ? 3.6 : 5.4, shaky ? GRAY : BLUE, alpha * (shaky ? 0.6 : 0.92));

    if (track.support) {
      for (let i = 1; i <= 2; i += 1) {
        const u = progress * (0.4 + i * 0.18);
        if (u <= 0.05 || u >= 0.98) continue;
        const a = track.self.atU(u);
        const b = track.partner.atU(u - 0.02);
        strokeWorld(ctx, frame, [a, b], {
          color: PALE, width: 1.4, alpha: 0.36 * alpha,
        });
      }
    }

    const names = shaky ? labels.partnerLeft : labels.partnerRight;
    const ats = [0.38, 0.62, 0.84];
    names.slice(0, 3).forEach((name, index) => {
      const u = ats[index] ?? 0.9;
      const reveal = span(t, 28.5 + index * 0.8, 29.0 + index * 0.8);
      if (reveal <= 0) return;
      const anchor = track.partner.atU(u);
      drawLabel(ctx, frame, add(anchor, [0, shaky ? -30 : 34, 0]), name,
        24, 0.84 * reveal * alpha * carry, shaky ? '#b7c0c9' : CREAM, 'center', 0, 0.82);
    });
  });

  // 关系结束后，支撑轨的抬升仍留在主路旁；牵制轨淡出。
  const liftReveal = span(t, 33.4, 35.2) * alpha * carry;
  if (liftReveal > 0) {
    strokeRidge(ctx, frame, PARTNER_LIFT.points, {
      color: BLUE, width: 1.8, alpha: 0.55 * liftReveal, glow: 0.12, ribbon: 7, ribbonAlpha: 0.1 * liftReveal,
    });
  }
}

// ------------------------------------------------------------------ 投资

function drawInvestment(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number, labels: Labels) {
  const alpha = actAlpha(t, 35.4, 43.3, 0.6) * (1 - span(t, 42.4, 43.2));
  if (alpha <= 0.005) return;
  const age = chartAgeAt(t);

  const gridAlpha = alpha * 0.22;
  for (let a = 25; a <= 60; a += 5) {
    strokeWorld(ctx, frame, [[ageX(a), chartY(100), CHART_Z], [ageX(a), chartY(390), CHART_Z]], {
      color: GRAY, width: 0.7, alpha: gridAlpha,
    });
  }
  strokeWorld(ctx, frame, [[ageX(25), chartY(100), CHART_Z], [ageX(60), chartY(100), CHART_Z]], {
    color: GRAY, width: 1.3, alpha: alpha * 0.62,
  });
  [25, 30, 35, 40, 45, 47].forEach((value) => {
    drawLabel(ctx, frame, [ageX(value), chartY(100) - 34, CHART_Z], String(value), 28,
      alpha * 0.86, GRAY, 'center', 0, 0.86);
  });
  drawLabel(ctx, frame, [ageX(47) + 90, chartY(100) - 34, CHART_Z], '年龄', 24,
    alpha * 0.52, GRAY, 'left', 0, 0.82);

  // 持续小额投入的台阶：让“垒高”成为可见过程，而不是一条抽象曲线。
  const stepReveal = span(t, 36.0, 42.4);
  for (let a = 26; a <= Math.min(60, age); a += 4) {
    const point = curvePointAt(INVEST_STEADY, a);
    const next = curvePointAt(INVEST_STEADY, Math.min(60, a + 4));
    const p0: Vec3 = [ageX(a), chartY(100), CHART_Z];
    const p1: Vec3 = [ageX(Math.min(60, a + 4)), chartY(100), CHART_Z];
    const p2: Vec3 = [ageX(Math.min(60, a + 4)), next.at[1], CHART_Z];
    const p3: Vec3 = [ageX(a), point.at[1], CHART_Z];
    fillQuad(ctx, frame, p0, p1, p2, p3, RIDGE, 0.3 * stepReveal * alpha);
  }

  const flat = slice(INVEST_FLAT.map((item) => item.at), span(t, 36.0, 42.6));
  const steady = slice(INVEST_STEADY.map((item) => item.at), span(t, 36.0, 42.6));
  strokeWorldBatch(ctx, frame, flat, {color: GRAY, width: 2.4, alpha: alpha * 0.9});
  strokeRidge(ctx, frame, steady, {
    color: PALE, width: 3.0, alpha, glow: 0.24, ribbon: 8, ribbonAlpha: 0.18 * alpha,
  });

  const walker = chartSubjectAt(t);
  subjectGlow(ctx, frame, walker, 4.6, alpha * 0.9);
  drawLabel(ctx, frame, add(walker, [0, 26, 0]), `${Math.round(age)} 岁`, 24,
    alpha * 0.58, GRAY, 'center', 0, 0.84);
  drawLabel(ctx, frame, [ageX(41.5), chartY(196), CHART_Z], '持续投入', 30,
    alpha * 0.92, PALE, 'right', 0, 0.86);
  drawLabel(ctx, frame, [ageX(41.5), chartY(108), CHART_Z], '只存下', 28,
    alpha * 0.76, GRAY, 'right', 0, 0.86);
}

// ------------------------------------------------------------------ 学习

function drawLearning(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number, labels: Labels) {
  const planted = 0.06 + 0.12 * span(t, 8.0, 15.0);
  strokeWorldBatch(ctx, frame, LEARNING_THREAD.points, {
    color: BLUE, width: 1.2, alpha: planted, dash: [8, 12],
  });

  const alpha = actAlpha(t, 42.8, 52.3, 0.9);
  if (alpha <= 0.005) return;

  // 原路走到尽头：端头用短横帽标出，不让它自然消失在雾里。
  const dead = mainPoint(47);
  strokeRidge(ctx, frame, MAIN_BEFORE.cut(MAIN_BEFORE.length), {
    color: GRAY, width: 2.0, alpha: 0.48 * alpha,
  });
  const deadP = projection(frame, dead);
  if (deadP.visible) {
    const r = clamp(deadP.rel, 0.6, 1.6);
    ctx.strokeStyle = rgba(BLUE, 0.7 * alpha);
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.moveTo(deadP.x - 13 * r, deadP.y - 13 * r);
    ctx.lineTo(deadP.x + 13 * r, deadP.y + 13 * r);
    ctx.stroke();
    strokeWorld(ctx, frame, [dead, add(dead, [55, 0, 0])], {
      color: GRAY, width: 1.2, alpha: 0.24 * alpha, dash: [7, 10],
    });
  }

  const threadReveal = span(t, 43.4, 45.2) * alpha;
  strokeWorldBatch(ctx, frame, LEARNING_THREAD.points, {
    color: BLUE, width: 2.0, alpha: 0.62 * (0.25 + threadReveal), glow: 0.16,
  });
  LEARNING_NODES.forEach((node, index) => {
    const reveal = span(t, node.reveal, node.reveal + 0.45) * alpha;
    if (index >= 3) dot3(ctx, frame, node.at, 4.2, BLUE, reveal);
    if (index === 6) {
      drawLabel(ctx, frame, add(node.at, [0, 30, 0]),
        labels.learningNodes[index] ?? '', 26, 0.92 * reveal, CREAM, 'center', 0, 0.84);
    }
  });

  // 连接：先虚后实；主体沿它真正走过去。
  const bridgeReveal = span(t, 45.8, 46.5);
  const bridgeCut = LEARNING_BRIDGE.cut(LEARNING_BRIDGE.length * bridgeReveal);
  strokeRidge(ctx, frame, bridgeCut, {
    color: PALE, width: 2.4, alpha: (0.24 + 0.7 * bridgeReveal) * alpha,
    glow: 0.2, ribbon: 6, ribbonAlpha: 0.12 * alpha,
  });

  const newReveal = span(t, 47.8, 49.4) * alpha;
  strokeRidge(ctx, frame, NEW_PATH.cut(NEW_PATH.length * span(t, 47.8, 50.2)), {
    color: PALE, width: 2.6, alpha: 0.9 * newReveal, glow: 0.18, ribbon: 8, ribbonAlpha: 0.12 * newReveal,
  });

}

// ------------------------------------------------------------------ 结尾树

function drawTree(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number, labels: Labels) {
  const base = span(t, 51.6, 52.25);
  if (base <= 0.005) return;
  const dim = 1 - span(t, 58.2, 59.1) * 0.2;
  const alpha = base * dim;

  TREE_PATHS.forEach((path, index) => {
    if (path.level === 0) return;
    const levelStart = path.level === 1 ? 52.2 : 54.1;
    const stagger = (index % 9) * 0.055;
    const reveal = span(t, levelStart + stagger, levelStart + 0.8 + stagger);
    if (reveal <= 0) return;
    const color = path.level === 1 ? PALE : '#8fb6d9';
    if (path.level === 1) {
      fillRibbon(ctx, frame, path.points, 7, RIDGE, path.alpha * alpha * reveal * 0.55, 32);
    }
    if (path.level === 2 && reveal > 0.45) {
      dot3(ctx, frame, path.origin, 2.0, BLUE, 0.45 * alpha * reveal);
    }
    strokeWorldBatch(ctx, frame, path.points, {
      color,
      width: path.level === 1 ? 3.2 : 1.2,
      alpha: path.alpha * 1.7 * alpha * reveal,
    });
    if (reveal > 0.7) {
      const end = path.points[path.points.length - 1];
      dot3(ctx, frame, end, path.level === 1 ? 3.6 : 2.4, color,
        0.75 * path.alpha * alpha * reveal);
    }
  });

  // 后拉时让光沿已走路段回扫一次：结尾是“重看一遍这条路”，不是单纯缩放。
  const retrace = span(t, 52.5, 54.7);
  if (retrace > 0 && retrace < 1) {
    const distance = REALIZED.length * retrace;
    const head = REALIZED.atDistance(distance);
    const tail = REALIZED.atDistance(Math.max(0, distance - 130));
    strokeWorldBatch(ctx, frame, [tail, head], {
      color: BLUE, width: 2.2, alpha: 0.5 * alpha * (1 - retrace), glow: 0.2,
    });
    dot3(ctx, frame, head, 3.4, BLUE, 0.7 * alpha * (1 - retrace));
  }

  // 已走主路：全段保持可认回，已走部分更亮。
  const realizedReveal = span(t, 51.8, 53.2);
  strokeRidge(ctx, frame, REALIZED.points, {
    color: PALE, width: 5.2, alpha: 0.86 * alpha * realizedReveal,
    glow: 0.3, ribbon: 14, ribbonAlpha: 0.16 * alpha * realizedReveal,
  });
  const traveled = REALIZED.cut(subjectDistance(t));
  strokeRidge(ctx, frame, traveled, {
    color: PALE, width: 3.0, alpha: 0.95 * alpha, glow: 0.2,
  });

  DECISION_AGES.forEach((age, index) => {
    const reveal = span(t, 53.4 + index * 0.32, 54.0 + index * 0.32) * alpha;
    if (reveal <= 0) return;
    const point = mainPoint(age);
    const p = projection(frame, point);
    if (!p.visible) return;
    const r = clamp(p.rel, 0.6, 1.6);
    ctx.strokeStyle = rgba(PALE, reveal * 0.9);
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 11 * r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = rgba(BLUE, reveal * 0.75);
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3.2 * r, 0, Math.PI * 2);
    ctx.fill();
  });

  // 选择名称：在决策点旁边出现，避免排在画面底部变成另一张标签条。
  const labelAlpha = span(t, 55.6, 56.4) * (1 - span(t, 57.9, 58.5)) * alpha;
  const labelOffsets: [number, number][] = [[0, 110], [0, -100], [80, 70], [80, -70], [100, -90]];
  labels.choices.forEach((text, index) => {
    const point = TREE_NODES[index] ?? mainPoint(DECISION_AGES[index] ?? 47);
    const p = projection(frame, point);
    if (!p.visible) return;
    const [dx, dy] = labelOffsets[index] ?? [80, 60];
    const x = clamp(p.x + dx, 70, frame.width - 70);
    const y = clamp(p.y + dy, 74, 850);
    drawScreenText(ctx, text, x, y, 36, labelAlpha, index === 4 ? PALE : CREAM);
  });
}

// ------------------------------------------------------------------ 主体与文字压暗

function drawSubject(ctx: CanvasRenderingContext2D, frame: CameraFrame, t: number) {
  if (t >= 35.4 && t < 43.3) return;
  const state = subjectAt(t);
  const fade = 1 - span(t, 58.8, 59.8);
  const trail: Vec3[] = [];
  for (let s = Math.max(0, t - 1.3); s <= t + 0.001; s += 0.1) {
    trail.push(subjectAt(s).point);
  }
  strokeWorldBatch(ctx, frame, trail, {
    color: PALE, width: 2.0, alpha: 0.3 * fade, glow: 0.14,
  });
  subjectGlow(ctx, frame, state.point, 6.4, 0.98 * fade);
}

function drawCopyScrims(
  ctx: CanvasRenderingContext2D,
  copy: CopyItem[],
  t: number,
  _w: number,
  _h: number,
) {
  if (t >= 52.0) return;
  for (const item of copy) {
    const inP = span(t, item.from, item.from + 0.55);
    const outP = span(t, item.to - 0.55, item.to);
    const opacity = inP * (1 - outP);
    if (opacity <= 0.02) continue;
    const cx = item.x + item.width / 2;
    const cy = item.y + item.size * 0.72;
    const radius = Math.max(item.width * 0.42, item.size * 2.4);
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    gradient.addColorStop(0, `rgba(3, 5, 8, ${(item.size > 120 ? 0.4 : 0.36) * opacity})`);
    gradient.addColorStop(0.55, `rgba(3, 5, 8, ${0.18 * opacity})`);
    gradient.addColorStop(1, 'rgba(3, 5, 8, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2);
  }
}

// ------------------------------------------------------------------ 主入口

export function drawFrame(
  ctx: CanvasRenderingContext2D,
  t: number,
  width: number,
  height: number,
  props: LifeProps,
) {
  const cam = cameraAt(t);
  const frame = cameraFrame(cam, {x: 0, y: 0, width, height});

  ctx.clearRect(0, 0, width, height);
  drawBackground(ctx, t, width, height);
  drawTerrainGrid(ctx, frame, t);
  drawTimeline(ctx, frame, t, props.labels);
  drawYouth(ctx, frame, t);
  drawCity(ctx, frame, t, props.labels);
  drawIndustry(ctx, frame, t, props.labels);
  drawPartner(ctx, frame, t, props.labels);
  drawInvestment(ctx, frame, t, props.labels);
  drawLearning(ctx, frame, t, props.labels);
  drawTree(ctx, frame, t, props.labels);
  drawSubject(ctx, frame, t);
  drawVignette(ctx, width, height);
  drawCopyScrims(ctx, props.copy, t, width, height);
}
