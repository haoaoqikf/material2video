import type { CSSProperties } from 'react';
import type { Scene } from '@/schema/storyboard';

/** 场景级镜头运动的纯函数实现；未声明 camera 时返回空样式，保持旧作品逐帧不变。 */
export function cameraStyle(scene: Scene, frame: number): CSSProperties {
  const camera = scene.camera;
  if (!camera || camera.movement === 'static' || scene.durationInFrames <= 1) return {};
  const progress = Math.min(1, Math.max(0, frame / (scene.durationInFrames - 1)));
  const eased = 1 - (1 - progress) ** 3;
  const scale = camera.movement === 'push-in' ? 1 + eased * 0.06 : camera.movement === 'pull-out' ? 1.06 - eased * 0.06 : 1;
  const offset = camera.movement === 'pan-left' ? -eased * 28 : camera.movement === 'pan-right' ? eased * 28 : 0;
  const orbit = camera.movement === 'orbit' ? eased * 1.5 : 0;
  return {
    transform: `translateX(${offset}px) scale(${scale}) rotate(${orbit}deg)`,
    perspective: camera.depth === 'layered' ? '1200px' : undefined,
    transformOrigin: camera.composition === 'left' ? '30% 50%' : camera.composition === 'right' ? '70% 50%' : '50% 50%',
  };
}
