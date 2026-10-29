/**
 * 《折叠》示例：一串珠子怎么折，决定细胞是什么形状。
 *
 * 选题与分镜按外部参考项目已登记的 fold_C 样片重写；实现、形体与配色由本仓库的
 * `vibe-night` 组件与绘制原语自行构造，不复制上游 `film.js`、GIF/JPG 或画面。
 *
 * **一个世界，一台摄影机，两个尺度。** 血红蛋白与红细胞不在同一个尺度上：一个红细胞
 * 里约有 2.7 亿个血红蛋白分子。所以世界坐标分两层——
 *
 * - 珠层：珠距 31.5、单珠半径 14、折后一团半径约 197；
 * - 细胞层：红细胞半径 250 像素。
 *
 * `RHO` 是两层之间的换算（珠层 1 单位 = 细胞层 `1/RHO` 像素）。整片只有一条相机
 * 时间轴，观众看到什么由**相机远近**决定：拉远时看见红细胞、珠子缩成一片模糊的
 * 小点；推近时红细胞退场、珠子浮现。九幕不是九个机位，而是这台摄影机的九段行程。
 */
import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps, painter} from 'm2v/code-scene';
import GlowText from 'm2v/style/components/glow-text';
import ChapterMark from 'm2v/style/components/chapter-mark';
import Dip from 'm2v/style/components/dip';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';
import {loadNightSerif} from 'm2v/style/components/kit';
import layoutData from './layout.json';

type Chapter = {id: string; index: string; character: string; title: string; caption: string};
type Subtitle = {startFrame: number; endFrame: number; text: string};
type Clock = {startSeconds: number};
type Props = {chapter: Chapter; clock: Clock; screenSubtitles: Subtitle[]; credit?: string};

type P = InstanceType<typeof painter.Painter>;
type Vec = [number, number];
type FoldLayout = {
  D: number; pitch: number; R: number; knob: number;
  cavity: Vec; notch: Vec; pts: Vec[];
};
const F = layoutData as unknown as FoldLayout;

const WHITE = '#F8F9F8';
const GOLD = '#F8D893';
const ICE = '#64E3F6';
const ROSE = '#E84B75';
const MUTED = '#879399';
// 血的实体与氧气：参考片的两个关键语义色，已登记进 tokens。
const BLOOD = '#C8384E';
const OXYGEN = '#FF6A55';
// 画布文字使用包内登记的宋体族；`serif` 是通用族，会静默回退到系统字体。
const SERIF = '"Vibe Night Serif", "Noto Serif SC", serif';

// ---------------------------------------------------------------- 世界尺度

/** 珠层单位；折前折后相邻两颗的距离都是它。 */
const D = 31.5;
const BEAD_R = 14;
/** 珠层 → 细胞层的换算：珠层 1 单位约等于细胞层的 1/66。 */
const RHO = 66;
/** 红细胞在细胞层的半径（像素），与参考样片一致。 */
const CELL_R_PX = 250;
/** 同一个半径换到珠层单位。 */
const CELL_R = CELL_R_PX * RHO;
/** 「整个细胞」的相机尺度：1 珠层单位画 1/66 像素。 */
const CELL_SCALE = 1 / RHO;

const ROW_Y = [-114, -38, 38, 114];
const ROW_X = 527.5;
const CORNER_R = 38;
const SEQ = 'VHLTPEEKSAVT';
const KNOB = F.knob;
const PITCH = F.pitch;

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
const smooth = (value: number) => {const t = clamp01(value); return t * t * (3 - 2 * t);};
const mix = (index: number, total: number) => total <= 1 ? 0 : index / (total - 1);

/** 把十六进制色按比例混向目标色；用来从单一语义色推出明暗阶。 */
function shade(hex: string, toward: string, amount: number): string {
  const parse = (value: string) => [1, 3, 5].map(at => parseInt(value.slice(at, at + 2), 16));
  const [r1, g1, b1] = parse(hex);
  const [r2, g2, b2] = parse(toward);
  const blend = (a: number, b: number) => Math.round(a + (b - a) * clamp01(amount)).toString(16).padStart(2, '0');
  return `#${blend(r1, r2)}${blend(g1, g2)}${blend(b1, b2)}`;
}

/**
 * 蛇形珠串：四行折返，行尾半圆接下一行，再按弧长均匀重采样成 146 个点。
 *
 * 先铺一条足够密的折线，再按累计弧长取等距点——相邻两颗因此始终等于 `D`，
 * 珠串读起来是一条连续的链，而不是几段各自排开的点。
 */
