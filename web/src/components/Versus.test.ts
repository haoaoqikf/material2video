/**
 * `versus` 迁移的取值与边界对照。
 *
 * 三条断言各挡一类会**静默出错**的问题：
 *
 * 1. **取值与手算一致**：幕内节奏由比例点换算成帧号，算错不会有任何报错，
 *    只会让箭头早半秒长出来——这里把关键帧上的每个数按公式手算一遍；
 * 2. **同输入同输出**：帧号是唯一输入，重复求值与乱序求值必须逐位相同（确定性契约）；
 * 3. **空数据不抛错**：`comparison` 场景没有 `text` / `annotations`，
 *    而 `quote + versus` 又没有 `left` / `right`，两种缺法都要能画出来。
 *
 * 强调短语的分段拿**旧实现当对照**：在 `node:vm` 里跑 `assets/figures.js` 里
 * 那两个纯字符串函数（`escapeHtml` / `emphasize`），再把新实现的片段表拼回 HTML
 * 逐字符比较。旧实现是在已拼好的串上做 `replace`，所以「后一个短语落进前一个短语
 * 的标记里就匹配不到」——这条真实行为必须一起照搬，靠人记是记不住的。
 *
 * 不引入 jsdom：本文件只碰纯函数，组件本身由抽帧对照与闸门去验。
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  VERSUS_ENTRANCE,
  VERSUS_NOTE_OPACITY,
  VERSUS_PROGRESS,
  versusBeat,
  versusHeatValue,
  versusLineTransform,
  versusOpacityValue,
  versusProgress,
  versusText,
  versusTimeline,
  type VersusTiming,
} from './Versus';
// 强调词的标记由运行时统一生成（旧实现 `emphasize` 的等价物），组件不自己拼
import { emphasisHtml } from '@/runtime/figures';

/** 与 `examples/` 的分镜同一个口径：comparison 幕 240 帧、normal 节奏。 */
const SCENE: VersusTiming = {
  localFrame: 0,
  sceneDurationFrames: 240,
  motion: 'normal',
};

function at(localFrame: number, sceneDurationFrames = 240, motion = 'normal'): VersusTiming {
  return { localFrame, sceneDurationFrames, motion };
}

/** 手算用的缓动：与 `motion.ts` 的 `outQuint` / `inOutCubic` 同一表达式。 */
const outQuint = (t: number): number => 1 - (1 - t) ** 5;
const inOutCubic = (t: number): number =>
  t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;

/** 帧号 → 与组件完全相同的推进量（组件每一帧算的就是这几个数）。 */
function timelineAt(localFrame: number): ReturnType<typeof versusTimeline> {
  return versusTimeline(at(localFrame));
}

/* ---------------- 旧实现的对照 ---------------- */

const here = path.dirname(fileURLToPath(import.meta.url));
const figuresPath = path.resolve(
  here,
  '..',
  '..',
  '..',
  '.agents',
  'skills',
  'article2video',
  'assets',
  'figures.js',
);

interface LegacyEmphasis {
  emphasize: (text: unknown, phrases?: unknown, underline?: boolean) => string;
}

/**
 * 在 `node:vm` 里只跑旧实现的两个纯字符串函数。
 *
 * 函数体按花括号配对从源码里截取（不用正则猜缩进），因此旧实现改了这里跟着改，
 * 不存在「抄一份到测试里然后两边悄悄漂移」的问题。
 */
function loadLegacyEmphasis(): LegacyEmphasis {
  const source = readFileSync(figuresPath, 'utf8');
  const context = vm.createContext({});
  vm.runInContext(`${extract(source, 'escapeHtml')}\n${extract(source, 'emphasize')}`, context);
  return context as unknown as LegacyEmphasis;
}

function extract(source: string, name: string): string {
  const start = source.indexOf(`function ${name}(`);
  if (start === -1) {
    throw new Error(`figures.js 里找不到 ${name}`);
  }
  const open = source.indexOf('{', start);
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    const char = source[i];
    if (char === '{') {
      depth += 1;
    } else if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return source.slice(start, i + 1);
      }
    }
  }
  throw new Error(`${name} 的函数体没有闭合`);
}

const legacy = loadLegacyEmphasis();

function mineHtml(text: unknown, phrases?: unknown, underline = true): string {
  return emphasisHtml(text, phrases, { underline });
}

