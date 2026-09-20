/**
 * 数字幕：按帧递增显示数值，并带标签与说明。
 *
 * 逐行对应旧组件库 `assets/figures.js` 的 `updateNumber`（第 1743–1766 行），
 * 包括几个「看起来可以简化、但简化就会改画面」的细节：
 *
 * - 数字滚动吃的是**缓动过的进度**，入场位移吃的是**线性秒数**，
 *   同一个起点各取所需（弹簧需要线性时间，喂缓动过的进度会让它的自然周期失去意义）；
 * - 只有滚得动的数值才滚：`|value| < ROLL_MIN` 时直接给最终值。
 *   否则 350px 的强调色数字会先显示一个**不是最终值**的数再跳变——
 *   实测数字幕 `value: 1` 在第 15–23 帧显示「0」，而那一幕讲的正是一「只保留 1 个」；
 * - 非数字（或非有限数）一律原样显示，这一支与从前完全一致。
 */
import type { FC } from 'react';

import {
  EASE,
  ROLL_MIN,
  beat,
  enterStyle,
  plainText,
  sinceBeat,
  useFigure,
  useFit,
} from '@/runtime/figures';

export const NumberFigure: FC = () => {
  const fig = useFigure();
  const { localFrame } = fig.state;
  const data = fig.data;

  const raw = data['value'];
  const progress = fig.api.progress(
    localFrame,
    beat(fig, 0.1),
    beat(fig, 0.36),
    EASE.out,
  );
  const rise = sinceBeat(fig, 0.1);

  const rollable =
    typeof raw === 'number' && Number.isFinite(raw) && Math.abs(raw) >= ROLL_MIN;
  const valueText = rollable
    ? String(Math.round(raw * progress))
    : raw === null || raw === undefined
      ? ''
      : String(raw);

  const value = useFit({ level: 'numeral', text: valueText });
  const labelText = plainText(data['label']);
  const label = useFit({ level: 'title', text: labelText });
  const captionText = plainText(data['caption']);
  const caption = useFit({ level: 'body', text: captionText });

  return (
    <>
      <div
        className="fig-number"
        data-el="value"
        data-a2v-fit="numeral"
        ref={value.ref}
        style={{ ...enterStyle(fig, rise, { distance: 42, scale: 0.92 }), ...value.style }}
      >
        {valueText}
      </div>
      <div
        className="fig-number-label"
        data-el="label"
        data-a2v-fit="title"
        ref={label.ref}
        style={{ ...enterStyle(fig, sinceBeat(fig, 0.22)), ...label.style }}
      >
        {labelText}
      </div>
      <p
        className="fig-number-caption"
        data-el="caption"
        data-a2v-fit="body"
        ref={caption.ref}
        style={{ ...enterStyle(fig, sinceBeat(fig, 0.38)), ...caption.style }}
      >
        {captionText}
      </p>
    </>
  );
};