const SERPENTINE: Vec[] = (() => {
  const dense: Vec[] = [];
  ROW_Y.forEach((y, row) => {
    const outward = row % 2 === 0;
    if (outward) {
      for (let x = -ROW_X; x <= ROW_X; x += 2) dense.push([x, y]);
    } else {
      for (let x = ROW_X; x >= -ROW_X; x -= 2) dense.push([x, y]);
    }
    if (row < ROW_Y.length - 1) {
      const centerX = outward ? ROW_X : -ROW_X;
      for (let a = -Math.PI / 2; a <= Math.PI / 2; a += 0.02) {
        dense.push([centerX + CORNER_R * Math.cos(outward ? a : Math.PI - a), y + CORNER_R + CORNER_R * Math.sin(a)]);
      }
    }
  });
  const cumulative = [0];
  for (let index = 1; index < dense.length; index += 1) {
    cumulative.push(cumulative[index - 1] + Math.hypot(
      dense[index][0] - dense[index - 1][0], dense[index][1] - dense[index - 1][1]));
  }
  const length = cumulative[cumulative.length - 1];
  const points: Vec[] = [];
  let cursor = 0;
  for (let index = 0; index < 146; index += 1) {
    const target = length * index / 145;
    while (cursor < dense.length - 2 && cumulative[cursor + 1] < target) cursor += 1;
    const span = cumulative[cursor + 1] - cumulative[cursor] || 1;
    const ratio = (target - cumulative[cursor]) / span;
    points.push([
      dense[cursor][0] + (dense[cursor + 1][0] - dense[cursor][0]) * ratio,
      dense[cursor][1] + (dense[cursor + 1][1] - dense[cursor][1]) * ratio,
    ]);
  }
  return points;
})();

/**
 * 折好的一团来自 `tools/gen_layout.py`：六角格上一条走遍 146 个格点的路径。
 *
 * 先保证关系，再谈外观：相邻两颗始终等于 `D`；第 6 颗是右侧凸点（knob），
 * 左侧留凹口（notch）；中间两个相邻空腔（cavity）放氧分子。接合时
 * `pitch < 2R`，凸点卡进凹口，两团的格点集合不重合。
 *
 * 生成脚本已经断言过；这里在场景加载时再查一遍，避免手工改 `layout.json`
 * 绕过关系检查。
 */
const BLOB: Vec[] = F.pts;
const BLOB_RADIUS = F.R;
(() => {
  if (F.D !== D) throw new Error('折叠布局的格距与场景不一致');
  if (BLOB.length !== 146) throw new Error(`折叠布局应有 146 颗珠子，实际 ${BLOB.length}`);
  if (new Set(BLOB.map(([x, y]) => `${x},${y}`)).size !== BLOB.length) {
    throw new Error('折叠布局有重复格点');
  }
  for (let index = 0; index < BLOB.length - 1; index += 1) {
    const [x0, y0] = BLOB[index], [x1, y1] = BLOB[index + 1];
    if (Math.abs(Math.hypot(x1 - x0, y1 - y0) - D) > 0.03) {
      throw new Error(`折叠布局第 ${index} 与 ${index + 1} 颗不相邻`);
    }
  }
  if (F.knob !== 5 || KNOB !== 5) throw new Error('折叠布局的 knob 必须是第 6 颗');
  if (!(F.pitch < 2 * F.R)) throw new Error('折叠布局的接合间距没有形成交错');
})();

// ---------------------------------------------------------------- 细胞形体

/**
 * 红细胞轮廓：`bend = 0` 是圆盘，`1` 是两头朝上、带尖的镰刀。
 *
 * 把单位圆盘上的点映射到镰刀的参数域：横向拉长、纵向按 `(1 - x*x)^0.6` 收出两端的尖、
 * 中线随 `x*x` 下垂，最后整体转 -0.26 弧度。同一个参数域连续变形，所以观众看到的是
 * **一个东西在弯**，而不是两个形状互相切换。
 */
function cellPoint(px: number, py: number, bend: number): Vec {
  const roundX = CELL_R * px;
  const roundY = CELL_R * py;
  const v = Math.max(-1, Math.min(1, py / Math.sqrt(Math.max(1e-6, 1 - px * px))));
  const half = 0.42 * CELL_R * Math.pow(Math.max(0, 1 - px * px), 0.6);
  const centre = CELL_R * (0.2 - 0.55 * px * px);
  const sickleX = 1.7 * CELL_R * px;
  const sickleY = centre + half * v;
  const x = roundX + (sickleX - roundX) * bend;
  const y = roundY + (sickleY - roundY) * bend;
  const angle = -0.26 * bend;
  const cos = Math.cos(angle), sin = Math.sin(angle);
  return [x * cos - y * sin, x * sin + y * cos];
}

function cellContour(bend: number, samples = 96): Vec[] {
  const points: Vec[] = [];
  // 沿圆周取点：上缘从右到左、下缘从左到右，`py` 必须落在单位圆上，
  // 取 ±1 会得到包围盒而不是圆。
  for (let index = 0; index <= samples; index += 1) {
    const px = 1 - 2 * index / samples;
    points.push(cellPoint(px, Math.sqrt(Math.max(0, 1 - px * px)), bend));
  }
  for (let index = 0; index <= samples; index += 1) {
    const px = -1 + 2 * index / samples;
    points.push(cellPoint(px, -Math.sqrt(Math.max(0, 1 - px * px)), bend));
  }
  return points;
}

