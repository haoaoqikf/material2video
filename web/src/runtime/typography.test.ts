/**
 * 排版引擎的纯函数契约（逐条对应 `tests/test_typography.py`）。
 *
 * 字体度量的部分不在这里：`fit` 收的是一个「文本 → em 数」的测宽函数，
 * 所以这些断言不依赖浏览器，也不依赖某个具体字体——测宽换成等宽假字体后，
 * 「取档、断行、到下限即停」这三条规则本身仍然可断言。
 *
 * 另一组断言把 `assets/typography.js`（旧实现）当**对照实现**在 `node:vm` 里
 * 跑起来逐值比对：字号阶、正文下限、`levelAtLeast`、`balance` 都是纯函数，
 * 新工程是移植，取值与行为都不许漂。
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  balance,
  emWidthFallback,
  fit,
  fitForPreset,
  isCJK,
  levelAtLeast,
  levelByName,
  maxLevelIndex,
  MIN_BODY_PX,
  SCALE,
  significant,
  type FitOptions,
} from '@/runtime/typography';

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, '..', '..');
const assets = path.resolve(webRoot, '..', '.agents', 'skills', 'article2video', 'assets');

interface LegacyType {
  levels: Array<{ name: string; size: number; leading: number; tracking: number }>;
  minBodyPx: number;
  levelAtLeast: (px: number) => { name: string; size: number };
  balance: (text: string | null, limit: number) => string[];
  significant: (text: string | null) => string;
}

function loadLegacy(): LegacyType {
  const sandbox: Record<string, unknown> = { console, A2V: {} };
  sandbox.window = sandbox;
  const context = vm.createContext(sandbox);
  vm.runInContext(
    readFileSync(path.join(assets, 'typography.js'), 'utf8'),
    context,
    { filename: 'typography.js' },
  );
  return (sandbox.A2V as { type: LegacyType }).type;
}

const legacy = loadLegacy();

/** 等宽假字体：每个汉字 1em，其余 0.5em。用它把「排版规则」与「字体度量」分开。 */
function fakeMeasure(text: string): number {
  return Array.from(String(text)).reduce((sum, ch) => sum + (isCJK(ch) ? 1 : 0.5), 0);
}

function options(overrides: Partial<FitOptions> = {}): FitOptions {
  return { text: '短句', availableWidth: 888, measure: fakeMeasure, ...overrides };
}

describe('字号阶', () => {
  it('从大到小排列，两端是字阶锚点', () => {
    const sizes = SCALE.map((level) => level.size);
    expect(sizes).toEqual([...sizes].sort((a, b) => b - a));
    expect(sizes[0]).toBe(350);
    expect(sizes[sizes.length - 1]).toBe(28);
    expect(sizes).toHaveLength(10);
  });

  it('相邻档位的比例落在 1.1–1.6', () => {
    // 字阶是模块化的：直接跳档（比如 140 → 350）会让画面突然空出两块
    for (let i = 1; i < SCALE.length; i += 1) {
      const ratio = SCALE[i - 1].size / SCALE[i].size;
      expect(ratio).toBeGreaterThanOrEqual(1.1);
      expect(ratio).toBeLessThanOrEqual(1.6);
    }
  });

  it('每一档都带行高与字距', () => {
    for (const level of SCALE) {
      expect(level.leading).toBeGreaterThan(0);
      expect(typeof level.tracking).toBe('number');
    }
  });

  it('正文下限向上取档落在 body 上', () => {
    expect(MIN_BODY_PX).toBe(36);
    expect(levelAtLeast(MIN_BODY_PX).name).toBe('body');
  });

  it('与旧实现的字号阶逐值一致', () => {
    expect(SCALE.map((level) => ({ ...level }))).toEqual(legacy.levels);
    expect(MIN_BODY_PX).toBe(legacy.minBodyPx);
  });
});

