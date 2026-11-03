/**
 * 《接》的纯函数几何：一条主动线在螺旋、纸、棋盘、网、回路与曲线之间形变。
 *
 * 全部坐标是 1920×1080 逻辑坐标；所有对象的主形状都重采样为同样多的点，
 * 因此可以直接逐点插值。这里不读帧号、不读挂钟、不使用随机源。
 */
import {clamp01, lerp} from 'm2v/style/components/kit';

export type Pt = {x: number; y: number};

export const W = 1920;
export const H = 1080;
export const CX = 960;
export const CY = 520;
export const TAU = Math.PI * 2;
export const SAMPLE = 240;

export function toPath(points: readonly Pt[], closed = false): string {
  if (!points.length) return '';
  const body = points.map((point, index) =>
    `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
  return closed ? `${body} Z` : body;
}

/** 两点之间的等距点列；包含端点。 */
export function linePoints(a: Pt, b: Pt, count = SAMPLE): Pt[] {
  return Array.from({length: count}, (_, index) => {
    const t = count <= 1 ? 0 : index / (count - 1);
    return {x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t)};
  });
}

export function dotPoints(count = SAMPLE): Pt[] {
  return Array.from({length: count}, () => ({x: CX, y: CY}));
}

/** 对数螺旋：每转一圈半径翻倍；从中心向外。 */
export function spiralPoints(count = SAMPLE, turns = 6, r0 = 8, rMax = 380): Pt[] {
  return Array.from({length: count}, (_, index) => {
    const t = count <= 1 ? 0 : index / (count - 1);
    const angle = -Math.PI / 2 + t * turns * TAU;
    const radius = Math.min(rMax, r0 * Math.pow(2, t * turns));
    return {x: CX + Math.cos(angle) * radius, y: CY + Math.sin(angle) * radius};
  });
}

/** 圆心在 (CX, CY) 的圆；首尾重合，便于和方框互形。 */
export function circlePoints(radius = 360, count = SAMPLE): Pt[] {
  return Array.from({length: count}, (_, index) => {
    const t = count <= 1 ? 0 : index / (count - 1);
    const angle = -Math.PI / 2 + t * TAU;
    return {x: CX + Math.cos(angle) * radius, y: CY + Math.sin(angle) * radius};
  });
}

/** 方框周长；从左上角起顺时针，首尾重合。 */
export function squareBorder(size = 560, count = SAMPLE): Pt[] {
  const left = CX - size / 2;
  const top = CY - size / 2;
  const right = CX + size / 2;
  const bottom = CY + size / 2;
  const points: Pt[] = [];
  const sides = [
    {from: {x: left, y: top}, to: {x: right, y: top}},
    {from: {x: right, y: top}, to: {x: right, y: bottom}},
    {from: {x: right, y: bottom}, to: {x: left, y: bottom}},
    {from: {x: left, y: bottom}, to: {x: left, y: top}},
  ];
  const perSide = Math.max(2, Math.floor((count - 1) / 4));
  for (const side of sides) {
    for (let index = 0; index < perSide; index += 1) {
      const t = index / perSide;
      points.push({x: lerp(side.from.x, side.to.x, t), y: lerp(side.from.y, side.to.y, t)});
    }
  }
  points.push({x: left, y: top});
  while (points.length < count) points.push({x: left, y: top});
  return points.slice(0, count);
}

/** 棋盘 8×8 的交点，行优先；用于“棋盘变网”的节点起点。 */
export function boardPoints(size = 560): Pt[] {
  const left = CX - size / 2;
  const top = CY - size / 2;
  const step = size / 7;
  const points: Pt[] = [];
  for (let row = 0; row < 8; row += 1) {
    for (let col = 0; col < 8; col += 1) {
      points.push({x: left + col * step, y: top + row * step});
    }
  }
  return points;
}

/** 网环节点：固定 100 个槽位，前 n 个可见；最后一个槽位让圆闭合。 */
export function networkNode(index: number, radius = 360): Pt {
  const angle = -Math.PI / 2 + (index % 100) * (TAU / 100);
  return {x: CX + Math.cos(angle) * radius, y: CY + Math.sin(angle) * radius};
}

export function networkNodes(count: number, radius = 360): Pt[] {
  return Array.from({length: count}, (_, index) => networkNode(index, radius));
}

/** 逐点插值；两条点列必须等长。 */
export function morphPoints(from: readonly Pt[], to: readonly Pt[], progress: number): Pt[] {
  const t = clamp01(progress);
  const length = Math.min(from.length, to.length);
  return Array.from({length}, (_, index) => ({
    x: lerp(from[index].x, to[index].x, t),
    y: lerp(from[index].y, to[index].y, t),
  }));
}

/** 向外微弯的弦；避免所有弦在圆心糊成一块。 */
export function chordPath(a: Pt, b: Pt, bow = 0.1): string {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = mx - CX;
  const dy = my - CY;
  const cx = mx + dx * bow;
  const cy = my + dy * bow;
  return `M${a.x.toFixed(1)} ${a.y.toFixed(1)} Q${cx.toFixed(1)} ${cy.toFixed(1)} `
    + `${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
}

/** 10 个节点均布在一个小圆上；用于“前 10 个”的独立小结。 */
export function rosetteNodes(count = 10, radius = 110): Pt[] {
  return Array.from({length: count}, (_, index) => {
    const angle = -Math.PI / 2 + (index / count) * TAU;
    return {x: CX + Math.cos(angle) * radius, y: CY + Math.sin(angle) * radius};
  });
}

/** 小圆上 n 个节点的全部弦；与 100 节点网络的固定槽位无关。 */
export function rosettePath(count = 10, radius = 110, bow = 0.1): string {
  const nodes = rosetteNodes(count, radius);
  const parts: string[] = [];
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      parts.push(chordPath(nodes[i], nodes[j], bow));
    }
  }
  return parts.join(' ');
}