function polyPath(points: Vec[]): string {
  return points.map((point, index) => `${index ? 'L' : 'M'} ${point[0].toFixed(1)},${point[1].toFixed(1)}`).join(' ') + ' Z';
}

/**
 * 红细胞：深的血红色圆盘，中间凹窝由多层更暗的同心轮廓叠出软边，左上有一段加宽的
 * 高光弧。它画在 `under` 层——参考片的实物不吃辉光，进了辉光会糊成粉色光团。
 */
function redCell(P: P, bend: number, cx: number, cy: number, alpha = 1, tint = BLOOD) {
  if (alpha <= 0.004) return;
  P.group({at: [cx, cy], alpha}, () => {
    // 血色的五段渐变：中间偏亮、边缘压暗，才能读出「有厚度的盘」而不是一块平色。
    // 镰刀展开得比圆盘宽，渐变半径同步放大，让可见区域仍落在亮段上。
    const reach = CELL_R * (1 + 0.75 * bend);
    const body = P.radialGradient(0, 0, 0, 0, 0, Math.max(1, reach),
      [[0, '#8E1626'],
        [0.3, '#B4283C'],
        [0.58, '#D2435A'],
        [0.82, '#DE5566'],
        [1, '#A81C30']]);
    P.path(polyPath(cellContour(bend)), {fill: body});
    for (const k of [0.64, 0.6, 0.56, 0.52, 0.48, 0.44, 0.4, 0.36, 0.32, 0.28, 0.24]) {
      const ring: Vec[] = [];
      for (let index = 0; index <= 72; index += 1) {
        const angle = index / 72 * Math.PI * 2;
        ring.push(cellPoint(k * Math.cos(angle), k * Math.sin(angle), bend));
      }
      P.path(polyPath(ring), {fill: '#3D0710', alpha: 0.05 * (1 - 0.4 * bend)});
    }
    P.poly(cellContour(bend), {color: '#F27C92', width: CELL_R * 0.01, alpha: 0.6});
    const highlight: Vec[] = [];
    for (let index = 0; index <= 26; index += 1) {
      const angle = (198 + index * 4) / 180 * Math.PI;
      highlight.push(cellPoint(0.9 * Math.cos(angle), 0.9 * Math.sin(angle), bend));
    }
    for (let index = 0; index < highlight.length - 1; index += 1) {
      P.line(highlight[index][0], highlight[index][1], highlight[index + 1][0], highlight[index + 1][1],
        {color: '#FFD3DA', width: CELL_R * 0.04, alpha: 0.26});
    }
  });
}

/**
 * 细胞里散落的血红蛋白。
 *
 * 位置用固定种子的低差异序列铺开，不排成同心环——排成环会读成装饰图案，
 * 而不是「里面塞满了分子」。分子本身很小，远了只看得出是一片弱光。
 */
function molecules(P: P, bend: number, alpha: number) {
  if (alpha <= 0.004) return;
  const COUNT = 300;
  for (let index = 0; index < COUNT; index += 1) {
    // 黄金角螺旋 + 轻微抖动：分布均匀但不呈现可见的环。
    const golden = index * 2.399963229728653;
    const radius = Math.sqrt((index + 0.5) / COUNT) * 0.93;
    const jitter = Math.sin(index * 12.9898) * 0.02;
    const [x, y] = cellPoint(
      (radius + jitter) * Math.cos(golden),
      (radius + jitter) * Math.sin(golden),
      bend,
    );
    P.circle(x, y, CELL_R * 0.011, {fill: '#F8BECB', alpha: 0.42 * alpha});
  }
}

// ---------------------------------------------------------------- 珠子形体

/**
 * 珠子：四段径向渐变的小球——白热核、偏移高光、本色、混入冷色的暗边。
 * 偏移的渐变是它读成「有体积的球」而不是「荧光点」的原因。
 */
function bead(P: P, x: number, y: number, radius: number, tint: string, alpha = 1) {
  if (radius < 0.35 || alpha <= 0.004) return;
  const body = P.radialGradient(
    x - radius * 0.34, y - radius * 0.38, radius * 0.04, x, y, radius * 1.04,
    [[0, shade(tint, '#FFFFFF', 0.88), alpha],
      [0.2, shade(tint, '#FFFFFF', 0.32), alpha],
      [0.62, tint, alpha],
      [1, shade(tint, '#020510', 0.72), alpha]],
  );
  P.circle(x, y, radius, {fill: body});
}

function chainLine(P: P, points: Vec[], width: number, depth: (index: number) => number) {
  for (let index = 0; index < points.length - 1; index += 1) {
    const alpha = 0.6 * Math.min(depth(index), depth(index + 1));
    if (alpha < 0.02) continue;
    P.line(points[index][0], points[index][1], points[index + 1][0], points[index + 1][1],
      {color: '#9FB6C8', width: Math.max(0.4, width), alpha});
  }
}

