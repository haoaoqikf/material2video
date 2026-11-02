/** `@remotion/paths` 的薄封装：只用于 SVG path，不用于 Canvas 点列。 */
import {cutPath, evolvePath, getLength, getPointAtLength, getTangentAtLength} from '@remotion/paths';
import {clampProgress} from '../primitives';

export type PathPoint = {x: number; y: number};

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