describe('取档与兜底', () => {
  it('向上取档', () => {
    expect(levelAtLeast(36).name).toBe('body');
    expect(levelAtLeast(40).name).toBe('body');
    expect(levelAtLeast(70).name).toBe('title');
  });

  it('请求超过最大档时给最大档，不是最小档', () => {
    expect(levelAtLeast(1000).name).toBe('numeral');
  });

  it('逐值对照旧实现', () => {
    for (const px of [0, 20, 28, 30, 34, 36, 40, 60, 76, 96, 120, 140, 220, 350, 1000]) {
      expect(levelAtLeast(px).name, `levelAtLeast(${px})`).toBe(legacy.levelAtLeast(px).name);
    }
  });

  it('档名兜底落在 hero 上，而不是最大档', () => {
    // 写死下标 0 的兜底会随「顶部又加了一档」漂移成「按最大档排版」
    expect(maxLevelIndex(undefined)).toBe(SCALE.findIndex((level) => level.name === 'hero'));
    expect(maxLevelIndex('不认识的档名')).toBe(maxLevelIndex('hero'));
    expect(maxLevelIndex('title')).toBe(SCALE.findIndex((level) => level.name === 'title'));
    expect(levelByName('numeral')?.size).toBe(350);
    expect(levelByName('nope')).toBeNull();
  });
});

describe('均衡断行', () => {
  const cases: Array<[string, string, number]> = [
    ['cjk', '我们以为选择越多越自由，其实每多一个选项就多一次犹豫', 8],
    ['cjkLong', '注意力是唯一不可再生的资源，你把时间花在哪里，你就会成为什么样的人', 10],
    ['hardBreak', '第一行\n第二行', 4],
    ['mixed', 'OKR 与 KPI 的区别在于目标是否可协商', 9],
    ['noLeadingPunctuation', '先做重要的事，而不是紧急的事，这是效率的第一原则。', 8],
    ['empty', '', 8],
    ['shortText', '短', 8],
  ];

  it.each(cases)('%s：每行不超过上限，且逐字对照旧实现', (_name, text, limit) => {
    const lines = balance(text, limit);
    for (const line of lines) {
      expect(Array.from(line).length).toBeLessThanOrEqual(Math.max(2, limit));
    }
    expect(lines).toEqual(legacy.balance(text, limit));
  });

  it('行首不出现标点（避头尾）', () => {
    const lines = balance('先做重要的事，而不是紧急的事，这是效率的第一原则。', 8);
    for (const line of lines) {
      expect('，。、；：！？）】》').not.toContain(line[0]);
    }
  });

  it('硬换行优先，段落顺序不变', () => {
    expect(balance('第一行\n第二行', 4)).toEqual(['第一行', '第二行']);
  });

  it('末行不留孤字', () => {
    for (const [, text, limit] of cases) {
      const lines = balance(text, limit);
      if (lines.length > 1) {
        expect(Array.from(lines[lines.length - 1]).length).toBeGreaterThanOrEqual(2);
      }
    }
  });

  it('一个字都不丢', () => {
    const text = '我们以为选择越多越自由，其实每多一个选项就多一次犹豫';
    expect(balance(text, 10).join('')).toBe(text);
    expect(significant(balance(text, 10).join('\n'))).toBe(significant(text));
    expect(significant(text)).toBe(legacy.significant(text));
  });

  it('退化输入不抛错', () => {
    expect(balance('', 8)).toEqual(['']);
    expect(balance('短', 8)).toEqual(['短']);
    expect(balance(null, 6)).toEqual(['']);
    // 上限小于 2 时按 2 处理，不能返回空行把文本吃掉
    expect(balance('一二三四五六七八九十', 1).join('')).toBe('一二三四五六七八九十');
  });

  it('空行是有意保留的段落分隔，不是丢失', () => {
    expect(balance('上\n\n下', 4)).toEqual(['上', '', '下']);
  });
});

