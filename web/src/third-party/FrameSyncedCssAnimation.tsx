import type { CSSProperties, PropsWithChildren } from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';

export interface FrameSyncedCssAnimationProps extends PropsWithChildren {
  className?: string;
  /** 相对第 0 帧的时间偏移，单位秒。 */
  offsetSeconds?: number;
}

export function cssAnimationTime(frame: number, fps: number, offsetSeconds = 0): number {
  if (!Number.isFinite(frame) || !Number.isFinite(fps) || fps <= 0) {
    throw new Error(`CSS 动画帧同步参数非法：frame=${frame}, fps=${fps}`);
  }
  return Math.max(0, frame / fps + offsetSeconds);
}

/**
 * 把任意 CSS keyframes 子树变成帧号的纯函数。
 *
 * CSS 仍负责插值，但不会自行播放：样式层把整棵子树设为 paused，并用负 delay
 * 把时间轴定位到当前帧。因此随机访问第 N 帧与从第 0 帧播放到 N 的结果一致。
 */
export const FrameSyncedCssAnimation: React.FC<FrameSyncedCssAnimationProps> = ({
  children,
  className,
  offsetSeconds = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = cssAnimationTime(frame, fps, offsetSeconds);
  return (
    <div
      className={className}
      data-a2v-css-sync=""
      data-a2v-css-time={time.toFixed(6)}
      style={{ '--a2v-css-time': time } as CSSProperties}
    >
      {children}
    </div>
  );
};
