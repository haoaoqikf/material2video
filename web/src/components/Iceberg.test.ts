/**
 * 冰山幕的纯计算与「填充层级关系」对照。
 *
 * 三件事在这里被机检，而不是只写在注释里：
 *
 * 1. **分区手算**：水面之上的尖端、水面之下的主体，各自落在哪一侧、有多深、
 *    面积多大——用可以直接手算的数（½ × 底 × 高）对一遍；
 * 2. **同输入同输出**：帧号是唯一输入，任意帧求值两次结果逐字段相同；
 * 3. **填充与层级**：水体、水上尖端、水下主体三档填充不许塌成一个令牌，
 *    并且绘制顺序（= DOM 顺序）必须是「水体 → 水面线 → 尖端 → 主体 → 光带」。
 *    这一条同时拿**冻结的旧 markup**（`assets/figures.js` 的 `MARKUP_ICEBERG`）
 *    与本组件的源码对照：层级不是靠人记得两边一致，而是两边一起量。
 *
 * 不引入 jsdom / 测试库：这里量的是纯函数与源码里的顺序，不是渲染结果。
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { createFigureApi } from '@/runtime/figures';
import { motionBeat } from '@/runtime/motion';

import {
  BERG_CALLOUT_H,
  BERG_CALLOUT_LINK_LENGTHS,
  BERG_CALLOUT_SLOTS,
  BERG_CALLOUT_X,
  BERG_CALLOUT_Y,
  BERG_LAYER_FILL,
  BERG_MASS_POINTS,
  BERG_PAINT_ORDER,
  BERG_SPARK_COUNT,
  BERG_SPARK_Y_FROM,
  BERG_TIP_POINTS,
  BERG_VIEW_HEIGHT,
  BERG_WATERLINE_Y,
  BERG_WATER_HEIGHT,
  BERG_WATER_LINE_LENGTH,
  bergCalloutGeometry,
  bergCalloutLinkLength,
  bergCalloutStart,
  bergCallouts,
  bergFrame,
  bergLayerIndex,
  bergPolygonZone,
  bergSparkPose,
  bergZone,
  bergZoneDepth,
  cubicArcLength,
  normalizeBergItems,
  type BergMotionState,
  type BergPoint,
} from './Iceberg';

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, '..', '..');
const repoRoot = path.resolve(webRoot, '..');
const legacyAssets = path.join(repoRoot, '.agents', 'skills', 'article2video', 'assets');
const componentSource = readFileSync(path.join(here, 'Iceberg.tsx'), 'utf8');
/**
 * 只量**组件本体**里的顺序：文件头的注释里也写着这些 `data-el` 名字
 * （那是为了说明层级依据），从注释里量到的顺序没有意义。
 */
const jsxSource = componentSource.slice(componentSource.indexOf('export const IcebergFigure'));
const legacyFigures = readFileSync(path.join(legacyAssets, 'figures.js'), 'utf8');
const figuresCss = readFileSync(path.join(webRoot, 'src', 'styles', 'figures.css'), 'utf8');

/** 冻结的 `MARKUP_ICEBERG` 原文（旧 figures.js 第 1008–1042 行）。 */
function legacyIcebergMarkup(): string {
  const head = legacyFigures.indexOf('var MARKUP_ICEBERG = `');
  expect(head).toBeGreaterThan(-1);
  const start = legacyFigures.indexOf('`', head) + 1;
  const end = legacyFigures.indexOf('`', start);
  expect(end).toBeGreaterThan(start);
  return legacyFigures.slice(start, end);
}

/** 从样式表里取某个选择器的声明块，用来核对「哪一档填充」而不是猜。 */
function cssBlock(selector: string): string {
  const at = figuresCss.indexOf(selector);
  expect(at).toBeGreaterThan(-1);
  const open = figuresCss.indexOf('{', at);
  const close = figuresCss.indexOf('}', open);
  return figuresCss.slice(open + 1, close);
}