function blobHalo(P: P, alpha: number) {
  if (alpha <= 0.004) return;
  const radius = BLOB_RADIUS + 26;
  const halo = P.radialGradient(-BLOB_RADIUS * 0.3, -BLOB_RADIUS * 0.36, 0, 0, 0, radius,
    [[0, '#9FD8E8', 0.13 * alpha], [0.82, '#9FD8E8', 0.09 * alpha], [1, '#9FD8E8', 0]]);
  P.circle(0, 0, radius, {fill: halo});
}

function hemePocket(P: P, x: number, y: number, bound: number) {
  P.circle(x, y, 17, {fill: shade('#4A0A14', '#FF6A55', 0.55 * bound)});
  P.circle(x, y, 17, {color: shade('#C23650', '#FFB3A6', bound), width: 2.4});
}

function oxygen(P: P, x: number, y: number, radius: number, alpha: number) {
  if (alpha <= 0.004) return;
  bead(P, x - radius * 0.56, y + radius * 0.12, radius, OXYGEN, alpha);
  bead(P, x + radius * 0.56, y - radius * 0.12, radius, OXYGEN, alpha);
  P.glow(x, y, radius * 4.5, OXYGEN, 0.35 * alpha);
}

/** 珠子的深度明暗：越靠外越暗，让密团有体积。 */
function blobDepth(index: number): number {
  const deep = Math.hypot(BLOB[index][0], BLOB[index][1]) / Math.max(1, BLOB_RADIUS);
  return 1 - 0.55 * deep * deep;
}

/** 一整团：底光、连线、除黏点以外的珠子。 */
function blobBody(P: P, radius = BEAD_R) {
  blobHalo(P, 1);
  chainLine(P, BLOB, radius * 0.17, blobDepth);
  BLOB.forEach((point, index) => {
    if (index === KNOB) return;
    bead(P, point[0], point[1], radius, shade(ICE, '#03101C', 0.9 * (1 - blobDepth(index))), 1);
  });
}

// ---------------------------------------------------------------- 摄影机

/**
 * 全片相机关键帧（秒）。世界坐标用珠层单位，`scale` 是「1 珠层单位画多少像素」。
 *
 * 行程：血管全景（几颗红细胞漂着）→ 推进正中那颗的珠串 → 再推近前十二颗 →
 * **在「形」幕里一路拉远**，回到细胞尺度并看它弯成镰刀 → 「问」极慢推近 →
 * 「折」推回珠层看折叠成团 → 拉远看长杆 → 「顶」拉回细胞尺度。
 *
 * 缩放连续变化，幕与幕之间不留尺度跳变。九幕分界是
 * 4.4 / 8.4 / 12.6 / 15.0 / 19.2 / 22.8 / 26.0 / 29.2 秒。
 */
const CAM: painter.CameraKey[] = [
  // 01 珠：血管全景 → 推入珠串。
  {at: 0, scale: 0.0175, focusX: 0, focusY: 0},
  {at: 1.8, scale: 0.0175, focusX: 0, focusY: 0},
  {at: 4.0, scale: 0.95, focusX: 0, focusY: 0},
  {at: 4.4, scale: 0.95, focusX: 0, focusY: 0},
  // 02 错：继续推近前十二颗。
  {at: 5.8, scale: 2.4, focusX: -330, focusY: -114},
  {at: 8.4, scale: 2.4, focusX: -330, focusY: -114},
  // 03 形：幕内立刻拉远到细胞尺度；字幕出现前必须已经看得见整颗细胞。
  {at: 9.15, scale: 0.019, focusX: 0, focusY: 0},
  {at: 12.6, scale: 0.019, focusX: 0, focusY: 0},
  // 04 问：镰刀停住，只做极慢的推近。
  {at: 15.0, scale: 0.0205, focusX: 0, focusY: 0},
  // 05 折：推回珠层看折叠。
  {at: 16.8, scale: 1.3, focusX: 0, focusY: 0},
  {at: 19.2, scale: 1.6, focusX: 0, focusY: 0},
  // 06 黏：留在珠层。
  {at: 22.8, scale: 1.6, focusX: 0, focusY: 0},
  // 07 杆：拉远到能看全九团。
  {at: 24.2, scale: 0.42, focusX: 0, focusY: 0},
  {at: 26.0, scale: 0.42, focusX: 0, focusY: 0},
  // 08 顶：拉回细胞尺度，看长杆从里面把细胞顶弯。
  {at: 27.4, scale: 0.0195, focusX: 0, focusY: 0},
  {at: 29.2, scale: 0.0195, focusX: 0, focusY: 0},
  // 09 结：镰刀停住。
  {at: 33.0, scale: 0.0155, focusX: 0, focusY: 0},
];

/**
 * 细胞什么时候可见：`scale × RHO` 是细胞层的屏幕缩放。它小于 5 时细胞还没铺满
 * 画面（看得见全貌），超过 28 时相机已经在细胞内部，细胞本体退场。
 */
