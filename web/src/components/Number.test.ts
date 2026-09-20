/**
 * 数值计数组件的帧级断言（任务 7.3）。
 *
 * `ROLL_MIN` 门槛挡的是这一类缺陷：幕在讲「只保留 1 个」，画面却先清楚地
 * 显示一秒「0」再跳成「1」——既是硬阶跃，也在断言错误的信息。
 * 这里把那次实测钉成逐帧机检：对 `value: 1` 走完整幕的每一帧，
 * 任何一个帧显示「0」都直接失败，不再依赖有人在成片里看见它。
 *
 * 只测纯函数（与其它组件测试同一约定）：不引 jsdom、不渲染组件。
 * 帧号 → 缓动进度的换算用 `runtime/motion` 的同一批原语按定义重写一遍，
 * 期望值是手算的（进度为 0 时给最终值，门槛之上才出现滚动序列）。
 */

import { describe, expect, it } from 'vitest';

import { rollValueText } from '@/components/Number';
import { ROLL_MIN } from '@/runtime/figures';
import { motionBeat, progress, type MotionState } from '@/runtime/motion';

const DURATION = 180;

/** 与 NumberFigure 相同的换算：幕内比例点 0.1 → 0.36，outQuint 缓动。 */
function frameText(raw: unknown, frame: number, duration = DURATION): string {
  const state: MotionState = { localFrame: frame, sceneDurationFrames: duration, motion: 'normal' };
  const eased = progress(frame, motionBeat(state, 0.1), motionBeat(state, 0.36), 'outQuint');
  return rollValueText(raw, eased);
}

describe('rollValueText：ROLL_MIN 步门槛', () => {
  it(`value: 1 的任何一帧都不显示「0」——门槛之内直接给最终值`, () => {
    for (let frame = 0; frame < DURATION; frame += 1) {
      expect(frameText(1, frame)).toBe('1');
    }
  });

  it('门槛之内的小数与负数同样不滚：9.9 / -5 每一帧都是最终值', () => {
    for (let frame = 0; frame < DURATION; frame += 1) {
      expect(frameText(9.9, frame)).toBe('9.9');
      expect(frameText(-5, frame)).toBe('-5');
    }
  });

  it(`边界恰好落在门槛上：|value| = ${ROLL_MIN} 会滚，${ROLL_MIN - 0.1} 不滚`, () => {
    expect(frameText(ROLL_MIN - 0.1, 0)).toBe(String(ROLL_MIN - 0.1));
    // 会滚的数值在进度为 0 时显示 0——那是滚动的起点，不是错误信息：
    // 从 0 到最终值之间有足够的步数，观众读到的是「在滚」
    expect(frameText(ROLL_MIN, 0)).toBe('0');
    expect(frameText(ROLL_MIN, DURATION - 1)).toBe(String(ROLL_MIN));
  });

  it('滚得动的数值单调不减，最后一帧等于最终值', () => {
    let previous = 0;
    for (let frame = 0; frame < DURATION; frame += 1) {
      const text = frameText(240, frame);
      const value = Number(text);
      expect(Number.isFinite(value)).toBe(true);
      expect(value).toBeGreaterThanOrEqual(previous);
      previous = value;
    }
    expect(previous).toBe(240);
  });

  it('非数字原样显示、缺省给空串：这两个分支与从前完全一致', () => {
    expect(frameText('42%', 30)).toBe('42%');
    expect(frameText(null, 30)).toBe('');
    expect(frameText(undefined, 30)).toBe('');
    expect(frameText(Number.NaN, 30)).toBe('NaN');
  });

  it('同一帧重复求值与求值顺序无关：随帧推进后回到任意帧，结果一致', () => {
    const forward = frameText(240, 90);
    // 先跳到很靠后的帧，再回到 90：纯函数不允许有「上一帧的残留」
    expect(frameText(240, DURATION - 1)).toBe('240');
    expect(frameText(240, 90)).toBe(forward);
  });
});