/** 当前 n 个节点的全部弦；缓存按 n 复用，避免每帧重算 4,950 条。 */
const chordCache = new Map<string, string>();

export function allChordsPath(count: number, radius = 360, bow = 0.1): string {
  const key = `${count}:${radius}:${bow.toFixed(3)}`;
  const cached = chordCache.get(key);
  if (cached) return cached;
  const nodes = networkNodes(count, radius);
  const parts: string[] = [];
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      parts.push(chordPath(nodes[i], nodes[j], bow));
    }
  }
  const value = parts.join(' ');
  chordCache.set(key, value);
  return value;
}

/** 最新节点发出的扇形。 */
export function fanPath(count: number, radius = 360, bow = 0.1): string {
  if (count < 2) return '';
  const nodes = networkNodes(count, radius);
  const newest = nodes[count - 1];
  return nodes.slice(0, count - 1)
    .map(node => chordPath(newest, node, bow)).join(' ');
}

/** 前 10 个节点内部的 45 条弦。 */
export function firstTenPath(radius = 360, bow = 0.1): string {
  const nodes = networkNodes(100, radius);
  const parts: string[] = [];
  for (let i = 0; i < 10; i += 1) {
    for (let j = i + 1; j < 10; j += 1) parts.push(chordPath(nodes[i], nodes[j], bow));
  }
  return parts.join(' ');
}

/** 后 10 个节点连前面 90 个（含内部 45 条），共 945 条。 */
export function lastTenPath(radius = 360, bow = 0.1): string {
  const nodes = networkNodes(100, radius);
  const parts: string[] = [];
  for (let i = 90; i < 100; i += 1) {
    for (let j = 0; j < i; j += 1) parts.push(chordPath(nodes[i], nodes[j], bow));
  }
  return parts.join(' ');
}

/** 回路：从圆心到每个节点的线。 */
export function loopThreads(count = 100, radius = 360): Array<[Pt, Pt]> {
  const nodes = networkNodes(count, radius);
  return nodes.slice(1).map(node => [{x: CX, y: CY}, node] as [Pt, Pt]);
}

