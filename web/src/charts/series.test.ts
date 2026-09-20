/**
 * 图表数据侧纯函数的逐值断言（任务 7.1 / 7.2 的可机检部分）。
 *
 * 「同一帧求值两次画面一致」与「图表内容随帧号变化」在这里被钉成两条
 * 不需要浏览器的性质：切片与 option 构造都是纯函数——同样输入两次调用
 * 结果逐值相等（确定性），换输入必有字段不同（随帧变化）。
 * 真画面的端到端判定由 `tests/test_web_charts.py` 在契约页上跑
 * （PSNR 判据与整条管线共用）。
 */

import { describe, expect, it } from 'vitest';

import {
  barSlice,
  formatValue,
  lineSlice,
  parseChartPoints,
  parseChartType,
  REVEAL_TIMING,
  revealProgresses,
  valueExtent,
} from '@/charts/series';

const POINTS = [
  { label: '四月', value: 12 },
  { label: '五月', value: 30 },
  { label: '六月', value: 18 },
  { label: '七月', value: 44 },
];

function stateAt(frame: number, duration = 180) {
  return { localFrame: frame, sceneDurationFrames: duration, motion: 'normal' } as const;
}

describe('parseChartType / parseChartPoints：分镜数据进来，缺了就报错', () => {
  it('缺省是柱状；bar/line/pie 之外直接报错', () => {
    expect(parseChartType(undefined)).toBe('bar');
    expect(parseChartType('')).toBe('bar');
    expect(parseChartType('pie')).toBe('pie');
    expect(() => parseChartType('area')).toThrow(/bar \/ line \/ pie/);
  });

  it('values 缺失或为空直接报错，不画空白', () => {
    expect(() => parseChartPoints(undefined)).toThrow(/values/);
    expect(() => parseChartPoints([])).toThrow(/values/);
  });

  it('条目缺标签、缺数值、数值非法都要能定位到下标', () => {
    expect(() => parseChartPoints([{ label: '四月', value: 1 }, { value: 2 }])).toThrow(
      /values\[1\]\.label/,
    );
    expect(() => parseChartPoints([{ label: '四月' }])).toThrow(/values\[0\]\.value/);
    expect(() => parseChartPoints([{ label: '四月', value: Number.NaN }])).toThrow(
      /values\[0\]\.value/,
    );
    expect(() => parseChartPoints(['四月'])).toThrow(/values\[0\]/);
  });

  it('合法序列按原样读出（标签去首尾空白），组件里没有第二份数据', () => {
    expect(parseChartPoints([{ label: ' 四月 ', value: 12 }])).toEqual([
      { label: '四月', value: 12 },
    ]);
  });
});

describe('revealProgresses：显影节奏只由帧号推出', () => {
  it('第 0 帧全部未显影，收尾帧全部显影完成', () => {
    expect(revealProgresses(stateAt(0), POINTS.length)).toEqual([0, 0, 0, 0]);
    const end = revealProgresses(stateAt(179), POINTS.length);
    expect(end.every((value) => value === 1)).toBe(true);
  });

  it('按下标错开：同一个帧上，越靠后的点进度越不领先', () => {
    const reveals = revealProgresses(stateAt(24), POINTS.length);
    for (let index = 1; index < reveals.length; index += 1) {
      expect(reveals[index]!).toBeLessThanOrEqual(reveals[index - 1]!);
    }
    // 错开量就是配方表里的 STAGGER_FRAMES：中段的点之间恰好差这些帧
    // （浮点上同一进度可能差 1 ulp，用近似相等钉住这个关系）
    const earlier = revealProgresses(stateAt(24 - REVEAL_TIMING.STAGGER_FRAMES), POINTS.length);
    expect(reveals[1]).toBeCloseTo(earlier[0]!, 12);
  });

  it('随机访问与顺序播放一致：先跳后回，结果不变', () => {
    const forward = revealProgresses(stateAt(33), POINTS.length);
    revealProgresses(stateAt(170), POINTS.length);
    expect(revealProgresses(stateAt(33), POINTS.length)).toEqual(forward);
  });
});

describe('切片：柱 / 折 / 饼', () => {
  it('柱状：满进度等于原值，半进度按比例收缩，进度为 0 时为 0', () => {
    expect(barSlice(POINTS, [1, 1, 1, 1])).toEqual([12, 30, 18, 44]);
    expect(barSlice(POINTS, [1, 0.5, 0, 1])).toEqual([12, 15, 0, 44]);
  });

  it('折线：线头落在两档之间，沿段推进而不是逐段跳出', () => {
    const slice = lineSlice(POINTS, [1, 1, 0.5, 0]);
    // 前两个点到位；第三个点以线头出现：x 在 1 与 2 之间，y 在 30 与 18 之间
    expect(slice.map((item) => item.x)).toEqual([0, 1, 1.5]);
    expect(slice.map((item) => item.y)).toEqual([12, 30, 24]);
    expect(slice.map((item) => item.tip)).toEqual([false, false, true]);
  });

  it('折线：第一个点从横轴上长出来（没有前驱可沿段推进）', () => {
    const slice = lineSlice(POINTS, [0.5, 0, 0, 0]);
    expect(slice).toEqual([{ x: 0, y: 6, tip: true }]);
  });

  it('同一帧两次切片逐值相等（确定性）', () => {
    expect(lineSlice(POINTS, revealProgresses(stateAt(40), POINTS.length))).toEqual(
      lineSlice(POINTS, revealProgresses(stateAt(40), POINTS.length)),
    );
    expect(barSlice(POINTS, revealProgresses(stateAt(40), POINTS.length))).toEqual(
      barSlice(POINTS, revealProgresses(stateAt(40), POINTS.length)),
    );
  });
});

describe('valueExtent：轴的范围由完整数据决定，与帧号无关', () => {
  it('上限给最大值留 8% 头部空间，下限从 0 起算', () => {
    expect(valueExtent(POINTS)).toEqual({ min: 0, max: 44 * 1.08 });
  });

  it('全 0 的序列也有轴；负值把下限压到负向极值', () => {
    expect(valueExtent([{ label: 'a', value: 0 }]).max).toBeGreaterThan(0);
    const extent = valueExtent([
      { label: 'a', value: -8 },
      { label: 'b', value: -2 },
    ]);
    expect(extent.min).toBe(-8);
    expect(extent.max).toBe(0);
  });
});

describe('formatValue：数值列显示的是最终值', () => {
  it('千分位、两位小数封顶', () => {
    expect(formatValue(1234.5)).toBe('1,235');
    expect(formatValue(12.345)).toBe('12.35');
    expect(formatValue(0)).toBe('0');
  });
});