const cellAlpha = (scale: number) => 1 - smooth((scale * RHO - 5) / 23);
/** 珠子什么时候可见：相机推近到珠层才浮现；再远就只是一片模糊的点。 */
const beadAlpha = (scale: number) => smooth((scale - 0.06) / (0.22 - 0.06));

type SceneProps = {
  camera: painter.CameraState;
  width: number;
  height: number;
  frame: number;
};

/** 在相机里画：世界坐标经缩放与焦点平移落到屏幕上。 */
function world(P: P, camera: painter.CameraState, width: number, height: number, draw: () => void) {
  P.group({
    at: [width / 2 - camera.focusX * camera.scale, height / 2 - camera.focusY * camera.scale],
    scale: camera.scale,
  }, draw);
}

/**
 * 统一的开场：近黑底 + 中央深蓝光池 + 暗角。
 *
 * 底色自己铺，不用 `NightBackdrop`：内容画布在合成时会先铺一层不透明黑，
 * DOM 层的星点底拿不到像素，铺了也看不见，只会白白多跑一遍绘制。
 *
 * 层序按参考片：`background` 底 → `under` 实物（红细胞，不吃辉光）→
 * `paint` 发光体（珠子，吃辉光）→ `overlay` 文字（锐利）。
 */
function Layer({camera, width, height, under, paint, overlay}: {
  camera: painter.CameraState;
  width: number;
  height: number;
  under?: (P: P) => void;
  paint: (P: P) => void;
  overlay?: (P: P) => void;
}) {
  return <painter.PainterCanvas width={width} height={height} bloom={0.55} grain={0.045} seed={11}
    background={(P) => {
      P.clear('#010104');
      const pool = P.radialGradient(width / 2, height * 0.44, 0, width / 2, height * 0.44, width * 0.62,
        [[0, '#0B1830', 0.62], [0.55, '#0B1830', 0.34], [1, '#0B1830', 0]]);
      P.rect(0, 0, width, height, {fill: pool});
      const vignette = P.radialGradient(width / 2, height / 2, width * 0.34, width / 2, height / 2, width * 0.78,
        [[0, '#000000', 0], [0.78, '#000000', 0.3], [1, '#000000', 0.7]]);
      P.rect(0, 0, width, height, {fill: vignette});
    }}
    under={under ? (P) => world(P, camera, width, height, () => under(P)) : undefined}
    paint={(P) => world(P, camera, width, height, () => paint(P))}
    overlay={overlay ? (P) => world(P, camera, width, height, () => overlay(P)) : undefined}/>;
}

/** 珠串按顺序折：越靠后的珠子越晚出发，折起来像一条被收进去的链。 */
function foldPositions(frame: number): {points: Vec[]; progress: (index: number) => number} {
  const start = (index: number) => 8 + 0.5 * index / 145 * 22;
  const progress = (index: number) => smooth((frame - start(index)) / 26);
  const points = SERPENTINE.map((from, index) => {
    const k = progress(index);
    if (k <= 0) return from;
    const to = BLOB[index];
    const x = from[0] + (to[0] - from[0]) * k;
    const y = from[1] + (to[1] - from[1]) * k;
    const swing = 0.85 * Math.sin(Math.PI * k);
    const cos = Math.cos(swing), sin = Math.sin(swing);
    return [x * cos - y * sin, x * sin + y * cos] as Vec;
  });
  return {points, progress};
}

// ---------------------------------------------------------------- 各幕

function ChainScene({camera, width, height, frame}: SceneProps) {
  const lit = Math.max(1, Math.round(BLOB.length * smooth((frame - 4) / 66)));
  const beads = beadAlpha(camera.scale);
  return (
    <Layer camera={camera} width={width} height={height}
      under={(P) => {
        const alpha = cellAlpha(camera.scale);
        if (alpha <= 0) return;
        redCell(P, 0, 0, 0, alpha, BLOOD);
        molecules(P, 0, alpha);
      }}
      paint={(P) => {
        if (beads <= 0) return;
        chainLine(P, SERPENTINE, BEAD_R * 0.17 * camera.scale, () => beads);
        SERPENTINE.forEach((point, index) => {
          if (index >= lit) return;
          // 正在被数到的那一颗鼓一下，数珠子的动作因此看得见。
          const bump = Math.exp(-Math.pow((index - lit) / 2.4, 2));
          bead(P, point[0], point[1], BEAD_R * (1 + 0.3 * bump),
            bump > 0.05 ? shade(ICE, '#FFFFFF', 0.45 * bump) : index === 0 ? GOLD : ICE, beads);
        });
      }}/>
  );
}

