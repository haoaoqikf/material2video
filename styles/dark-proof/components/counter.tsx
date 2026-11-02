/**
 * 计数器：在 `from → to` 之间按显式进度滚动，进度由调用方用帧号求出。
 *
 * 数字本身不携带含义；是否用金色表示“被强调的结果”由调用方按语义决定。
 * 组件不读取挂钟，也不包办数字出现或消失的时刻。
 */
import HeroNumber from './hero-number';
import {clamp01, easeInOutSine, T} from './kit';

export type CounterProps = {
  from: number;
  to: number;
  /** 0–1 进度；调用方用 `frameProgress` 计算。 */
  progress: number;
  decimals?: number;
  x: number;
  y: number;
  size?: number;
  color?: string;
  opacity?: number;
  prefix?: string;
  suffix?: string;
  align?: 'center' | 'left' | 'right';
};

export default function Counter({
  from, to, progress, decimals = 0, x, y, size = T.type.hero, color = T.colors.gold,
  opacity = 1, prefix = '', suffix, align = 'center',
}: CounterProps) {
  const eased = easeInOutSine(clamp01(progress));
  const value = from + (to - from) * eased;
  return (
    <HeroNumber
      value={`${prefix}${value.toFixed(decimals)}`}
      suffix={suffix}
      x={x}
      y={y}
      size={size}
      color={color}
      opacity={opacity}
      align={align}
    />
  );
}
