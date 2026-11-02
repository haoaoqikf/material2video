/**
 * 计数器：在 `from → to` 之间按显式进度滚动，可选带 2–3 层残影。
 *
 * 数字本身不携带含义；是否用金色表示“被强调的结果”由调用方按语义决定。
 * 残影只用于表现数字滚动的动态模糊，不读取挂钟，也不累积上一帧状态。
 */
import {rollNumber, type Easing} from 'm2v/code-scene';
import HeroNumber from './hero-number';
import {clamp01, easeInOutSine, T} from './kit';

export type CounterGhosts = {
  count?: number;
  /** 每层相对主数字滞后的进度。 */
  step?: number;
  /** 每层相对主数字的纵向偏移。 */
  offsetY?: number;
  /** 最靠近主数字的残影不透明度。 */
  opacity?: number;
};

export type CounterProps = {
  from: number;
  to: number;
  /** 0–1 进度；调用方用 `frameProgress` 计算。 */
  progress: number;
  decimals?: number;
  /** 缓动可由调用方覆盖；默认保持原有的 easeInOutSine。 */
  easing?: Easing;
  x: number;
  y: number;
  size?: number;
  color?: string;
  opacity?: number;
  prefix?: string;
  suffix?: string;
  align?: 'center' | 'left' | 'right';
  ghosts?: CounterGhosts;
};

export default function Counter({
  from, to, progress, decimals = 0, easing = easeInOutSine, x, y, size = T.type.hero,
  color = T.colors.gold, opacity = 1, prefix = '', suffix, align = 'center', ghosts,
}: CounterProps) {
  const count = Math.max(0, Math.floor(ghosts?.count ?? 0));
  const step = Math.max(0, ghosts?.step ?? 0.08);
  const offsetY = ghosts?.offsetY ?? 10;
  const ghostOpacity = ghosts?.opacity ?? 0.2;
  const layer = (value: number, layerOpacity: number, dy: number, index: number) => {
    const {text} = rollNumber({from, to, progress: clamp01(value), decimals, easing});
    return (
      <HeroNumber
        key={index}
        value={`${prefix}${text}`}
        suffix={suffix}
        x={x}
        y={y + dy}
        size={size}
        color={color}
        opacity={layerOpacity}
        align={align}
      />
    );
  };
  const ghostLayers = Array.from({length: count}, (_, index) => {
    const delayed = clamp01(progress - (index + 1) * step);
    const fade = ghostOpacity * (1 - index / Math.max(1, count));
    return layer(delayed, fade, (index + 1) * offsetY, index);
  });
  return (
    <>
      {ghostLayers}
      {layer(progress, opacity, 0, count + 1)}
    </>
  );
}
