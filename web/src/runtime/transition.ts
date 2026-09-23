import type { CSSProperties } from 'react';
import type { Scene } from '@/schema/storyboard';
import { stylePackDefinition } from '@/registry';

/** 场景转场的帧驱动样式；它只作用于当前幕的根，不使用 CSS transition。 */
export function transitionStyle(scene: Scene, frame: number, stylePack?: string): CSSProperties {
  const transition = scene.transition;
  if (!transition || scene.durationInFrames <= 1) return {};
  const span = Math.min(stylePackDefinition(stylePack).transitionSpan, Math.max(1, Math.floor(scene.durationInFrames / 5)));
  const progress = Math.min(1, Math.max(0, frame / span));
  const eased = 1 - (1 - progress) ** 3;
  if (transition.kind === 'dissolve') return { opacity: eased };
  if (transition.kind === 'transform') return { opacity: eased, transform: `scale(${0.96 + eased * 0.04})` };
  if (transition.kind === 'break') return { opacity: eased, transform: `translateY(${(1 - eased) * 24}px)` };
  return {};
}
