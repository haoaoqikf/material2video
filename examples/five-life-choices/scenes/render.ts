/**
 * 人生五选择的 Canvas 绘制层。
 *
 * 只做一件事：给定 elapsedSeconds，把 geometry.ts 的世界画成一帧。
 * 不读挂钟、不累积状态、不用 CSS 动画；同一帧重复绘制结果一致。
 */
import {
  AGE_MARKS,
  CHART_Y0,
  CHART_Z,
  CITY_BRANCHES,
  CITY_BUILDINGS,
  CITY_NETWORK,
  DECISION_AGES,
  INDUSTRY_PATHS,
  INVEST_FLAT,
  INVEST_GROW,
  LEARNING_NODES,
  LEARNING_PATH,
  NEAR,
  PARTNER_TRACKS,
  TREE_PATHS,
  UPPER_BAND,
  actAlpha,
  add,
  ageAt,
  ageX,
  basePoint,
  bezierPoints,
  cameraAt,
  cameraFrame,
  chartY,
  clamp,
  curvePointAt,
  fogAlpha,
  lanePoint,
  learningPoint,
  lerp3,
  lifePoint,
  projectPoint,
  projectView,
  seeded,
  span,
  viewOf,
  type CameraFrame,
  type CameraState,
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

export type LifeProps = {copy: CopyItem[]; labels: Labels; shots?: unknown};

const BG_TOP = '#05070a';
const BG_BOTTOM = '#020304';
const CREAM = '#f2f6fb';
const GRAY = '#9aa7b4';
const BLUE = '#9cc8ff';
const PALE = '#dbe9ff';
const INK = '#020407';

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
};