/** 独立参照：把三次贝塞尔折成很多小段求和，与自适应 Simpson 互校。 */
function polylineLength(
  p0: BergPoint,
  c1: BergPoint,
  c2: BergPoint,
  p3: BergPoint,
  segments: number,
): number {
  const at = (t: number): BergPoint => {
    const mt = 1 - t;
    return {
      x: mt ** 3 * p0.x + 3 * mt ** 2 * t * c1.x + 3 * mt * t ** 2 * c2.x + t ** 3 * p3.x,
      y: mt ** 3 * p0.y + 3 * mt ** 2 * t * c1.y + 3 * mt * t ** 2 * c2.y + t ** 3 * p3.y,
    };
  };
  let sum = 0;
  let previous = at(0);
  for (let index = 1; index <= segments; index += 1) {
    const next = at(index / segments);
    sum += Math.hypot(next.x - previous.x, next.y - previous.y);
    previous = next;
  }
  return sum;
}

/** 多边形面积（鞋带公式），用于「水上 / 水下各占多大」的手算对照。 */
function polygonArea(points: readonly BergPoint[]): number {
  let sum = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index]!;
    const next = points[(index + 1) % points.length]!;
    sum += current.x * next.y - next.x * current.y;
  }
  return Math.abs(sum) / 2;
}

const api = createFigureApi(30);
const beatAt = (state: BergMotionState) => (fraction: number) => motionBeat(state, fraction);
const frameState = (localFrame: number): BergMotionState => ({
  localFrame,
  sceneDurationFrames: 300,
  motion: 'normal',
});

describe('水面分区：手算对照', () => {
  it('一个点落在水面哪一侧，水面线本身单列一档', () => {
    expect(bergZone(64)).toBe('above');
    expect(bergZone(299.5)).toBe('above');
    // 水面线是一条零面积的线：压在它上面的顶点既不算水上、也不算水下
    expect(bergZone(BERG_WATERLINE_Y)).toBe('waterline');
    expect(bergZone(300.5)).toBe('below');
    expect(bergZone(692)).toBe('below');
  });

  it('水上尖端整体在水面之上，水下主体整体在水面之下', () => {
    // 旧 markup 第 1033 行：M215 64 L138 300 L296 300 Z
    expect(bergPolygonZone(BERG_TIP_POINTS)).toBe('above');
    // 旧 markup 第 1035 行：顶边两点压在水面线上，其余四点都在水面之下
    expect(bergPolygonZone(BERG_MASS_POINTS)).toBe('below');
    // 跨过水面线的形状必须被认出来（这张图里没有，但判据不能漏）
    expect(
      bergPolygonZone([
        { x: 0, y: 100 },
        { x: 100, y: 100 },
        { x: 100, y: 500 },
        { x: 0, y: 500 },
      ]),
    ).toBe('spanning');
  });

  it('尖端的底边与主体的顶边共线在水面线上', () => {
    const tipOnLine = BERG_TIP_POINTS.filter((point) => point.y === BERG_WATERLINE_Y);
    const massOnLine = BERG_MASS_POINTS.filter((point) => point.y === BERG_WATERLINE_Y);
    expect(tipOnLine).toEqual([
      { x: 138, y: 300 },
      { x: 296, y: 300 },
    ]);
    // 主体顶边与尖端底边是同一条线段，两块因此拼成一座完整的山
    expect(massOnLine).toEqual(tipOnLine);
    // 水体矩形从水面线起画、正好铺到画面底边（300 + 460 = 760）
    expect(BERG_WATERLINE_Y + BERG_WATER_HEIGHT).toBe(BERG_VIEW_HEIGHT);
  });

  it('两侧深度与面积：尖端 236 深 / 18644 面积，主体 392 深且明显更大', () => {
    expect(bergZoneDepth(BERG_TIP_POINTS, 'above')).toBe(236);
    expect(bergZoneDepth(BERG_MASS_POINTS, 'below')).toBe(392);

    // 手算：底边 296 − 138 = 158，高 300 − 64 = 236，三角形面积 = ½ × 158 × 236
    expect(polygonArea(BERG_TIP_POINTS)).toBe((158 * 236) / 2);
    expect(polygonArea(BERG_TIP_POINTS)).toBe(18644);

    // 这张图的语义：「看不见的主体」必须比「看得见的一角」大得多
    expect(polygonArea(BERG_MASS_POINTS)).toBeGreaterThan(polygonArea(BERG_TIP_POINTS) * 2);
  });
});