/** 标记里有没有强调片段。旧实现的判据是 `querySelector('.key')` 是否拿到节点。 */
function emphasisHasKey(html: string): boolean {
  return html.includes('class="key"');
}

/**
 * 从标记里读出每个 `<span>` 的开合深度序列。
 *
 * 这是「片段表」时代那条断言的替代：不再有片段对象，但「深度不为负、
 * 不跳级」这条不变量仍然要守——跳级就意味着拼出了没有正确闭合的标签，
 * 浏览器会把后面整段文字吞进错误的位置。
 */
function spanDepths(html: string): number[] {
  const depths: number[] = [];
  let depth = 0;
  for (const match of html.matchAll(/<(\/?)([a-z]+)[^>]*>/g)) {
    if (match[2] !== 'span') {
      continue;
    }
    depth += match[1] === '/' ? -1 : 1;
    depths.push(depth);
  }
  return depths;
}

function legacyHtml(text: unknown, phrases?: unknown, underline = true): string {
  return legacy.emphasize(text, phrases, underline);
}

/** 去掉标签后的可见文本：两边必须一字不差，否则抽帧对照会因为少字而白差像素。 */
function visibleText(html: string): string {
  return html.replace(/<[^>]*>/g, '');
}

/* ---------------- 1. 取值与手算一致 ---------------- */

describe('幕内节奏：比例点与帧数的换算', () => {
  it('beat 按幕长缩放，calm 慢一档、impact 快一档', () => {
    // 老运行时：fraction * sceneDurationFrames / tempo
    expect(versusBeat(SCENE, 0.4)).toBe(96);
    expect(versusBeat(at(0, 240, 'calm'), 0.4)).toBeCloseTo(117.0731707, 6);
    expect(versusBeat(at(0, 240, 'impact'), 0.4)).toBeCloseTo(77.4193548, 6);
  });

  it('空幕（时长 0）退化成「未开始」，不是 NaN', () => {
    const empty: VersusTiming = { localFrame: 0, sceneDurationFrames: 0 };
    expect(versusBeat(empty, 0.4)).toBe(0);
    const timeline = versusTimeline(empty);
    for (const value of Object.values(timeline)) {
      expect(Number.isFinite(value)).toBe(true);
    }
    // 起点全落在第 0 帧，因此第 0 帧就已经到位——这是退化，不是「画错」
    expect(timeline.line).toBe(1);
    expect(timeline.heat).toBe(1);
    expect(versusLineTransform(timeline.line)).toBe('scaleX(1.0000)');
  });

  it('progress 在区间外被钳住，时长为 0 时退化成硬开关', () => {
    expect(versusProgress(at(95), 96, 36, inOutCubic)).toBe(0);
    expect(versusProgress(at(96), 96, 36, inOutCubic)).toBe(0);
    expect(versusProgress(at(132), 96, 36, inOutCubic)).toBe(1);
    expect(versusProgress(at(200), 96, 36, inOutCubic)).toBe(1);
    expect(versusProgress(at(95), 96, 0, inOutCubic)).toBe(0);
    expect(versusProgress(at(96), 96, 0, inOutCubic)).toBe(1);
  });
});