function MutationScene({camera, width, height, frame}: SceneProps) {
  const squash = Math.max(0.04, Math.abs(Math.cos(Math.PI * smooth((frame - 30) / 20))));
  const mutated = frame >= 42;
  const ripple = (frame - 40) / 24;
  const head = SERPENTINE.slice(0, 12);
  return (
    <Layer camera={camera} width={width} height={height}
      paint={(P) => {
        chainLine(P, head, BEAD_R * 0.17 * camera.scale, () => 1);
        head.forEach((point, index) => {
          if (index === KNOB) return;
          bead(P, point[0], point[1], BEAD_R, ICE, 1);
        });
        const [kx, ky] = head[KNOB];
        // 第 6 颗翻面：横向压扁再摊开，颜色在翻面之后换成玫红。
        P.group({at: [kx, ky], scale: [squash, 1]}, () => bead(P, 0, 0, BEAD_R, mutated ? ROSE : ICE, 1));
        if (mutated) P.glow(kx, ky, BEAD_R * 4.2, ROSE, 0.3);
        if (ripple > 0 && ripple < 1) {
          P.circle(kx, ky, BEAD_R * (1.3 + 3.2 * smooth(ripple)), {color: ROSE, width: 1.1, alpha: 1 - ripple});
        }
      }}
      overlay={(P) => {
        // 字母行贴在每颗珠子下方，是同一个东西的一部分。
        head.forEach((point, index) => {
          const sixth = index === KNOB;
          P.text(sixth && mutated ? 'V' : SEQ[index], point[0], point[1] + BEAD_R + 26, {
            size: 40, color: sixth ? (mutated ? ROSE : WHITE) : MUTED, font: SERIF,
            alpha: sixth ? 1 : 0.8,
          });
        });
        const [kx, ky] = head[KNOB];
        P.line(kx, ky - BEAD_R - 18, kx, ky - BEAD_R - 46, {color: MUTED, width: 1.1, alpha: 0.7});
      }}/>
  );
}

/** 拉远：珠子退成细胞里的一片点，同一个轮廓连续弯成镰刀。 */
function SickleScene({camera, width, height, frame}: SceneProps) {
  const bend = smooth((frame - 24) / 62);
  const beads = beadAlpha(camera.scale) * 0.9;
  const cell = cellAlpha(camera.scale);
  return (
    <Layer camera={camera} width={width} height={height}
      under={(P) => {
        if (cell <= 0) return;
        redCell(P, bend, 0, 0, cell, BLOOD);
        molecules(P, bend, cell);
      }}
      paint={(P) => {
        if (beads <= 0) return;
        // 珠子保持在自己的世界坐标上：相机拉远时它们自然缩成细胞里的一片点，
        // 不需要另换一套几何。
        chainLine(P, SERPENTINE, BEAD_R * 0.17 * camera.scale, () => beads);
        SERPENTINE.forEach((point, index) => {
          bead(P, point[0], point[1], BEAD_R, index === KNOB ? ROSE : ICE, beads);
        });
      }}
      overlay={(P) => {
        if (cell < 0.4) return;
        const label = (text: string, at: Vec, color: string) => {
          P.line(at[0], at[1], at[0] + CELL_R * 0.5, at[1] - CELL_R * 0.3,
            {color, width: CELL_R * 0.006, alpha: 0.5 * cell});
          P.text(text, at[0] + CELL_R * 0.56, at[1] - CELL_R * 0.34,
            {size: CELL_R * 0.15, color, font: SERIF, alpha: cell, align: 'left'});
        };
        label(bend > 0.55 ? '镰状细胞' : '红细胞', cellPoint(0.72, 0.5, bend), bend > 0.55 ? ROSE : WHITE);
      }}/>
  );
}

/** 提问：镰刀停在那儿慢慢漂；漂浮只由帧号决定，不用计时器。 */
function QuestionScene({camera, width, height, frame}: SceneProps) {
  const drift = Math.sin(frame * 0.035) * CELL_R * 0.02;
  return (
    <Layer camera={camera} width={width} height={height}
      under={(P) => {
        const alpha = cellAlpha(camera.scale);
        if (alpha <= 0) return;
        redCell(P, 1, 0, drift, alpha, BLOOD);
        molecules(P, 1, alpha * 0.6);
      }}
      paint={() => undefined}/>
  );
}