describe('标注几何与连线', () => {
  it('三个槽位的 y 与文字坐标照抄旧 BERG', () => {
    expect(BERG_CALLOUT_Y).toEqual([84, 316, 548]);
    expect(BERG_CALLOUT_X).toBe(452);
    expect(BERG_CALLOUT_H).toBe(132);

    const first = bergCalloutGeometry(0);
    expect(first.slot).toBe(0);
    expect(first.y).toBe(84);
    expect(first.target).toEqual({ x: 300, y: 172 });
    expect(first.labelX).toBe(484);
    expect(first.labelY).toBe(134);
    expect(first.descY).toBe(180);
  });

  it('连线的 d 与旧实现的字符串拼法逐字符相同', () => {
    // 旧第 889–894 行：M452 {y + 66} C 408 {y + 66}, {target.x + 70} {target.y}, {target.x} {target.y}
    expect(bergCalloutGeometry(0).linkD).toBe('M452 150 C 408 150, 370 172, 300 172');
    expect(bergCalloutGeometry(1).linkD).toBe('M452 382 C 408 382, 370 384, 300 384');
    expect(bergCalloutGeometry(2).linkD).toBe('M452 614 C 408 614, 414 566, 344 566');
  });

  it('弧长用两种数值方法互校', () => {
    // 第 0 条连线：M452 150 C 408 150, 370 172, 300 172
    const approximated = cubicArcLength(
      { x: 452, y: 150 },
      { x: 408, y: 150 },
      { x: 370, y: 172 },
      { x: 300, y: 172 },
    );
    const reference = polylineLength(
      { x: 452, y: 150 },
      { x: 408, y: 150 },
      { x: 370, y: 172 },
      { x: 300, y: 172 },
      200000,
    );
    expect(Math.abs(approximated - reference)).toBeLessThan(1e-6);
    expect(approximated).toBeCloseTo(153.9817, 3);

    // 三条连线的长度（旧实现用 getTotalLength 量，这里算）
    expect(BERG_CALLOUT_LINK_LENGTHS).toHaveLength(BERG_CALLOUT_SLOTS);
    expect(bergCalloutLinkLength(0)).toBeCloseTo(153.98, 1);
    expect(bergCalloutLinkLength(1)).toBeCloseTo(152.02, 1);
    expect(bergCalloutLinkLength(2)).toBeCloseTo(122.14, 1);
  });

  it('起拍点按「先水上、再水下、最后出路」，超表走 0.72 兜底', () => {
    expect([0, 1, 2].map(bergCalloutStart)).toEqual([0.2, 0.5, 0.72]);
    expect(bergCalloutStart(3)).toBe(0.72);
    expect(bergCalloutStart(99)).toBe(0.72);
  });
});

describe('每帧数值：同输入同输出', () => {
  it('同一帧求值两次，结果逐字段相同', () => {
    const state = frameState(120);
    const first = bergFrame(state, api, beatAt(state));
    const second = bergFrame(state, api, beatAt(state));
    expect(second).toEqual(first);
  });

  it('第 0 帧：水面线还没画出来，粒子停在上浮起点', () => {
    const state = frameState(0);
    const calc = bergFrame(state, api, beatAt(state));
    expect(calc.waterLine.strokeDasharray).toBe(String(BERG_WATER_LINE_LENGTH));
    expect(calc.waterLine.strokeDashoffset).toBe(String(BERG_WATER_LINE_LENGTH));
    expect(calc.waterLine.opacity).toBe('0');
    expect(calc.waterOpacity).toBe('0');
    expect(calc.sparks).toHaveLength(BERG_SPARK_COUNT);
    // 第 0 颗粒子：泳道 (0 % 3) − 1 = −1 → 344 − 30 = 314；y 起点 620
    expect(calc.sparks[0]).toEqual({ cx: '314.0', cy: String(BERG_SPARK_Y_FROM) + '.0', opacity: '0' });
  });

  it('任一帧都不出现 NaN，不透明度都钳在 0..1', () => {
    const state = frameState(0);
    for (let frame = 0; frame <= 300; frame += 1) {
      state.localFrame = frame;
      const calc = bergFrame(state, api, beatAt(state));
      const strings = [
        calc.waterLine.strokeDasharray,
        calc.waterLine.strokeDashoffset,
        calc.waterLine.opacity,
        calc.waterOpacity,
        calc.surfaceNoteOpacity,
        calc.mass.transform,
        calc.mass.opacity,
        calc.lightBand.x,
        calc.lightBand.opacity,
      ];
      for (const value of strings) {
        expect(value).not.toMatch(/NaN|undefined/);
      }
      for (const opacity of [
        calc.waterLine.opacity,
        calc.waterOpacity,
        calc.surfaceNoteOpacity,
        calc.mass.opacity,
        calc.lightBand.opacity,
      ]) {
        const n = Number(opacity);
        expect(n).toBeGreaterThanOrEqual(0);
        expect(n).toBeLessThanOrEqual(1);
      }
      for (const spark of calc.sparks) {
        expect(spark.cx).not.toMatch(/NaN|undefined/);
        expect(spark.cy).not.toMatch(/NaN|undefined/);
      }
    }
  });

  it('上浮粒子：中途最偏、两端归位，不透明度两端为 0', () => {
    expect(bergSparkPose(0, 0).opacity).toBe('0');
    expect(bergSparkPose(0, 1).opacity).toBe(String(Math.sin(Math.PI) * 0.9));
    // life = 0.5 时摆幅最大：同一条泳道的 x 与两端不同
    const mid = bergSparkPose(0, 0.5);
    expect(Number(mid.cx)).toBeGreaterThan(Number(bergSparkPose(0, 0).cx));
    expect(Number(mid.cy)).toBeLessThan(Number(bergSparkPose(0, 0).cy));
  });
});