describe('关键帧的推进量：逐项手算', () => {
  it('第 0 帧：什么都还没开始', () => {
    const timeline = timelineAt(0);
    expect(timeline).toEqual({ line: 0, head: 0, heat: 0, note: 0, emphasize: 0 });
  });

  it('第 96 帧：连接线刚抬起来（inOutCubic 在 0 处斜率为 0）', () => {
    // line = inOutCubic((96 - 96) / 24) = 0
    // head = outQuint((96 - 110.4) / 12) → 钳到 0；heat / note 同理
    const timeline = timelineAt(96);
    expect(timeline).toEqual({ line: 0, head: 0, heat: 0, note: 0, emphasize: 0 });
  });

  it('第 108 帧：线走完一半（1/4 幕 = 60 帧里过了 12 帧）', () => {
    // line = inOutCubic((108 - 96) / 24) = 4 × 0.5³
    const timeline = timelineAt(108);
    expect(timeline.line).toBeCloseTo(inOutCubic(0.5), 12);
    expect(timeline.line).toBeCloseTo(0.5, 12);
  });

  it('第 120 帧：线长满、箭头头几乎点亮、右栏还没升温', () => {
    // line = inOutCubic((120 - 96) / 24) = 1
    // head = outQuint((120 - 110.4) / 12) = outQuint(0.8)
    // heat = inOutCubic((120 - 124.8) / 33.6) → 钳到 0
    const timeline = timelineAt(120);
    expect(timeline.line).toBe(1);
    expect(timeline.head).toBeCloseTo(outQuint(0.8), 12);
    expect(timeline.head).toBeCloseTo(0.99968, 12);
    expect(timeline.heat).toBe(0);
    expect(timeline.note).toBe(0);
    expect(timeline.emphasize).toBe(0);
  });

  it('第 141 帧：右栏升到 inOutCubic 曲线上（0.482… 的三次方段）', () => {
    const fraction = (141 - 124.8) / 33.6;
    expect(fraction).toBeCloseTo(0.4821428, 6);
    expect(timelineAt(141).heat).toBeCloseTo(inOutCubic(fraction), 12);
    expect(timelineAt(141).heat).toBeGreaterThan(0);
    expect(timelineAt(141).heat).toBeLessThan(1);
  });

  it('第 239 帧（末帧）：线 / 箭头 / 升温到顶，注释只到 0.9', () => {
    const timeline = timelineAt(239);
    expect(timeline.line).toBe(1);
    expect(timeline.head).toBe(1);
    expect(timeline.heat).toBe(1);
    expect(timeline.note).toBeCloseTo(VERSUS_NOTE_OPACITY, 12);
    expect(timeline.emphasize).toBe(1);
    // 写进 CSS 的字符串形式：`--vs-heat` 就是 calc() 的乘数
    expect(versusHeatValue(timeline.heat)).toBe('1.000');
    expect(versusOpacityValue(timeline.note)).toBe('0.9');
  });

  it('注释的时长是 20 帧、升温的时长是 0.14 个幕长（不是同一个）', () => {
    expect(timelineAt(148).note).toBe(0);
    expect(timelineAt(149).note).toBeGreaterThan(0);
    expect(timelineAt(169).note).toBeCloseTo(VERSUS_NOTE_OPACITY, 12);
    expect(timelineAt(124).heat).toBe(0);
    expect(timelineAt(125).heat).toBeGreaterThan(0);
    expect(timelineAt(158).heat).toBeLessThan(1);
    expect(timelineAt(159).heat).toBe(1);
  });

  it('每个比例点都落在老实现写的那一拍上', () => {
    expect(VERSUS_PROGRESS.line).toEqual({ at: 0.4, span: 0.1, ease: 'inOutCubic' });
    expect(VERSUS_PROGRESS.head).toEqual({ at: 0.46, span: 12, ease: 'outQuint' });
    expect(VERSUS_PROGRESS.heat).toEqual({ at: 0.52, span: 0.14, ease: 'inOutCubic' });
    expect(VERSUS_PROGRESS.note).toEqual({ at: 0.62, span: 20, ease: 'outQuint' });
    expect(VERSUS_ENTRANCE.lead.distance).toBe(48);
    expect(VERSUS_ENTRANCE.leftSide.distance).toBe(-46);
    expect(VERSUS_ENTRANCE.rightSide.distance).toBe(46);
    expect(VERSUS_ENTRANCE.rightSide.phase).toBe(40);
    expect(VERSUS_ENTRANCE.leftSide.amplitude).toBe(2.2);
  });
});