/** 折叠：珠串每一颗从蛇形位置移到密团位置，氧分子随后落进小窝。 */
function FoldScene({camera, width, height, frame}: SceneProps) {
  const {points, progress} = foldPositions(frame);
  const folded = smooth((frame - 60) / 28);
  const oxygenIn = smooth((frame - 76) / 32);
  const pocket: Vec = F.cavity;
  return (
    <Layer camera={camera} width={width} height={height}
      under={(P) => {
        const alpha = cellAlpha(camera.scale);
        if (alpha <= 0) return;
        redCell(P, 0, 0, 0, alpha, BLOOD);
        molecules(P, 0, alpha);
      }}
      paint={(P) => {
        blobHalo(P, folded);
        chainLine(P, points, BEAD_R * 0.17 * camera.scale, (index) => 1 - 0.55 * progress(index));
        if (folded > 0) hemePocket(P, pocket[0], pocket[1], oxygenIn);
        points.forEach((point, index) => {
          const depth = Math.hypot(point[0], point[1]) / Math.max(1, BLOB_RADIUS);
          const tint = index === KNOB && folded > 0.2 ? ROSE : shade(ICE, '#03101C', 0.9 * depth * depth);
          bead(P, point[0], point[1], BEAD_R, tint, 1);
        });
        if (oxygenIn > 0) {
          const from: Vec = [BLOB_RADIUS * 1.9, -BLOB_RADIUS * 1.5];
          const k = smooth(oxygenIn);
          oxygen(P, from[0] + (pocket[0] - from[0]) * k, from[1] + (pocket[1] - from[1]) * k, 12.5, oxygenIn);
        }
      }}/>
  );
}

function StickyScene({camera, width, height, frame}: SceneProps) {
  // 放下氧气以后：小窝暗下去，表面那颗玫红珠子鼓出来并一下一下地亮。
  const released = smooth((frame - 10) / 26);
  const pulse = 0.5 + 0.5 * Math.sin(frame * 0.16);
  const [kx, ky] = BLOB[KNOB];
  return (
    <Layer camera={camera} width={width} height={height}
      paint={(P) => {
        blobHalo(P, 1);
        hemePocket(P, F.cavity[0], F.cavity[1], 1 - released);
        chainLine(P, BLOB, BEAD_R * 0.17 * camera.scale, blobDepth);
        BLOB.forEach((point, index) => {
          if (index === KNOB) return;
          bead(P, point[0], point[1], BEAD_R, shade(ICE, '#03101C', 0.9 * (1 - blobDepth(index))), 1);
        });
        bead(P, kx, ky, BEAD_R * (1 + 0.22 * released), ROSE, 1);
        P.glow(kx, ky, BEAD_R * 4.2, ROSE, released * (0.28 + 0.3 * pulse));
      }}
      overlay={(P) => {
        if (released <= 0.05) return;
        P.line(kx + 24, ky - 20, kx + 112, ky - 84, {color: ROSE, width: 1.4, alpha: 0.7 * released});
        P.text('黏点', kx + 128, ky - 96, {size: 40, color: ROSE, font: SERIF, alpha: released, glow: 10});
      }}/>
  );
}

/** 一个粘一个：九团依次接上，越接越快，连成一根长杆。 */
function RodScene({camera, width, height, frame}: SceneProps) {
  // 接合中心距来自布局：pitch < 2R，前一团的 knob 正好落进后一团的 notch。
  return (
    <Layer camera={camera} width={width} height={height}
      paint={(P) => {
        // 承接上一幕的主团，其余团从中心向两端依次到达。
        const slots = [0, -1, 1, -2, 2, -3, 3, -4, 4];
        for (let index = 0; index < 9; index += 1) {
          const arrival = index === 0 ? 1 : smooth((frame - 4 - index * 6) / 18);
          if (arrival <= 0) continue;
          // 从长杆两端飞入，越靠外越晚到——接起来的顺序看得见。
          const distance = Math.abs(slots[index]) / 4;
          const side = slots[index] < 0 ? -1 : 1;
          const x = slots[index] * PITCH + side * 220 * (1 - arrival);
          const y = side * 120 * (1 - arrival) + distance * 60 * (1 - arrival);
          const rotation = side * 0.6 * (1 - arrival);
          P.group({at: [x, y], rotate: rotation, alpha: Math.min(1, arrival * 2.5)}, () => {
            blobBody(P);
            const [kx, ky] = BLOB[KNOB];
            bead(P, kx, ky, BEAD_R * 1.1, ROSE, 1);
            P.glow(kx, ky, BEAD_R * 4, ROSE, 0.45);
          });
        }
        // 刚接上的那一刻亮一下，把「粘住了」点明。
        for (let index = 1; index < 9; index += 1) {
          const flash = (frame - 22 - index * 6) / 14;
          if (flash <= 0 || flash >= 1) continue;
          P.glow(slots[index] * PITCH + BLOB[KNOB][0], BLOB[KNOB][1], 150,
            '#FFD0DA', 0.8 * (1 - flash));
        }
      }}/>
  );
}