describe('条目归一：空值与超容量都不许崩', () => {
  it('空 items 不抛错，也不产生任何标注帧', () => {
    const state = frameState(120);
    expect(normalizeBergItems([])).toEqual([]);
    expect(normalizeBergItems(undefined)).toEqual([]);
    expect(normalizeBergItems(null)).toEqual([]);
    expect(normalizeBergItems('不是数组')).toEqual([]);
    expect(bergCallouts(state, api, beatAt(state), [])).toEqual([]);
    expect(bergCallouts(state, api, beatAt(state), undefined)).toEqual([]);
  });

  it('字符串项按 {label} 处理，对象项取 label / desc', () => {
    expect(normalizeBergItems(['我要什么', { label: '哪个更好', desc: '比较' }])).toEqual([
      { label: '我要什么', desc: '' },
      { label: '哪个更好', desc: '比较' },
    ]);
    // 旧实现写的是 `entry.label || ''`：假值一律留空，不做 String() 强转
    expect(normalizeBergItems([{ label: 0, desc: null }])).toEqual([{ label: '', desc: '' }]);
    expect(normalizeBergItems([42])).toEqual([{ label: '', desc: '' }]);
  });

  it('超过建议上限（3 条）时复用最后一格，仍然稳定且无 NaN', () => {
    const state = frameState(150);
    const items = ['一', '二', '三', '四', '五', '六'];
    const frames = bergCallouts(state, api, beatAt(state), items);
    expect(frames).toHaveLength(items.length);
    // 焦点始终是**最后一个**条目（旧 `index === items.length - 1`）
    expect(frames.map((frame) => frame.isAccent)).toEqual([
      false, false, false, false, false, true,
    ]);
    for (const frame of frames) {
      expect(frame.link.strokeDasharray).not.toMatch(/NaN|undefined/);
      expect(frame.link.strokeDashoffset).not.toMatch(/NaN|undefined/);
      expect(frame.shift).not.toMatch(/NaN|undefined/);
      expect(Number(frame.linkLength)).toBeGreaterThan(0);
    }
    // 第 4..6 条复用第 3 格：几何仍然落在表内
    const over = bergCalloutGeometry(5);
    expect(over.slot).toBe(BERG_CALLOUT_SLOTS - 1);
    expect(over.linkD).toBe(bergCalloutGeometry(2).linkD);
    expect(over.y).toBe(BERG_CALLOUT_Y[BERG_CALLOUT_SLOTS - 1]);
    // 远远超出时也一样：20 条不崩
    expect(bergCallouts(state, api, beatAt(state), Array.from({ length: 20 }, (_v, i) => `第${i}条`)))
      .toHaveLength(20);
  });
});