describe('连续量 --vs-heat 的边界区间', () => {
  it('整幕都在 0..1 内、单调不减，且首位两端分别是 0 与 1', () => {
    let previous = -1;
    for (let frame = 0; frame <= 240; frame += 1) {
      const heat = timelineAt(frame).heat;
      expect(heat).toBeGreaterThanOrEqual(0);
      expect(heat).toBeLessThanOrEqual(1);
      // 缓动是单调的：升温过程不许回退（回退就是画面上的「退热」抖动）
      expect(heat).toBeGreaterThanOrEqual(previous);
      previous = heat;
      // 三位小数写进 CSS 后仍落在 0..1：越界会让边框透明度与光晕一起出错
      const written = Number(versusHeatValue(heat));
      expect(written).toBeGreaterThanOrEqual(0);
      expect(written).toBeLessThanOrEqual(1);
    }
    expect(timelineAt(0).heat).toBe(0);
    expect(timelineAt(240).heat).toBe(1);
  });

  it('线的生长、箭头头与注释也都在各自的区间内', () => {
    for (let frame = 0; frame <= 240; frame += 1) {
      const timeline = timelineAt(frame);
      expect(timeline.line).toBeGreaterThanOrEqual(0);
      expect(timeline.line).toBeLessThanOrEqual(1);
      expect(timeline.head).toBeGreaterThanOrEqual(0);
      expect(timeline.head).toBeLessThanOrEqual(1);
      expect(timeline.note).toBeGreaterThanOrEqual(0);
      expect(timeline.note).toBeLessThanOrEqual(VERSUS_NOTE_OPACITY);
      expect(timeline.emphasize).toBeGreaterThanOrEqual(0);
      expect(timeline.emphasize).toBeLessThanOrEqual(1);
    }
  });

  it('字符串格式与老实现的 toFixed 一致（线四位、升温三位）', () => {
    expect(versusLineTransform(0)).toBe('scaleX(0.0000)');
    expect(versusHeatValue(0)).toBe('0.000');
    expect(versusHeatValue(0.0289)).toBe('0.029');
    expect(versusLineTransform(0.123456789)).toBe('scaleX(0.1235)');
  });
});

/* ---------------- 2. 同输入同输出 ---------------- */

describe('确定性：帧号是唯一输入', () => {
  it('重复求值逐位相同', () => {
    for (const frame of [0, 1, 47, 96, 120, 141, 199, 239]) {
      expect(timelineAt(frame)).toEqual(timelineAt(frame));
    }
  });

  it('乱序求值与顺序求值结果相同（没有跨帧状态）', () => {
    const frames = [0, 12, 61, 96, 120, 141, 200, 239];
    const reference = new Map(frames.map((frame) => [frame, timelineAt(frame)]));
    const shuffled = [239, 0, 120, 61, 200, 96, 141, 12];
    for (const frame of shuffled) {
      expect(timelineAt(frame)).toEqual(reference.get(frame));
    }
  });

  it('强调短语的分段只与文案有关', () => {
    const text = '努力没有结果，\n往往不是因为不够努力，\n而是因为方向错了。';
    const phrases = ['方向'];
    expect(mineHtml(text, phrases)).toBe(mineHtml(text, phrases));
  });
});

/* ---------------- 3. 空数据不抛错 ---------------- */

describe('空数据：两种情况都要能画出来', () => {
  it('comparison 场景：没有 text / emphasis / annotations', () => {
    expect(versusText(undefined)).toBe('');
    expect(versusText(null)).toBe('');
    expect(versusText(0)).toBe('0');
    expect(versusText('更多自由')).toBe('更多自由');
    // 没有 text 时引子整段不占位，但推进量照算（老实现也是先算再决定显示）
    expect(timelineAt(239).heat).toBe(1);
    expect(mineHtml(undefined, undefined)).toBe('');
    expect(emphasisHasKey(mineHtml(undefined, undefined))).toBe(false);
  });

  it('quote + versus：left / right 缺失时退回标注，两者都缺就留空', () => {
    // 取值规则照抄 `data.left || ann.left` / `data.right || ann.right`
    const left = (data: string | undefined, ann: string | undefined): string =>
      versusText(data ?? ann);
    const right = (data: string | undefined, ann: string | undefined): string =>
      versusText(data ?? ann);
    expect([left('更多自由', '甲'), right('更长比较', '乙')]).toEqual(['更多自由', '更长比较']);
    expect([left(undefined, '甲'), right(undefined, '乙')]).toEqual(['甲', '乙']);
    expect([left(undefined, undefined), right(undefined, undefined)]).toEqual(['', '']);
  });

  it('非法的强调短语（非数组、空串、数字、对象）既不抛错也不改文本', () => {
    const text = '一段没有重点的话';
    for (const phrases of [undefined, null, '不是数组', [], [''], [0], [{}]]) {
      const html = mineHtml(text, phrases);
      expect(emphasisHasKey(html)).toBe(false);
      expect(visibleText(html)).toBe(text);
    }
  });

  it('短语没命中时不会多出节点（老实现的 querySelector 返回 null）', () => {
    expect(mineHtml('普通文案', ['不存在的词'])).toBe('普通文案');
  });
});

