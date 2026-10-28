/**
 * 引线标注：贴着画面里某个东西的小字，一条细线指过去。
 * 只用于识别对象或指出可见特征，不写解释性长句。
 */
import {useId} from 'react';
import {T, alpha, color} from './kit';

export type CalloutProps = {
  text: string;
  /** 被标注对象的位置（引线起点）与文字位置（引线终点）。 */
  at: {x: number; y: number};
  label: {x: number; y: number};
  align?: 'left' | 'right';
  color?: string;
  opacity?: number;
  role?: string;
  state?: string;
};

export default function Callout({
  text, at, label, align = label.x >= at.x ? 'left' : 'right', color: textColor = color('ink'),
  opacity = 1, role, state,
}: CalloutProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const accent = color('gold');
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{position: 'absolute', inset: 0, opacity, pointerEvents: 'none'}}>
      <svg width="100%" height="100%" style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <line x1={at.x} y1={at.y} x2={label.x} y2={label.y} stroke={alpha(accent, 0.9)} strokeWidth={2}/>
        <circle cx={at.x} cy={at.y} r={5} fill={accent}/>
      </svg>
      <div style={{
        position: 'absolute', left: label.x, top: label.y,
        transform: align === 'left' ? 'translate(0, -50%)' : 'translate(-100%, -50%)',
        marginLeft: align === 'left' ? 14 : -14,
        fontFamily: T.type.fontStack, fontSize: T.type.callout, color: textColor, whiteSpace: 'nowrap',
        textShadow: '0 2px 8px rgba(0,0,0,.4)',
      }}>{text}</div>
    </div>
  );
}