/** 曲线：t∈[0,1]，kind 决定形状。 */
export type CurveKind = 'paper' | 'board' | 'network';

export function curveValue(kind: CurveKind, t: number): number {
  const value = clamp01(t);
  if (kind === 'network') return value * value;
  const total = kind === 'paper' ? 42 : 63;
  return (Math.pow(2, value * total) - 1) / (Math.pow(2, total) - 1);
}

export function curvePoints(kind: CurveKind, count = SAMPLE): Pt[] {
  const left = 480;
  const right = 1440;
  const base = 760;
  const height = 520;
  return Array.from({length: count}, (_, index) => {
    const t = count <= 1 ? 0 : index / (count - 1);
    return {x: lerp(left, right, t), y: base - height * curveValue(kind, t)};
  });
}

/** 纸堆顶部：线性高度轴；月球线位置可指定，默认 384,400 km 所在高度。 */
export function paperStackTop(fold: number, moonY = 220): {y: number; km: number} {
  const layers = Math.pow(2, fold);
  const km = layers * 0.1e-6;
  const moonKm = 384400;
  const baseY = 820;
  const y = baseY - (km / moonKm) * (baseY - moonY);
  return {y, km};
}

/** 纸的主线：纸堆顶端的一条短线。 */
export function paperLine(fold: number): Pt[] {
  const {y} = paperStackTop(fold);
  return linePoints({x: 900, y}, {x: 1020, y}, SAMPLE);
}

/** 棋盘格线：8 竖 + 8 横，各 40 个点；用于向弦形变。 */
export function boardGridLines(size = 560): Array<{from: Pt; to: Pt; points: Pt[]}> {
  const left = CX - size / 2;
  const top = CY - size / 2;
  const step = size / 7;
  const lines: Array<{from: Pt; to: Pt; points: Pt[]}> = [];
  for (let index = 0; index < 8; index += 1) {
    const x = left + index * step;
    lines.push({from: {x, y: top}, to: {x, y: top + size},
      points: linePoints({x, y: top}, {x, y: top + size}, 40)});
  }
  for (let index = 0; index < 8; index += 1) {
    const y = top + index * step;
    lines.push({from: {x: left, y}, to: {x: left + size, y},
      points: linePoints({x: left, y}, {x: left + size, y}, 40)});
  }
  return lines;
}

/** 棋盘格线形变后的目标弦：16 条跨圆的弦。 */
export function boardTargetChords(radius = 360): Pt[][] {
  const nodes = networkNodes(100, radius);
  const chords: Pt[][] = [];
  for (let index = 0; index < 8; index += 1) {
    chords.push(linePoints(nodes[index], nodes[99 - index], 40));
  }
  for (let index = 0; index < 8; index += 1) {
    chords.push(linePoints(nodes[25 + index], nodes[75 - index], 40));
  }
  return chords;
}

/** 10×10 的可数总体：100 个点，第一点可单独强调。 */
export function hundredDots(box = {x: 560, y: 220, width: 800, height: 560}): Pt[] {
  const points: Pt[] = [];
  for (let row = 0; row < 10; row += 1) {
    for (let col = 0; col < 10; col += 1) {
      points.push({
        x: box.x + (col + 0.5) * (box.width / 10),
        y: box.y + (row + 0.5) * (box.height / 10),
      });
    }
  }
  return points;
}

/** 0–1 窗口进度。 */
export function windowProgress(frame: number, start: number, end: number): number {
  return clamp01((frame - start) / Math.max(1, end - start));
}

/** 只在窗口内可见；两端各留少量可见度供量测。 */
export function windowOpacity(frame: number, start: number, end: number, fade = 10): number {
  const inPart = clamp01((frame - start) / fade);
  const outPart = clamp01((end - frame) / fade);
  return Math.min(inPart, outPart);
}