/* ---------------- 强调短语：与旧实现逐字符对照 ---------------- */

describe('强调短语：拿旧实现当对照', () => {
  const CASES: Array<[unknown, unknown]> = [
    ['而是因为方向错了。', ['方向']],
    ['选项越多\n决定越慢', ['越多']],
    ['选择消耗的\n是做决定的力气', ['力气']],
    ['缺的不是更好的选项\n而是一把砍掉选项的刀', ['砍掉选项']],
    // 短语不在文案里：整段普通，不许凭空造一个 key
    ['本来就找不到这个词', ['没有的短语']],
    // 重叠短语：后一个落进前一个的标记里，老实现匹配不到——必须一起照搬
    ['自由与由己', ['自由', '由']],
    ['由己与自由', ['由', '自由']],
    // 同一短语出现两次：只替换第一处
    ['方向错了，方向还是错的', ['方向']],
    // 需要转义的正文与短语
    ['a < b & c > d', ['&']],
    ['<script>alert(1)</script>', ['alert']],
    // 空值
    ['', ['方向']],
    [null, ['方向']],
    ['方向', undefined],
  ];

  it('逐字符等于旧实现的 innerHTML（带底横线）', () => {
    for (const [text, phrases] of CASES) {
      expect(mineHtml(text, phrases)).toBe(legacyHtml(text, phrases));
    }
  });

  it('不带底横线时也逐字符相同', () => {
    for (const [text, phrases] of CASES) {
      expect(mineHtml(text, phrases, false)).toBe(legacyHtml(text, phrases, false));
    }
  });

  it('可见文本不丢字、不改序（差异只允许出现在标签上）', () => {
    for (const [text, phrases] of CASES) {
      expect(visibleText(mineHtml(text, phrases))).toBe(visibleText(legacyHtml(text, phrases)));
    }
  });

  it('只产出 .key 与 .key-underline 两种标签，属性一字不差', () => {
    // 逐个**开标签**比对：正则匹配到的是 `<span class="key-underline">` 这一段，
    // 因此集合里写完整的 `<span …></span>` 是匹配不上的（那条断言会永远失败）
    const allowed = new Set(['<span class="key">', '<span class="key-underline">', '</span>']);
    for (const [text, phrases] of CASES) {
      for (const tag of mineHtml(text, phrases).match(/<[^>]*>/g) ?? []) {
        expect(allowed.has(tag), `多出来的标签：${tag}`).toBe(true);
      }
    }
  });

  it('嵌套情形：短语落进已强调的片段里会被再套一层（旧实现真的会）', () => {
    /*
     * 老实现是在已拼好的串上继续 `replace`，所以「由」命中的是「自由」所在的**文本**，
     * 于是「自由」之外又多出一个包裹「由」的 key：
     *   <span class="key">自<span class="key">由<span class="key-underline"></span>
     *   </span><span class="key-underline"></span></span>与由己
     * 这不是缺陷，是要一起照搬的行为。期望值一律由旧实现给出，
     * 手写一遍就等于把「我以为它会怎么嵌套」写进断言。
     */
    expect(mineHtml('自由与由己', ['自由', '由'])).toBe(legacyHtml('自由与由己', ['自由', '由']));
    // 反过来：先包「由」，此后「自由」在串里已经连不起来（中间隔着标记），因此匹配不到
    expect(mineHtml('自由与由己', ['由', '自由'])).toBe(legacyHtml('自由与由己', ['由', '自由']));
  });

  it('嵌套标记的深度不跳级（跳级会拼出没有闭合的标签）', () => {
    const html = mineHtml('自由与由己', ['自由', '由']);
    expect(emphasisHasKey(html)).toBe(true);
    let previous = 0;
    for (const depth of spanDepths(html)) {
      expect(depth).toBeGreaterThanOrEqual(0);
      // 嵌套可以到三层（key > key > key-underline），因此上界只要求「不跳级」
      expect(Math.abs(depth - previous)).toBeLessThanOrEqual(1);
      previous = depth;
    }
    // 收尾必须回到 0：否则标签没有闭合
    expect(previous).toBe(0);
  });
});
