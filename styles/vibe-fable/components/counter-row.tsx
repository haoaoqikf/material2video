/**
 * 对照计数：左右各一组「标签 + 大数字」，用来并排放真实值与夸张值。
 * 真值用暖白，夸张值用红；颜色语义与 tokens 一致，不由调用方随意改。
 */
import {motionCurve, rollNumber, type Easing} from 'm2v/code-scene';
import {T, color} from './kit';

const LINEAR = motionCurve('linear');

export type CounterItem = {label: string; value: number | string; exaggerated?: boolean};

export type CounterRowProps = {
  /** 恰好两组：左真值、右夸张值。 */
  items: [CounterItem, CounterItem];
  frame?: number;
  startFrame?: number;
  durationFrames?: number;
  opacity?: number;
  easing?: Easing;
  y?: number;
  role?: string;
  state?: string;
};

function formatValue(value: number | string, progress: number, easing: Easing): string {
  if (typeof value === 'string') return value;
  return rollNumber({from: 0, to: value, progress, decimals: 0, easing}).text;
}

export default function CounterRow({
  items, frame, startFrame = 0, durationFrames = 0, opacity = 1, easing = LINEAR,
  y = T.layout.counter.y, role, state,
}: CounterRowProps) {
  const progress = durationFrames > 0 && frame !== undefined
    ? Math.min(1, Math.max(0, (frame - startFrame) / Math.max(1, durationFrames)))
    : 1;
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{
      position: 'absolute', left: 0, right: 0, top: y, height: T.layout.counter.height,
      display: 'flex', justifyContent: 'center', gap: 180, opacity, pointerEvents: 'none',
      fontFamily: T.type.fontStack,
    }}>
      {items.map((item, index) => (
        <div key={index} style={{textAlign: 'center', minWidth: 260}}>
          <div style={{fontSize: T.type.counterLabel, color: color('dim'), letterSpacing: '0.08em'}}>{item.label}</div>
          <div style={{
            fontSize: T.type.counterNumber, fontWeight: 700, lineHeight: 1.1,
            color: item.exaggerated ? color('red') : color('ink'), fontVariantNumeric: 'tabular-nums',
            textShadow: '0 3px 12px rgba(0,0,0,.35)',
          }}>{formatValue(item.value, progress, easing)}</div>
        </div>
      ))}
    </div>
  );
}