/** 逐段投影描边：每段按深度调整透明度与线宽，近平面处插值裁剪。 */
function strokeWorld(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  points: Vec3[],
  style: StrokeStyle,
) {
  const base = style.alpha ?? 1;
  ctx.lineCap = 'butt';
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
    const width = Math.max(0.45, Math.min(6, style.width * rel));
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

/** 整条路径一次描边（决策树与远景用，避免几百次状态切换）。 */
function strokeWorldBatch(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  points: Vec3[],
  style: StrokeStyle,
) {
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
  const width = Math.max(0.4, Math.min(5, style.width * lastRel));
  ctx.lineCap = 'round';
  if (style.glow) {
    ctx.strokeStyle = rgba(style.color, alpha * style.glow);
    ctx.lineWidth = width * 2.8;
    ctx.stroke();
  }
  ctx.strokeStyle = rgba(style.color, alpha);
  ctx.lineWidth = width;
  ctx.stroke();
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
  const r = clamp(radius * Math.max(0.5, p.rel), 1.2, radius * 2.6);
  const a = alpha * fogAlpha(p.z);
  if (a <= 0.01) return;
  ctx.fillStyle = rgba(color, a * 0.1);
  ctx.beginPath();
  ctx.arc(p.x, p.y, r * 3.1, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = rgba(color, a * 0.24);
  ctx.beginPath();
  ctx.arc(p.x, p.y, r * 1.8, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = rgba(color, a);
  ctx.beginPath();
  ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
  ctx.fill();
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
  if (a <= 0.02 || s < 9) return;
  ctx.font = `400 ${s.toFixed(1)}px "M2V Sans", sans-serif`;
  ctx.textAlign = align;
  ctx.textBaseline = 'middle';
  const textWidth = ctx.measureText(text).width;
  const leftMargin = align === 'right' ? textWidth + 12 : align === 'center' ? textWidth / 2 + 12 : 12;
  const rightMargin = align === 'left' ? textWidth + 12 : align === 'center' ? textWidth / 2 + 12 : 12;
  const x = clamp(p.x, frame.x0 + leftMargin, frame.x0 + frame.width - rightMargin);
  const y = p.y - lift * clamp(p.rel, 0.5, 1.7);
  if (y < 18 || y > frame.height - 18) return;
  ctx.lineJoin = 'round';
  ctx.strokeStyle = rgba(INK, 0.88 * a);
  ctx.lineWidth = Math.max(3, s * 0.2);
  ctx.strokeText(text, x, y);
  ctx.fillStyle = rgba(color, a);
  ctx.fillText(text, x, y);
}

// ------------------------------------------------------------------ 背景

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

// ------------------------------------------------------------------ 时间轴与年龄

function drawTimeline(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
  labels: Labels,
) {
  const age = ageAt(t);
  const full: Vec3[] = [];
  for (let a = 0; a <= 80.001; a += 0.5) full.push(lifePoint(a));
  const traveled: Vec3[] = [];
  for (let a = 0; a <= age + 0.001; a += 0.25) traveled.push(lifePoint(a));

  strokeWorldBatch(ctx, frame, full, {color: GRAY, width: 1.5, alpha: 0.26});
  strokeWorldBatch(ctx, frame, traveled, {color: PALE, width: 2.2, alpha: 0.8, glow: 0.22});

  const marks = labels.ages.length ? labels.ages : [...AGE_MARKS];
  const tickFade = 1 - span(t, 43.5, 45.6);
  for (const mark of marks) {
    const point = lifePoint(mark);
    const p = projection(frame, point);
    if (!p.visible) continue;
    const passed = age >= mark;
    const wave = t >= 0.35 + (mark / 80) * 4.3;
    const focus = mark === 22;
    const alpha = (passed ? (focus ? 0.95 : 0.62) : wave ? 0.46 : 0.16) * tickFade;
    if (alpha <= 0.01) continue;
    const r = clamp(p.rel, 0.5, 1.5);
    ctx.strokeStyle = rgba(BLUE, alpha * fogAlpha(p.z));
    ctx.lineWidth = clamp((focus ? 1.8 : 1.1) * p.rel, 0.6, 2.4);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y - 7 * r);
    ctx.lineTo(p.x, p.y + 7 * r);
    ctx.stroke();
    drawLabel(ctx, frame, add(point, [0, 30, 0]), String(mark), mark === 22 ? 30 : 24,
      alpha, focus ? PALE : GRAY, 'center', 0, 0.7);
    if (mark === 22) {
      drawLabel(ctx, frame, add(point, [0, 54, 0]), '岁', 15, alpha * 0.8, GRAY, 'center', 0, 0.7);
    }
  }
}

// ------------------------------------------------------------------ 城市

function drawCity(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
  labels: Labels,
) {
  const alpha = actAlpha(t, 6.9, 16.4, 0.7);
  if (alpha <= 0.005) return;
  const branchProgress = span(t, 6.9, 8.0);

  for (const branch of CITY_BRANCHES) {
    const points = slice(branch.points, branchProgress);
    const name = labels.cities[branch.nameIndex] ?? '';
    const ghost = branch.chosen ? 1 : 1 - 0.55 * span(t, 10.2, 11.8);
    strokeWorldBatch(ctx, frame, points, {
      color: branch.chosen ? PALE : GRAY,
      width: branch.chosen ? 2.8 : 1.6,
      alpha: (branch.chosen ? 0.92 : 0.32) * ghost * alpha,
      glow: branch.chosen ? 0.2 : 0,
    });
    if (branchProgress > 0.36) {
      const lifts = [90, 30, 10, -70, -150];
      const lift = lifts[branch.nameIndex] ?? 0;
      drawLabel(ctx, frame, add(branch.anchor, [0, lift, 0]), name, branch.chosen ? 38 : 32,
        (branch.chosen ? 0.98 : 0.68) * ghost * alpha, branch.chosen ? CREAM : GRAY,
        'center', 0, 0.76);
    }
  }

  const cityReveal = span(t, 7.8, 9.4) * alpha;
  if (cityReveal <= 0) return;

  // 抽象城市：只画轮廓、顶线与稀疏窗光，不画真实照片。
  for (const building of CITY_BUILDINGS) {
    const base = building.base;
    const top: Vec3 = [base[0], base[1] + building.height * span(t, 7.9, 9.6), base[2]];
    const left: Vec3 = [base[0], base[1], base[2] - building.width / 2];
    const right: Vec3 = [base[0], base[1], base[2] + building.width / 2];
    const topLeft: Vec3 = [top[0], top[1], left[2]];
    const topRight: Vec3 = [top[0], top[1], right[2]];
    const bl = projection(frame, left);
    const br = projection(frame, right);
    const tl = projection(frame, topLeft);
    const tr = projection(frame, topRight);
    if (!bl.visible || !br.visible || !tl.visible || !tr.visible) continue;
    if (bl.x < -240 || bl.x > 2160) continue;
    const a = cityReveal * (0.26 + 0.18 * ((building.phase + 1) / 2)) * fogAlpha(bl.z);
    ctx.beginPath();
    ctx.moveTo(bl.x, bl.y);
    ctx.lineTo(br.x, br.y);
    ctx.lineTo(tr.x, tr.y);
    ctx.lineTo(tl.x, tl.y);
    ctx.closePath();
    ctx.fillStyle = rgba('#131a24', 0.5 * a);
    ctx.fill();
    ctx.strokeStyle = rgba(GRAY, a);
    ctx.lineWidth = clamp(1.4 * bl.rel, 0.5, 2.0);
    ctx.stroke();
    const lit = 0.35 + 0.65 * Math.max(0, Math.sin(t * 0.7 + building.phase)) ** 2;
    if (bl.rel > 0.45) {
      ctx.fillStyle = rgba(BLUE, a * 0.9 * lit);
      const count = Math.min(5, Math.max(1, Math.floor(building.height / 80)));
      for (let i = 0; i < count; i += 1) {
        const yy = tl.y + (bl.y - tl.y) * ((i + 1) / (count + 1));
        ctx.fillRect(bl.x + 2, yy, Math.max(2, Math.abs(br.x - bl.x) * 0.3), 2);
      }
    }
  }

  const network = CITY_NETWORK;
  const networkReveal = span(t, 10.0, 10.7);
  for (const edge of network.edges) {
    const reveal = span(t, edge.reveal, edge.reveal + 0.55) * networkReveal;
    if (reveal <= 0) continue;
    const points = [
      network.nodes[edge.a].at,
      network.nodes[edge.b].at,
    ];
    strokeWorldBatch(ctx, frame, points, {
      color: BLUE,
      width: 1.2,
      alpha: 0.4 * reveal * alpha,
    });
  }
  network.nodes.forEach((node, index) => {
    const reveal = span(t, 10.2 + index * 0.62, 10.65 + index * 0.62) * alpha;
    if (reveal <= 0) return;
    dot3(ctx, frame, node.at, 4.0, BLUE, 0.92 * reveal);
    const text = labels.cityNodes[index] ?? '';
    const dxs = [-120, 110, -150, 120, -100, 140, 0];
    const lifts = [-90, -40, 20, -40, 150, 170, -190];
    const labelAt = add(node.at, [dxs[index] ?? 0, lifts[index] ?? 0, 0]);
    strokeWorldBatch(ctx, frame, [node.at, labelAt], {
      color: BLUE, width: 0.7, alpha: 0.32 * reveal,
    });
    drawLabel(ctx, frame, labelAt, text, 30,
      0.94 * reveal, CREAM, 'center', 0, 0.8);
  });
}

// ------------------------------------------------------------------ 行业

function drawIndustry(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
  labels: Labels,
) {
  const alpha = actAlpha(t, 16.0, 27.35, 0.6);
  if (alpha <= 0.005) return;
  const u = 0.08 + 0.52 * span(t, 16.4, 26.6);

  INDUSTRY_PATHS.forEach((lane, index) => {
    const progress = span(t, 16.1 + index * 0.07, 17.9);
    const points = slice(lane.points, progress);
    const rail = points.map((point) => [point[0], point[1] + 9, point[2]] as Vec3);
    strokeWorldBatch(ctx, frame, points, {
      color: lane.chosen ? PALE : GRAY,
      width: lane.chosen ? 2.8 : 1.8,
      alpha: (lane.chosen ? 0.92 : 0.34) * alpha,
      glow: lane.chosen ? 0.22 : 0,
    });
    strokeWorldBatch(ctx, frame, rail, {
      color: lane.chosen ? BLUE : GRAY,
      width: lane.chosen ? 1.2 : 0.8,
      alpha: (lane.chosen ? 0.4 : 0.16) * alpha,
    });
    const runner = lanePoint(lane.points, u);
    const tail = lanePoint(lane.points, Math.max(0, u - 0.075));
    strokeWorldBatch(ctx, frame, [tail, runner], {
      color: lane.chosen ? PALE : BLUE,
      width: lane.chosen ? 3.2 : 2.2,
      alpha: (lane.chosen ? 0.55 : 0.3) * alpha,
      glow: lane.chosen ? 0.25 : 0,
    });
    dot3(ctx, frame, runner, lane.chosen ? 6.2 : 4.6,
      lane.chosen ? PALE : BLUE, (lane.chosen ? 1 : 0.75) * alpha);
    const labelAt = lane.points[Math.floor(lane.points.length * 0.26)];
    drawLabel(ctx, frame, add(labelAt, [0, 34, 0]),
      labels.industries[lane.nameIndex] ?? '', lane.chosen ? 36 : 32,
      (lane.chosen ? 0.98 : 0.68) * alpha, lane.chosen ? CREAM : GRAY,
      'center', 0, 0.88);
  });

  // 被选中跑道上的短刻线：让“跑道”而不只是“一条线”可辨。
  const chosen = INDUSTRY_PATHS[2];
  for (let i = 0; i < 12; i += 1) {
    const tickU = 0.2 + i * 0.058;
    if (tickU > u) continue;
    const point = lanePoint(chosen.points, tickU);
    const tick: Vec3[] = [point, [point[0], point[1] + 17, point[2]]];
    strokeWorldBatch(ctx, frame, tick, {
      color: BLUE, width: 1.1, alpha: alpha * 0.28,
    });
  }

  // 拉远后补一条极淡的竖向参照，让高度差自己说话，不加文字。
  if (t > 23.2) {
    const a = span(t, 23.2, 24.4) * alpha * 0.16;
    const high = INDUSTRY_PATHS[4].points[INDUSTRY_PATHS[4].points.length - 1];
    const low = INDUSTRY_PATHS[0].points[INDUSTRY_PATHS[0].points.length - 1];
    const line = [high, low];
    strokeWorld(ctx, frame, line, {color: BLUE, width: 0.8, alpha: a});
  }
}

// ------------------------------------------------------------------ 伴侣

function partnerEntry(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
  labels: Labels,
) {
  const reveal = span(t, 27.0, 28.2);
  if (reveal <= 0) return;
  const start = lifePoint(29.2);
  const end = add(lifePoint(30.2), [0, -62, 64]);
  const points = bezierPoints(start, add(start, [180, -90, 60]), lerp3(start, end, 0.72), end, 40);
  strokeWorld(ctx, frame, points, {color: PALE, width: 2.2, alpha: 0.8 * reveal, glow: 0.22});
  const partner = points[Math.min(points.length - 1, Math.floor(points.length * reveal))];
  dot3(ctx, frame, partner, 5.2, PALE, reveal);
}

function drawPartnerSplit(
  ctx: CanvasRenderingContext2D,
  cam: CameraState,
  t: number,
  labels: Labels,
  w: number,
  h: number,
) {
  const split = span(t, 28.15, 29.1) * (1 - span(t, 35.4, 36.2));
  if (split <= 0.005) {
    if (t >= 27.0 && t < 28.3) {
      partnerEntry(ctx, cameraFrame(cam, {x: 0, y: 0, width: w, height: h}), t, labels);
    }
    return;
  }

  const viewports: {viewport: Viewport; side: 'left' | 'right'}[] = [
    {viewport: {x: 8, y: 0, width: w / 2 - 16, height: h}, side: 'left'},
    {viewport: {x: w / 2 + 8, y: 0, width: w / 2 - 16, height: h}, side: 'right'},
  ];

  viewports.forEach(({viewport, side}) => {
    const index = side === 'left' ? 0 : 1;
    const track = PARTNER_TRACKS[index];
    const targetZ = side === 'left' ? 300 : -300;
    const sideCam: CameraState = {
      pos: add(cam.pos, [0, 0, targetZ * 0.22]),
      target: [cam.target[0], cam.target[1], targetZ],
      fov: cam.fov,
      roll: cam.roll,
    };
    const frame = cameraFrame(sideCam, viewport);
    ctx.save();
    ctx.beginPath();
    ctx.rect(viewport.x, viewport.y, viewport.width, viewport.height);
    ctx.clip();

    const progress = span(t, 28.35, 30.1) * split;
    const selfPoints = slice(track.self, progress);
    const partnerPoints = slice(track.partner, progress);
    const shaky = side === 'left';
    const color = shaky ? '#7d8792' : PALE;
    const lineWidth = shaky ? 2.0 : 2.6;
    const lineAlpha = shaky ? 0.55 : 0.92;

    // 左轨的断裂与抖动只由时间推导，不用随机。
    const selfJitter = selfPoints.map((point, i) =>
      [point[0], point[1] + (shaky ? Math.sin(i * 0.72 + t * 2.6) * 4 : 0), point[2]] as Vec3);
    const partnerJitter = partnerPoints.map((point, i) =>
      [point[0], point[1] + (shaky ? Math.sin(i * 0.61 + t * 2.1 + 1.6) * 5 : 0), point[2]] as Vec3);
    const drawBroken = (points: Vec3[], style: StrokeStyle) => {
      if (!shaky) {
        strokeWorldBatch(ctx, frame, points, style);
        return;
      }
      const stride = 8;
      for (let start = 0; start < points.length - 1; start += stride) {
        const part = points.slice(start, start + 5);
        if (part.length > 1) strokeWorldBatch(ctx, frame, part, style);
      }
    };
    drawBroken(selfJitter, {
      color, width: lineWidth, alpha: lineAlpha * split, glow: shaky ? 0 : 0.2,
    });
    drawBroken(partnerJitter, {
      color: shaky ? '#5f6872' : BLUE, width: shaky ? 1.6 : 2.0,
      alpha: (shaky ? 0.45 : 0.78) * split, glow: shaky ? 0 : 0.16,
    });

    const selfDot = selfPoints[selfPoints.length - 1];
    const partnerDot = partnerPoints[partnerPoints.length - 1];
    if (selfDot) dot3(ctx, frame, selfDot, shaky ? 4.4 : 6, color, split);
    if (partnerDot) dot3(ctx, frame, partnerDot, shaky ? 3.8 : 5.2, shaky ? GRAY : BLUE, split);

    const names = shaky ? labels.partnerLeft : labels.partnerRight;
    const times = shaky ? [31.0, 31.9, 32.8, 33.7] : [30.8, 31.6, 32.4, 33.2, 34.0];
    const lifts = shaky ? [34, 78, 42, 88] : [34, 84, 40, 88, 122];
    names.forEach((name, i) => {
      const at = times[i] ?? 34.8;
      const anchor = lifePoint(Math.min(37.4, at));
      const p = projection(frame, add(anchor, [0, lifts[i] ?? 40, targetZ * 0.72]));
      if (!p.visible) return;
      const alpha = 0.84 * split * span(t, at - 0.4, at + 0.2);
      if (alpha <= 0.02) return;
      const x = clamp(p.x, viewport.x + 62, viewport.x + viewport.width - 62);
      const s = 28 * clamp(p.rel, 0.84, 1.6);
      drawScreenText(ctx, name, x, p.y, s, alpha, shaky ? '#b7c0c9' : CREAM);
    });

    ctx.restore();
  });

  // 中间一条极细分隔光，不画底板。
  const divider = ctx.createLinearGradient(0, h * 0.12, 0, h * 0.88);
  divider.addColorStop(0, 'rgba(156,200,255,0)');
  divider.addColorStop(0.5, rgba(BLUE, 0.32 * split));
  divider.addColorStop(1, 'rgba(156,200,255,0)');
  ctx.fillStyle = divider;
  ctx.fillRect(w / 2 - 0.75, h * 0.12, 1.5, h * 0.76);
}

// ------------------------------------------------------------------ 投资

/** 资产曲线是示意，不承诺收益；只表达时间放大的方向性差异。 */
function drawInvestment(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
  labels: Labels,
) {
  const alpha = actAlpha(t, 35.55, 40.9, 0.7) * (1 - span(t, 39.9, 40.6));
  if (alpha <= 0.005) return;
  const age = clamp(ageAt(t), 26, 60);

  // 网格与坐标轴：只保留年龄，不标资产数字。
  const gridAlpha = alpha * 0.1;
  for (let a = 25; a <= 60; a += 5) {
    strokeWorld(ctx, frame, [[ageX(a), CHART_Y0, CHART_Z], [ageX(a), chartY(560), CHART_Z]], {
      color: GRAY, width: 0.7, alpha: gridAlpha,
    });
  }
  for (let v = 100; v <= 550; v += 100) {
    strokeWorld(ctx, frame, [[ageX(25), chartY(v), CHART_Z], [ageX(60), chartY(v), CHART_Z]], {
      color: GRAY, width: 0.6, alpha: gridAlpha * 0.8,
    });
  }
  strokeWorld(ctx, frame, [[ageX(25), CHART_Y0, CHART_Z], [ageX(60), CHART_Y0, CHART_Z]], {
    color: GRAY, width: 1.2, alpha: alpha * 0.45,
  });
  strokeWorld(ctx, frame, [[ageX(25), CHART_Y0, CHART_Z], [ageX(25), chartY(560), CHART_Z]], {
    color: GRAY, width: 1.1, alpha: alpha * 0.38,
  });

  [25, 30, 35, 40, 45, 50, 60].forEach((value) => {
    drawLabel(ctx, frame, [ageX(value), CHART_Y0 - 44, CHART_Z], String(value), 34,
      alpha * 0.74, GRAY, 'center', 0, 0.82);
  });
  drawLabel(ctx, frame, [ageX(60) + 100, CHART_Y0 - 44, CHART_Z], '年龄', 26,
    alpha * 0.58, GRAY, 'left', 0, 0.82);
  drawLabel(ctx, frame, [ageX(25) - 50, chartY(560), CHART_Z], '资产', 26,
    alpha * 0.54, GRAY, 'right', 0, 0.82);

  strokeWorldBatch(ctx, frame, INVEST_FLAT.map((point) => point.at), {
    color: GRAY, width: 2.4, alpha: alpha * 0.72,
  });
  strokeWorldBatch(ctx, frame, INVEST_GROW.map((point) => point.at), {
    color: PALE, width: 2.8, alpha: alpha * 0.9, glow: 0.22,
  });

  // 当前年龄的亮点：前半段两线几乎重合，越往后差距越明显。
  const marker = curvePointAt(INVEST_GROW, age);
  dot3(ctx, frame, marker.at, 5.4, PALE, alpha);
  const flat = curvePointAt(INVEST_FLAT, age);
  dot3(ctx, frame, flat.at, 3.6, GRAY, alpha * 0.65);
}

// ------------------------------------------------------------------ 学习

function drawLearning(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
  labels: Labels,
) {
  const dim = 0.05 + 0.55 * span(t, 44.1, 45.4);
  strokeWorldBatch(ctx, frame, LEARNING_PATH, {
    color: BLUE, width: 1.6 + 0.8 * span(t, 44.1, 45.4), alpha: dim,
    glow: t > 44 ? 0.18 : 0,
  });

  const alpha = actAlpha(t, 45.0, 52.55, 0.7);
  if (alpha <= 0.005) return;

  // 上方：25 岁以后停止学习，轨道越来越窄、节点越来越少。
  for (let i = 0; i < UPPER_BAND.length - 1; i += 1) {
    const age = 25 + (i / (UPPER_BAND.length - 1)) * 45;
    if (age > 31 && i % 7 >= 5) continue;
    const shrink = 1 - 0.55 * span(age, 30, 62);
    strokeWorld(ctx, frame, [UPPER_BAND[i], UPPER_BAND[i + 1]], {
      color: GRAY, width: Math.max(1.0, 2.6 * shrink), alpha: alpha * 0.7,
    });
  }
  [34, 44, 54].forEach((age, index) => {
    const anchor = basePoint(age);
    dot3(ctx, frame, [anchor[0], anchor[1] + 620, anchor[2]], 3.8, GRAY,
      alpha * (0.72 - index * 0.07));
  });
  drawLabel(ctx, frame, add(basePointLift(38, 620), [0, -70, 0]), labels.learningUpper,
    36, alpha * 0.9, GRAY, 'left', 0, 0.84);

  // 下方：持续学习，节点连成一张越来越大的知识网络。
  const combined = LEARNING_NODES;
  combined.forEach((node, index) => {
    const reveal = span(t, node.reveal, node.reveal + 0.45) * alpha;
    if (reveal <= 0) return;
    if (index > 0) {
      const prev = combined[index - 1].at;
      strokeWorld(ctx, frame, [prev, node.at], {
        color: BLUE, width: 1.3, alpha: 0.52 * reveal,
      });
    }
    if (index > 1) {
      const prev = combined[index - 2].at;
      strokeWorld(ctx, frame, [prev, node.at], {
        color: BLUE, width: 1.0, alpha: 0.32 * reveal,
      });
    }
    if (index > 2) {
      const prev = combined[index - 3].at;
      strokeWorld(ctx, frame, [prev, node.at], {
        color: BLUE, width: 0.8, alpha: 0.2 * reveal,
      });
    }
    dot3(ctx, frame, node.at, 4.2, BLUE, reveal);
    drawLabel(ctx, frame, add(node.at, [0, index % 2 === 0 ? -30 : 32, 0]),
      labels.learningNodes[index] ?? '', 30, 0.92 * reveal, CREAM, 'center', 0, 0.84);
  });
  drawLabel(ctx, frame, add(learningPoint(58), [0, 110, 0]), labels.learningLower,
    36, alpha, PALE, 'center', 0, 0.84);

  // 学习支线与主线的连接：一条极淡的竖向关系，不写解释。
  const bridgeA = learningPoint(44);
  const bridgeB = lifePoint(44);
  strokeWorld(ctx, frame, [bridgeA, bridgeB], {
    color: BLUE, width: 1, alpha: alpha * 0.18, dash: [5, 9],
  });
}

function basePointLift(age: number, lift: number): Vec3 {
  const anchor = basePoint(age);
  return [anchor[0], anchor[1] + lift, anchor[2]];
}

// ------------------------------------------------------------------ 决策树

function drawScreenText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  size: number,
  alpha: number,
  color = CREAM,
) {
  if (alpha <= 0.01) return;
  ctx.font = `400 ${size}px "M2V Sans", sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = rgba(INK, 0.85 * alpha);
  ctx.lineWidth = Math.max(3, size * 0.18);
  ctx.strokeText(text, x, y);
  ctx.fillStyle = rgba(color, alpha);
  ctx.fillText(text, x, y);
}

function drawTree(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
  labels: Labels,
) {
  const base = actAlpha(t, 52.0, 58.6, 0.8);
  if (base <= 0.005) return;
  const fade = 1 - span(t, 56.0, 58.2) * 0.92;
  const alpha = base * fade;

  TREE_PATHS.forEach((path, index) => {
    if (path.bright) return;
    const reveal = span(t, 52.1 + (index % 12) * 0.09, 53.1 + (index % 12) * 0.09);
    if (reveal <= 0) return;
    strokeWorldBatch(ctx, frame, path.points, {
      color: index % 3 === 0 ? BLUE : '#8fb6d9', width: 1.5, alpha: path.alpha * alpha * reveal,
    });
    if (reveal > 0.7) {
      const end = path.points[path.points.length - 1];
      dot3(ctx, frame, end, 2.4, BLUE, 0.65 * path.alpha * alpha * reveal);
    }
  });
  TREE_PATHS.forEach((path) => {
    if (!path.bright) return;
    const reveal = span(t, 52.7, 54.0);
    strokeWorldBatch(ctx, frame, path.points, {
      color: PALE, width: 6.0, alpha: alpha * 0.94 * reveal, glow: 0.3,
    });
    if (reveal > 0.8) {
      const end = path.points[path.points.length - 1];
      dot3(ctx, frame, end, 6.5, PALE, alpha * 0.95);
    }
  });

  // 五个决策点：小环 + 逐项出现的一行标签，避免透视压缩后叠在一起。
  DECISION_AGES.forEach((age, index) => {
    const reveal = span(t, 54.2 + index * 0.24, 54.7 + index * 0.24) * alpha;
    if (reveal <= 0) return;
    const point = lifePoint(age);
    const p = projection(frame, point);
    if (p.visible) {
      const r = clamp(p.rel, 0.6, 1.6);
      ctx.strokeStyle = rgba(BLUE, reveal * 0.7);
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 7 * r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = rgba(BLUE, reveal * 0.55);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2.2 * r, 0, Math.PI * 2);
      ctx.fill();
    }
  });
  const rowAlpha = span(t, 54.2, 54.7) * alpha;
  labels.choices.forEach((text, index) => {
    const reveal = span(t, 54.2 + index * 0.24, 54.6 + index * 0.24) * rowAlpha;
    drawScreenText(ctx, text, 220 + index * 175, 838, 36, reveal * 0.92,
      index === 4 ? PALE : CREAM);
  });
}

// ------------------------------------------------------------------ 主体

function drawSubject(
  ctx: CanvasRenderingContext2D,
  frame: CameraFrame,
  t: number,
) {
  const act = t >= 52 ? 'ending' : t >= 44 ? 'learning' : t >= 35.5 ? 'investment'
    : t >= 27 ? 'partner' : 'other';
  if (act === 'investment' || act === 'partner') return;
  const point = lifePoint(ageAt(t));
  const fade = 1 - span(t, 57.8, 59.2);
  const trail: Vec3[] = [];
  const from = Math.max(0, t - 1.4);
  for (let s = from; s <= t + 0.001; s += 0.12) trail.push(lifePoint(ageAt(s)));
  strokeWorldBatch(ctx, frame, trail, {color: PALE, width: 2.2, alpha: 0.32 * fade, glow: 0.16});
  dot3(ctx, frame, point, 6.2, PALE, 0.96 * fade);
  const p = projection(frame, point);
  if (p.visible && p.rel > 0.35) {
    const r = clamp(6.2 * p.rel, 3, 13);
    const halo = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 7);
    halo.addColorStop(0, rgba(BLUE, 0.18 * fade));
    halo.addColorStop(0.4, rgba(BLUE, 0.06 * fade));
    halo.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(p.x, p.y, r * 7, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ------------------------------------------------------------------ 文字压暗

function drawCopyScrims(
  ctx: CanvasRenderingContext2D,
  copy: CopyItem[],
  t: number,
  w: number,
  h: number,
) {
  for (const item of copy) {
    const inP = span(t, item.from, item.from + 0.55);
    const outP = span(t, item.to - 0.55, item.to);
    const opacity = inP * (1 - outP);
    if (opacity <= 0.02) continue;
    const cx = item.x + item.width / 2;
    const cy = item.y + item.size * 0.72;
    const radius = Math.max(item.width * 0.46, item.size * 2.6);
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    gradient.addColorStop(0, `rgba(3, 5, 8, ${(item.size > 120 ? 0.52 : 0.4) * opacity})`);
    gradient.addColorStop(0.55, `rgba(3, 5, 8, ${(item.size > 120 ? 0.3 : 0.22) * opacity})`);
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

  // 城市与行业段给一点地面网格，提供透视参照。
  if (t >= 6.5 && t <= 27.5) {
    const groundAlpha = actAlpha(t, 6.5, 27.5, 1.2) * 0.08;
    for (let age = 18; age <= 62; age += 2) {
      const anchor = lifePoint(age);
      strokeWorld(ctx, frame, [
        [anchor[0], anchor[1] - 150, -760],
        [anchor[0], anchor[1] - 150, 760],
      ], {color: BLUE, width: 0.6, alpha: groundAlpha});
    }
    for (let z = -720; z <= 720; z += 120) {
      strokeWorld(ctx, frame, [
        [ageX(18), lifePoint(18)[1] - 150, z],
        [ageX(62), lifePoint(62)[1] - 150, z],
      ], {color: BLUE, width: 0.5, alpha: groundAlpha * 0.8});
    }
  }

  drawTimeline(ctx, frame, t, props.labels);
  drawCity(ctx, frame, t, props.labels);
  drawIndustry(ctx, frame, t, props.labels);
  drawPartnerSplit(ctx, cam, t, props.labels, width, height);
  drawInvestment(ctx, frame, t, props.labels);
  drawLearning(ctx, frame, t, props.labels);
  drawTree(ctx, frame, t, props.labels);
  drawSubject(ctx, frame, t);

  drawVignette(ctx, width, height);
  drawCopyScrims(ctx, props.copy, t, width, height);

  const blackout = span(t, 58.15, 58.6);
  if (blackout > 0) {
    ctx.fillStyle = `rgba(0, 0, 0, ${blackout})`;
    ctx.fillRect(0, 0, width, height);
  }
}
