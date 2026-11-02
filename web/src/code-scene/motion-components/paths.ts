/** `@remotion/paths` 的薄封装：只用于 SVG path，不用于 Canvas 点列。 */
import {
  centerPath, cutPath, evolvePath, getBoundingBox, getInstructionIndexAtLength, getLength,
  getPointAtLength, getSubpaths, getTangentAtLength, interpolatePath, normalizePath, reversePath,
  scalePath, translatePath, warpPath,
} from '@remotion/paths';
import {clampProgress} from '../primitives';

export type PathPoint = {x: number; y: number};
export type PathBox = {x: number; y: number; width: number; height: number};
export type PathWarp = (point: PathPoint) => PathPoint;

export function pathDrawProps(
  d: string, progress: number,
): {strokeDasharray: string; strokeDashoffset: number} {
  if (!d) return {strokeDasharray: '0 1', strokeDashoffset: 0};
  return evolvePath(clampProgress(progress), d);
}

export function pathLength(d: string): number {
  return d ? getLength(d) : 0;
}

export function pathPointAtLength(d: string, length: number): PathPoint | null {
  return d ? getPointAtLength(d, Math.max(0, length)) : null;
}

export function pathTangentAtLength(d: string, length: number): PathPoint | null {
  return d ? getTangentAtLength(d, Math.max(0, length)) : null;
}

export function pathCut(d: string, length: number): string {
  if (!d) return '';
  return cutPath(d, Math.min(pathLength(d), Math.max(0, length)));
}

/** 两条路径的逐点插值；不做拓扑匹配，复杂轮廓需自行保证对应关系。 */
export function pathMorphAt(progress: number, from: string, to: string): string {
  if (!from) return to;
  if (!to) return from;
  return interpolatePath(clampProgress(progress), from, to);
}

/** 把路径上每个点交给纯函数变换，用于波化、扭曲与透视近似。 */
export function pathWarped(d: string, warp: PathWarp): string {
  return d ? warpPath(d, warp) : '';
}

export function pathBox(d: string): PathBox | null {
  if (!d) return null;
  const box = getBoundingBox(d);
  return {x: box.x1, y: box.y1, width: box.width, height: box.height};
}

export function pathNormalized(d: string): string {
  return d ? normalizePath(d) : '';
}

export function pathReversed(d: string): string {
  return d ? reversePath(d) : '';
}

export function pathScaled(d: string, scaleX: number, scaleY = scaleX): string {
  return d ? scalePath(d, scaleX, scaleY) : '';
}

export function pathTranslated(d: string, x: number, y: number): string {
  return d ? translatePath(d, x, y) : '';
}

export function pathCentered(d: string, target?: PathPoint): string {
  return d ? centerPath(d, target) : '';
}

export function pathSubpaths(d: string): string[] {
  return d ? getSubpaths(d) : [];
}

export function pathInstructionAtLength(
  d: string, length: number,
): {index: number; lengthIntoInstruction: number} | null {
  if (!d) return null;
  return getInstructionIndexAtLength(d, Math.max(0, length));
}