describe('填充与层级（水体 / 水上尖端 / 水下主体）', () => {
  it('三档面填充互不相同，水体只用一条水深渐变', () => {
    expect(BERG_LAYER_FILL.waterBody).toBe('url(#berg-depth)');
    expect(BERG_LAYER_FILL.tip).toBe('var(--fig-surface)');
    expect(BERG_LAYER_FILL.mass).toBe('var(--fig-water)');
    const fills = Object.values(BERG_LAYER_FILL);
    expect(new Set(fills).size).toBe(fills.length);

    // 样式表里必须还是这三条：水体走渐变，尖端走实心面，主体走冷色水面
    expect(cssBlock('.berg-water')).toMatch(/fill:\s*url\(#berg-depth\)/);
    expect(cssBlock('.berg-tip')).toMatch(/fill:\s*var\(--fig-surface\)/);
    expect(cssBlock('.berg-mass')).toMatch(/fill:\s*var\(--fig-water\)/);
  });

  it('绘制顺序：水体 → 水面线 → 尖端 → 主体 → 光带（后来者在上）', () => {
    // 水体垫在下面，尖端与主体画在它上面
    expect(bergLayerIndex('waterBody')).toBeLessThan(bergLayerIndex('tip'));
    expect(bergLayerIndex('waterBody')).toBeLessThan(bergLayerIndex('mass'));
    // 水面线在水体之后：线压在水面上，不被水体渐变压暗
    expect(bergLayerIndex('waterBody')).toBeLessThan(bergLayerIndex('waterLine'));
    // 主体在最后：它叠在水体渐变之上，读起来才是「这一大团在水里」
    expect(bergLayerIndex('tip')).toBeLessThan(bergLayerIndex('mass'));
    // 光带在主体之后，并且被裁在主体轮廓内
    expect(bergLayerIndex('mass')).toBeLessThan(bergLayerIndex('lightBand'));
    expect(bergLayerIndex('lightBand')).toBeLessThan(bergLayerIndex('sparks'));
    expect(bergLayerIndex('sparks')).toBeLessThan(bergLayerIndex('callouts'));
  });

  it('源码与冻结的旧 markup 顺序一致：层级不是靠注释维持的', () => {
    const markers: Record<(typeof BERG_PAINT_ORDER)[number], string> = {
      waterBody: 'data-el="waterBody"',
      waterLine: 'data-el="waterLine"',
      surfaceNote: 'data-el="surfaceNote"',
      tip: 'data-el="tip"',
      mass: 'data-el="massGroup"',
      lightBand: 'data-el="lightBand"',
      sparks: 'data-el="sparks"',
      callouts: 'data-el="callouts"',
    };
    const positions = (source: string): number[] =>
      BERG_PAINT_ORDER.map((layer) => {
        const at = source.indexOf(markers[layer]);
        expect(at, `${layer} 在源码里找不到`).toBeGreaterThan(-1);
        return at;
      });

    const legacy = positions(legacyIcebergMarkup());
    const current = positions(jsxSource);
    for (let index = 1; index < BERG_PAINT_ORDER.length; index += 1) {
      expect(legacy[index]!).toBeGreaterThan(legacy[index - 1]!);
      expect(current[index]!).toBeGreaterThan(current[index - 1]!);
    }
  });

  it('旧 markup 的裁剪路径就是主体轮廓，光带因此不会漏到水体或尖端上', () => {
    const markup = legacyIcebergMarkup();
    const massD = 'M138 300 L296 300 L392 452 L348 632 L150 692 L34 500 Z';
    // 同一个 d 出现两次：clipPath 的轮廓 + 主体的路径（旧 markup 1035 / 1013 行）
    expect(markup.split(massD)).toHaveLength(3);
    expect(componentSource.split(massD)).toHaveLength(3);
    // 光带在主体组内、且在光带之后才出现主体路径的闭合
    expect(markup.indexOf('fill="url(#berg-light)"')).toBeGreaterThan(
      markup.indexOf('data-el="massGroup"'),
    );
    expect(componentSource.indexOf('fill="url(#berg-light)"')).toBeGreaterThan(
      componentSource.indexOf('data-el="massGroup"'),
    );
    // 水体矩形与尖端都不写 fill：填充归样式表的令牌，组件不临场挑颜色
    expect(markup).toMatch(/<rect class="berg-water" data-el="waterBody"[^>]*height="460"><\/rect>/);
    expect(markup).toMatch(/<path class="berg-tip" data-el="tip" d="M215 64 L138 300 L296 300 Z"><\/path>/);
  });
});
