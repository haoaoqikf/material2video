/**
 * v4 运动层：每页一个标量；数字滚动、局部镜头、页面进出。
 *
 * 所有值都由帧号求值；没有全局粒子场，没有环境装饰。
 */
import {painter, motionCurve, type Easing} from 'm2v/code-scene';
import {LATIN, NUMERIC_STYLE, T, easeInOutSine, easeOutCubic} from 'm2v/style/components/kit';

const GOLD = T.colors.gold;

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export type TimelineKey = {
  start: number;
  end: number;
  from: number;
  to: number;
  easing?: Easing;
};

export type TimelineSample = {
  value: number;
  previous: number;
  previous2: number;
  speed: number;
  progress: number;
  active: boolean;
};

function valueAt(keys: readonly TimelineKey[], frame: number): number {
  let value = keys[0]?.from ?? 0;
  for (const key of keys) {
    if (frame < key.start) break;
    if (frame >= key.end) {
      value = key.to;
      continue;
    }
    const raw = (frame - key.start) / Math.max(1, key.end - key.start);
    const eased = (key.easing ?? motionCurve('easeOutCubic'))(clamp01(raw));
    return key.from + (key.to - key.from) * eased;
  }
  return value;
}

export function sampleTimeline(keys: readonly TimelineKey[], frame: number): TimelineSample {
  const value = valueAt(keys, frame);
  const previous = valueAt(keys, frame - 2);
  const previous2 = valueAt(keys, frame - 4);
  const speed = Math.abs(value - previous) / 2;
  let progress = 1;
  let active = false;
  for (const key of keys) {
    if (frame < key.start) break;
    if (frame < key.end) {
      progress = clamp01((frame - key.start) / Math.max(1, key.end - key.start));
      active = true;
      break;
    }
  }
  return {value, previous, previous2, speed, progress, active};
}

export function blurFor(speed: number, scale = 2.2): number {
  return Math.min(1.6, Math.max(0, speed) * scale);
}

export function breathe(frame: number, phase = 0, amplitude = 1.5): number {
  return Math.sin(frame / 45 + phase) * amplitude;
}

/** 旧页在边界后 14 帧内退净；前 8 帧降到约 0.09。 */
export function leavePage(boundary: number, frame: number, duration = 14): number {
  return 1 - easeOutCubic(clamp01((frame - boundary) / duration));
}

/** 新页在边界后 2 帧进入，14 帧到 1；与 leavePage 重叠但不留空档。 */
export function enterPage(boundary: number, frame: number, delay = 2, duration = 14): number {
  return easeInOutSine(clamp01((frame - boundary - delay) / duration));
}

/** 页面文字比几何更晚进、更早退。 */
export function textFade(frame: number, start: number, end: number, fade = 8): number {
  return Math.min(
    easeOutCubic(clamp01((frame - start) / fade)),
    1 - easeOutCubic(clamp01((frame - (end - fade)) / fade)),
  );
}

function formatValue(value: number, decimals: number): string {
  const fixed = value.toFixed(decimals);
  const [whole, fraction] = fixed.split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return fraction ? `${grouped}.${fraction}` : grouped;
}

export type RollingFigureProps = {
  value: number;
  previous: number;
  previous2: number;
  speed: number;
  x: number;
  y: number;
  size: number;
  color?: string;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  align?: 'left' | 'center' | 'right';
  opacity?: number;
};

/** 逐帧滚动数字：2 层方向残影 + 轻模糊；停稳后完全锐利。 */
export function RollingFigure({
  value, previous, previous2, speed, x, y, size, color = GOLD,
  decimals = 0, prefix = '', suffix, align = 'left', opacity = 1,
}: RollingFigureProps) {
  const blur = blurFor(speed);
  const ghost = Math.min(1, speed * 0.32);
  const translate = align === 'center' ? 'translate(-50%, -50%)'
    : align === 'right' ? 'translate(-100%, -50%)' : 'translate(0, -50%)';
  const base = {
    position: 'absolute' as const, left: x, top: y, transform: translate,
    fontFamily: LATIN, ...NUMERIC_STYLE, fontSize: size, lineHeight: 0.9,
    letterSpacing: '-0.035em', whiteSpace: 'nowrap' as const,
  };
  const render = (v: number, layerOpacity: number, dy: number, key: string) => (
    <span key={key} style={{
      position: 'absolute', left: 0, top: 0, opacity: layerOpacity,
      transform: `translateY(${dy}px)`,
      filter: blur > 0 ? `blur(${blur}px)` : undefined,
    }}>{prefix}{formatValue(v, decimals)}{suffix ?? ''}</span>
  );
  return (
    <div data-m2v-role="hero-number" style={{...base, color, opacity}}>
      <span style={{visibility: 'hidden'}}>{prefix}{formatValue(value, decimals)}{suffix ?? ''}</span>
      {ghost > 0.04 ? render(previous2, ghost * 0.16, -12, 'g2') : null}
      {ghost > 0.04 ? render(previous, ghost * 0.26, -6, 'g1') : null}
      <span style={{
        position: 'absolute', left: 0, top: 0,
        filter: blur > 0 ? `blur(${blur}px)` : undefined,
      }}>{prefix}{formatValue(value, decimals)}{suffix ?? ''}</span>
    </div>
  );
}

export type CameraKey = {at: number; scale: number; focusX: number; focusY: number};

/** 页面镜头：只给需要尺度/跟随的页；边界回到中性，避免交接物跳位。 */
export function pageCamera(keys: readonly CameraKey[], frame: number): {
  scale: number; focusX: number; focusY: number; transform: string;
} {
  const state = painter.cameraAt(keys, frame, motionCurve('easeInOutSine'));
  return {
    ...state,
    transform: `translate(${960 - state.focusX * state.scale}px, ${540 - state.focusY * state.scale}px) scale(${state.scale})`,
  };
}
