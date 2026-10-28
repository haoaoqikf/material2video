/**
 * 相机求值：确定性、端点精度与对数缩放。
 *
 * 相机只返回值，不施加变换；这里验证的是「同一输入永远给出同一组数」，
 * 而这正是逐帧录制、跳帧采样与重录能够一致的前提。
 */
import {describe, expect, it} from 'vitest';
import {cameraAt, project, type CameraKey} from './camera';

const KEYS: CameraKey[] = [
  {at: 0, scale: 1, focusX: 0, focusY: 0},
  {at: 10, scale: 4, focusX: 100, focusY: -50},
  {at: 20, scale: 2, focusX: 100, focusY: -50},
];

describe('相机求值', () => {
  it('同一输入两次求值完全相等', () => {
    for (const progress of [0, 2.5, 7.125, 10, 13.75, 20, 21]) {
      expect(cameraAt(KEYS, progress)).toEqual(cameraAt(KEYS, progress));
    }
  });

  it('进度 0 与末关键帧精确返回端点值', () => {
    expect(cameraAt(KEYS, 0)).toEqual({scale: 1, focusX: 0, focusY: 0});
    expect(cameraAt(KEYS, 20)).toEqual({scale: 2, focusX: 100, focusY: -50});
  });

  it('超出范围的进度夹到端点，不外推', () => {
    expect(cameraAt(KEYS, -5)).toEqual({scale: 1, focusX: 0, focusY: 0});
    expect(cameraAt(KEYS, 999)).toEqual({scale: 2, focusX: 100, focusY: -50});
  });

  it('缩放按对数空间插值：1 与 4 的中点返回 2 而不是 2.5', () => {
    const state = cameraAt([{at: 0, scale: 1, focusX: 0, focusY: 0},
      {at: 1, scale: 4, focusX: 0, focusY: 0}], 0.5);
    expect(state.scale).toBeCloseTo(2, 10);
  });

  it('等距关键帧产生几何级数，而不是等差', () => {
    const keys: CameraKey[] = [0, 1, 2, 3].map(index => ({at: index, scale: 2 ** index, focusX: 0, focusY: 0}));
    const values = [0, 1, 2, 3].map(at => cameraAt(keys, at).scale);
    expect(values).toEqual([1, 2, 4, 8]);
    expect(cameraAt(keys, 0.5).scale).toBeCloseTo(Math.SQRT2, 10);
  });

  it('缩放不变时焦点与进度线性同步', () => {
    const state = cameraAt([{at: 0, scale: 3, focusX: 0, focusY: 0},
      {at: 1, scale: 3, focusX: 90, focusY: 40}], 0.25);
    expect(state.scale).toBeCloseTo(3, 12);
    expect(state.focusX).toBeCloseTo(22.5, 10);
    expect(state.focusY).toBeCloseTo(10, 10);
  });

  it('推近时焦点早于线性抵达目标', () => {
    const state = cameraAt([{at: 0, scale: 1, focusX: 0, focusY: 0},
      {at: 1, scale: 8, focusX: 100, focusY: 0}], 0.5);
    // 对数缩放的中点缩放到 √8≈2.83；按 1/scale 加权后焦点应超过线性的 50。
    expect(state.focusX).toBeGreaterThan(50);
    expect(state.focusX).toBeLessThan(100);
  });

  it('缓动曲线由调用方给出，缺省为恒等', () => {
    const linear = cameraAt([{at: 0, scale: 1, focusX: 0, focusY: 0},
      {at: 1, scale: 4, focusX: 0, focusY: 0}], 0.5);
    const eased = cameraAt([{at: 0, scale: 1, focusX: 0, focusY: 0},
      {at: 1, scale: 4, focusX: 0, focusY: 0}], 0.5, t => t * t);
    expect(linear.scale).toBeCloseTo(2, 10);
    expect(eased.scale).toBeCloseTo(4 ** 0.25, 10);
  });

  it('单个关键帧在任意进度返回同一状态', () => {
    const only: CameraKey[] = [{at: 5, scale: 2.5, focusX: 7, focusY: 8}];
    expect(cameraAt(only, 0)).toEqual({scale: 2.5, focusX: 7, focusY: 8});
    expect(cameraAt(only, 500)).toEqual({scale: 2.5, focusX: 7, focusY: 8});
  });

  it('空表、非法缩放与乱序关键帧明确报错', () => {
    expect(() => cameraAt([], 0)).toThrow(RangeError);
    expect(() => cameraAt([{at: 0, scale: 0, focusX: 0, focusY: 0}], 0)).toThrow(RangeError);
    expect(() => cameraAt([{at: 0, scale: Number.NaN, focusX: 0, focusY: 0}], 0)).toThrow(RangeError);
    expect(() => cameraAt([{at: 2, scale: 1, focusX: 0, focusY: 0},
      {at: 1, scale: 1, focusX: 0, focusY: 0}], 1)).toThrow(RangeError);
    expect(() => cameraAt([{at: 0, scale: 1, focusX: Number.POSITIVE_INFINITY, focusY: 0}], 0))
      .toThrow(RangeError);
  });
});

describe('世界坐标换算', () => {
  it('焦点落在画面中心，缩放决定其余点距离', () => {
    const state = {scale: 2, focusX: 30, focusY: 40};
    expect(project(state, [30, 40], 960, 540)).toEqual([960, 540]);
    expect(project(state, [40, 30], 960, 540)).toEqual([980, 520]);
  });

  it('是纯函数，同参数两次结果一致', () => {
    const state = {scale: 1.5, focusX: -12, focusY: 6};
    expect(project(state, [3, 4], 0, 0)).toEqual(project(state, [3, 4], 0, 0));
  });
});