/** 长杆从里面把细胞顶弯：同一轮廓再弯一次，内部是排开的长杆。 */
function PushScene({camera, width, height, frame}: SceneProps) {
  const bend = smooth((frame - 14) / 50);
  const rods = [-0.62, -0.31, 0, 0.31, 0.62];
  const reach = 0.2 + 0.62 * bend;
  const glide = smooth((frame - 26) / 42);
  return (
    <Layer camera={camera} width={width} height={height}
      under={(P) => {
        const alpha = cellAlpha(camera.scale);
        if (alpha <= 0) return;
        redCell(P, bend, 0, 0, alpha, BLOOD);
        // 细胞里的其它血红蛋白：先是一片散点，弯下时排到杆上。
        for (let index = 0; index < 150; index += 1) {
          const px = -0.92 + 1.84 * mix(index % 15, 15);
          const row = (mix(Math.floor(index / 15), 10) - 0.5) * 1.7;
          const limit = Math.sqrt(Math.max(0, 1 - px * px));
          const py = Math.max(-limit, Math.min(limit, row * limit));
          const nearest = rods.reduce((best, value) => Math.abs(value - row) < Math.abs(best - row) ? value : best, rods[0]);
          const gx = px + (Math.max(-reach, Math.min(reach, px)) - px) * glide;
          const gy = py + (nearest * Math.sqrt(Math.max(0, 1 - gx * gx)) - py) * glide;
          const [x, y] = cellPoint(gx, gy, bend);
          P.circle(x, y, CELL_R * 0.026, {fill: '#F8BECB', alpha: 0.62 * alpha});
        }
        // 长杆本身：沿参数域里的水平线排开，再映射到当前轮廓上。
        rods.forEach((row) => {
          const points: Vec[] = [];
          for (let index = 0; index <= 40; index += 1) {
            const px = -reach + 2 * reach * index / 40;
            points.push(cellPoint(px, row * Math.sqrt(Math.max(0, 1 - px * px)), bend));
          }
          P.poly(points, {color: '#FFE8EF', width: CELL_R * 0.02, alpha: (0.6 + 0.4 * bend) * alpha, glow: 16,
            glowColor: ROSE});
        });
      }}
      paint={() => undefined}/>
  );
}

function ClosingScene({camera, width, height}: SceneProps) {
  return (
    <Layer camera={camera} width={width} height={height}
      under={(P) => {
        const alpha = cellAlpha(camera.scale);
        if (alpha <= 0) return;
        redCell(P, 1, 0, CELL_R * 0.18, alpha * 0.9, BLOOD);
      }}
      paint={() => undefined}/>
  );
}

export default function Fold(props: CodeSceneProps & Props) {
  const {width, height, fps, subtitleSafeArea, props: values, durationInFrames} = props;
  const {chapter, clock, screenSubtitles, credit} = values;
  const {elapsedSeconds, ready} = useSceneContext();
  useEffect(() => { loadNightSerif().then(() => ready()); }, [ready]);
  const frame = Math.round(elapsedSeconds * fps);
  // 逐幕挂载：幕内时间 + 本幕在全片时间轴上的起点 = 全片时间，相机因此跨幕连续。
  const globalSeconds = (clock?.startSeconds ?? 0) + elapsedSeconds;
  const camera = painter.cameraAt(CAM, globalSeconds, smooth);
  const sceneProps = {camera, width, height, frame};

  const scene = (() => {
    switch (chapter.id) {
      case 'chain': return <ChainScene {...sceneProps}/>;
      case 'mutation': return <MutationScene {...sceneProps}/>;
      case 'sickle': return <SickleScene {...sceneProps}/>;
      case 'question': return <QuestionScene {...sceneProps}/>;
      case 'fold': return <FoldScene {...sceneProps}/>;
      case 'sticky': return <StickyScene {...sceneProps}/>;
      case 'rod': return <RodScene {...sceneProps}/>;
      case 'push': return <PushScene {...sceneProps}/>;
      default: return <ClosingScene {...sceneProps}/>;
    }
  })();

  return (
    <div style={{position: 'absolute', inset: 0, width, height}}>
      {scene}
      {/* 顶部渐变衬底：推近到满屏亮红时，保证章题与副标仍可读。 */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 230,
        background: 'linear-gradient(rgba(0,0,0,.55), rgba(0,0,0,0))', pointerEvents: 'none'}}/>
      {chapter.id !== 'closing' ? (
        <ChapterMark index={chapter.index} character={chapter.character} frame={frame} startFrame={0}/>
      ) : null}
      <GlowText text={chapter.title} x={width / 2} y={96} size={40}
        color={chapter.id === 'closing' ? GOLD : WHITE} glow={chapter.id === 'closing' ? 0.7 : 0.35}/>
      {chapter.caption && chapter.id !== 'closing' ? (
        <GlowText text={chapter.caption} x={width / 2} y={142} size={24} color={MUTED} glow={0.1}
          letterSpacing="0.3em"/>
      ) : null}
      {credit && frame >= 10 ? (
        <GlowText text={credit} x={width / 2} y={1018} size={44} color={WHITE} glow={0.2} opacity={0.92}/>
      ) : null}
      <ScreenSubtitle items={screenSubtitles} frame={frame} safeArea={subtitleSafeArea} fps={fps}/>
      {/* 黑场只留给片尾；开场不再做先亮后暗的 Dip，避免第一帧闪一下。 */}
      {chapter.id === 'closing' ? (
        <Dip frame={frame} startFrame={durationInFrames - 30} durationFrames={30} peak={1} holdEnd/>
      ) : null}
    </div>
  );
}