describe('取档：到正文下限即停', () => {
  it('宽度为 0 时不假装排好了', () => {
    const fitted = fit(options({ availableWidth: 0 }));
    expect(fitted.fits).toBe(false);
    expect(fitted.measured).toBe(false);
    expect(fitted.reason).toBe('no-width');
  });

  it('长文案不会被缩到正文下限以下', () => {
    const text = '我们以为选择越多越自由，其实每多一个选项就多一次犹豫，而犹豫本身就是成本';
    // 宽度窄到「断行之后仍然放不下」：断行的最小粒度是两个字，40px 下就是 80px，
    // 所以 60px 这个宽度无论怎么断都放不下——此时必须报 fits: false，而不是继续缩字号
    const fitted = fit(options({ text, availableWidth: 60 }));
    expect(fitted.fontSize).toBeGreaterThanOrEqual(MIN_BODY_PX);
    expect(fitted.fits).toBe(false);
    expect(fitted.reason).toBe('overflows-at-min-size');
  });

  it('窄容器里断成多行就放得下，不误报溢出', () => {
    // 旧实现会拿「原文最长行的字数」当断行上限，于是这种文案被判成「缩到下限仍放不下」
    const text = '我们以为选择越多越自由，其实每多一个选项就多一次犹豫';
    const fitted = fit(options({ text, availableWidth: 300 }));
    expect(fitted.lines.length).toBeGreaterThanOrEqual(2);
    expect(fitted.fits).toBe(true);
    expect(fitted.lines.join('')).toBe(text);
  });

  it('断成两行放得下就不报溢出', () => {
    const text = '我们以为选择越多越自由，其实每多一个选项就多一次犹豫';
    const fitted = fit(options({ text, availableWidth: 900 }));
    expect(fitted.fits).toBe(true);
    expect(fitted.reason).toBeNull();
    expect(fitted.lines.length).toBeGreaterThan(1);
    expect(fitted.lines.join('')).toBe(text);
  });

  it('短文案取到上限档', () => {
    const fitted = fit(options({ text: '自由', availableWidth: 888, maxLevel: 'hero' }));
    expect(fitted.level).toBe('hero');
    expect(fitted.fontSize).toBe(140);
    expect(fitted.lines).toEqual(['自由']);
  });

  it('上限档可以压到 headline', () => {
    const fitted = fit(options({ text: '一句话结论', availableWidth: 888, maxLevel: 'headline' }));
    expect(fitted.fontSize).toBeLessThanOrEqual(96);
  });

  it('显式下限生效，但仍不会低于字阶最低档', () => {
    const text = '我们以为选择越多越自由，其实每多一个选项就多一次犹豫，而犹豫本身就是成本';
    const fitted = fit(options({ text, availableWidth: 300, minPx: 60 }));
    expect(fitted.fontSize).toBeGreaterThanOrEqual(60);
  });

  it('同一输入永远同一结果（帧无关）', () => {
    const text = '我们以为选择越多越自由，其实每多一个选项就多一次犹豫';
    const first = fit(options({ text, availableWidth: 620 }));
    const second = fit(options({ text, availableWidth: 620 }));
    expect(second).toEqual(first);
  });

  it('测宽失败时标记为未实测，而不是假装量到了', () => {
    const fitted = fit(
      options({
        text: '文字',
        availableWidth: 888,
        measure: () => 0,
      }),
    );
    expect(fitted.measured).toBe(false);
  });
});

describe('未启用预设时不取档', () => {
  it('没有预设就拿不到排版结果', () => {
    expect(fitForPreset(undefined, options())).toBeNull();
    expect(fitForPreset('', options())).toBeNull();
    expect(fitForPreset('unknown', options())).toBeNull();
  });

  it('启用预设时照常取档', () => {
    const fitted = fitForPreset('keynote', options({ text: '自由', availableWidth: 888 }));
    expect(fitted?.level).toBe('hero');
  });
});

describe('字宽估算', () => {
  it('汉字算 1，拉丁按 0.55 估', () => {
    expect(emWidthFallback('汉')).toBeCloseTo(1, 6);
    expect(emWidthFallback('ab')).toBeCloseTo(0.55, 6);
    expect(emWidthFallback('')).toBe(1);
  });

  it('汉字判定边界', () => {
    expect(isCJK('汉')).toBe(true);
    expect(isCJK('，')).toBe(true);
    expect(isCJK('a')).toBe(false);
    expect(isCJK('1')).toBe(false);
  });
});
