/**
 * 量测代理：把本帧的绘制清单转成透明的 `data-m2v-role` 元素与状态探针。
 *
 * 为什么必须有它：检查点量测读的是 DOM 标记（`[data-m2v-role]`），
 * `window.__M2V_REVIEW_STATE__` 只产出独立的"可选状态探针"检查，**不会**
 * 消除"观测范围：未验证"；更糟的是，若该帧有活动文字计划而页面没有 DOM
 * 标记，文字状态会直接判失败，而人工证据只能替换未验证项、翻不了失败。
 *
 * 代理元素必须是透明的：它只提供几何与文字，不参与像素绘制，因此不会改变
 * 成片画面。位置与尺寸来自 `Painter` 记录的同一份布局数据。
 */
import React from 'react';
import type {Mark} from './frame';

export type ReviewState = {role: string; count: number; state?: string};

/** 按角色聚合的状态列表，写入 `window.__M2V_REVIEW_STATE__`。 */
export function reviewState(marks: Mark[]): ReviewState[] {
  const counts = new Map<string, ReviewState>();
  for (const mark of marks) {
    const existing = counts.get(mark.role);
    if (existing) {
      existing.count += 1;
      // 同一角色可能有多个状态；探针按「恰好一条记录」匹配，状态不一致时不猜。
      if (existing.state !== undefined && existing.state !== mark.state) existing.state = '';
    } else {
      counts.set(mark.role, {role: mark.role, count: 1, ...(mark.state ? {state: mark.state} : {})});
    }
  }
  return [...counts.values()];
}

/**
 * 把一帧的绘制清单渲染成透明代理元素。
 *
 * 元素带 `data-m2v-role` 与 `data-m2v-state`、与实际绘制一致的字号与文本；
 * 颜色写进 `color`，供量测核对。
 *
 * **文字必须用 `-webkit-text-fill-color: transparent` 隐藏，不能用
 * `opacity: 0` 或 `color: transparent`**：
 *
 * - `opacity: 0` 会让量测判定元素不可见，代理等于不存在；
 * - `color: transparent` 会让量测读到的颜色变成 transparent，颜色断言全部失败；
 * - 只有 text-fill-color 能同时满足「计算样式里的 color 仍是原值」与「屏幕上看不见」。
 *
 * 早些时候漏了这一条，代理文字与画布文字叠在一起，画面里每个字都出现重影。
 */
export function MeasureProxy({marks}: {marks: Mark[]}): React.ReactElement {
  return (
    <div aria-hidden style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      {marks.map((mark, index) => (
        <div
          key={`${mark.role}-${index}`}
          data-m2v-role={mark.role}
          data-m2v-state={mark.state}
          style={{
            position: 'absolute',
            left: mark.x,
            top: mark.y,
            width: Math.max(0, mark.width),
            height: Math.max(0, mark.height),
            fontSize: mark.fontSize,
            color: mark.color,
            background: 'transparent',
            // 只隐藏填充，不改计算样式里的 color。
            WebkitTextFillColor: 'transparent',
            whiteSpace: 'nowrap',
            overflow: 'visible',
          }}
        >
          {mark.text ?? ''}
        </div>
      ))}
    </div>
  );
}
