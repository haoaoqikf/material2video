/**
 * 引线标注：贴着画面里某个东西的小字，一条细线指过去。
 * 只用于识别对象或指出可见特征，不写解释性长句。
 *
 * 引线生长交给共享 Callout/@remotion/paths；本文件只保留 vibe-fable 的
 * 颜色、字号与文字阴影。
 */
import {Callout as SharedCallout} from 'm2v/code-scene';
import {T, alpha, color} from './kit';

export type CalloutProps = {
  text: string;
  /** 被标注对象的位置（引线起点）与文字位置（引线终点）。 */
  at: {x: number; y: number};
  label: {x: number; y: number};
  align?: 'left' | 'right';
  color?: string;
  opacity?: number;
  progress?: number;
  role?: string;
  state?: string;
};

export default function Callout({
  text, at, label, align = label.x >= at.x ? 'left' : 'right', color: textColor = color('ink'),
  opacity = 1, progress = 1, role, state,
}: CalloutProps) {
  return (
    <SharedCallout
      text={text}
      at={at}
      label={label}
      align={align}
      color={alpha(color('gold'), 0.9)}
      textColor={textColor}
      opacity={opacity}
      progress={progress}
      fontSize={T.type.callout}
      fontFamily={T.type.fontStack}
      textShadow="0 2px 8px rgba(0,0,0,.4)"
      role={role}
      state={state}
    />
  );
}
