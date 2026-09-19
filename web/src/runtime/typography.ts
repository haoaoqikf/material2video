/**
 * 排版引擎（由 `assets/typography.js` 的纯函数部分移植为 TypeScript）。
 *
 * 它回答一个问题：**这段文字用哪一档字号、断成哪几行**。
 * 取档按实测宽度从上往下试，断行按宽度均衡，缩到正文下限就不再缩、
 * 而是如实报「放不下」——低到读不出来的字比溢出更糟。
 *
 * 与旧实现的两处结构差异，都是 React 决定的：
 *
 * 1. 旧版把 DOM 元素当输入（`fit({el})`），在里面量宽度、写 `style`。
 *    这里只收「可用宽度 + 一个测宽函数」，因此可以在 Node 里逐值测试，
 *    组件层只负责把元素量出来喂进去。**测量与排版分开**之后，
 *    「同一份文案在同一宽度下永远取同一档」成了可以直接断言的性质。
 * 2. 写回 DOM 的部分（`applyFit` / `reflow` / `optical`）不在这里：
 *    React 里文字由 JSX 渲染，重排是「算出 lines 再渲染」，
 *    不需要在已有 DOM 上做「保留子元素的字符级改写」。
 *    对应的契约（强调词与逐字节点不被抹掉）由组件结构本身保证。
 *
 * 字号档与 `tokens.css` 的 `--a2v-size-*` 一一对应，`typography.test.ts`
 * 会对照两处：漂移即失败，因为引擎取档与样式表取值必须是同一个真源。
 */

/** 一档字号。`tracking` 是 em 值，与 `--a2v-tracking-*` 同源。 */
export interface TypeLevel {
  name: string;
  size: number;
  leading: number;
  tracking: number;
}

/** 字号阶。**从大到小**排列：`fit` 与 `levelAtLeast` 都依赖这个顺序。 */
export const SCALE: readonly TypeLevel[] = [
  { name: 'numeral', size: 350, leading: 1, tracking: -0.04 },
  { name: 'mega', size: 220, leading: 1, tracking: -0.035 },
  { name: 'hero', size: 140, leading: 1.06, tracking: -0.03 },
  { name: 'display', size: 120, leading: 1.1, tracking: -0.025 },
  { name: 'headline', size: 96, leading: 1.14, tracking: -0.02 },
  { name: 'title', size: 76, leading: 1.2, tracking: -0.015 },
  { name: 'lead', size: 60, leading: 1.32, tracking: -0.005 },
  { name: 'body', size: 40, leading: 1.47, tracking: 0 },
  { name: 'label', size: 34, leading: 1.4, tracking: 0.14 },
  { name: 'caption', size: 28, leading: 1.45, tracking: 0.06 },
];

/**
 * 正文下限：低于此值的文字在竖屏上不可读，规范要求「拆场景」而不是「缩字号」。
 * 引擎因此不会取到比它更小的档，而是报告 `fits: false`。
 */
export const MIN_BODY_PX = 36;

/** 中文标点：不参与单字宽度统计（它们本来就窄），也是断行时的语义边界。 */
export const CJK_PUNCT = '，。！？；：、）」』】》〉·…—～!?,.;:)]}\'"';
export const OPEN_PUNCT = '「『【（(《〈[{';
/** 避头尾：这些不能出现在行首。 */
export const NO_LINE_START = '，。！？；：、）』」】》〉·…～!?,.;:)]}%';
/** 避尾：这些不能留在行末。 */
export const NO_LINE_END = '「『【（(《〈[{';

export function isCJK(ch: string): boolean {
  const code = ch.codePointAt(0) ?? 0;
  return (
    (code >= 0x2e80 && code <= 0x9fff) ||
    (code >= 0xf900 && code <= 0xfaff) ||
    (code >= 0xff00 && code <= 0xff60) ||
    (code >= 0xffe0 && code <= 0xffe6)
  );
}

export function levelIndex(name: string | undefined): number {
  if (!name) {
    return -1;
  }
  return SCALE.findIndex((level) => level.name === name);
}

export function levelByName(name: string | undefined): TypeLevel | null {
  const index = levelIndex(name);
  return index < 0 ? null : SCALE[index];
}

/**
 * 取档上限的下标。
 *
 * 兜底按**名字**找 hero，不写死下标 0：字阶顶部是可以继续加档的
 * （主角数值就加在 hero 之上），写死下标会让兜底的含义随「哪天又加了一档」
 * 漂移——从「按 hero 排版」变成「按最大档排版」。
 */
export function maxLevelIndex(name?: string): number {
  const fallback = levelIndex('hero');
  return levelIndex(name) >= 0 ? levelIndex(name) : fallback;
}

/**
 * 不小于给定字号的最近档（向上取档，例如下限 36px 会落到 body 40px）。
 *
 * SCALE 按**从大到小**排列，所以兜底方向不要写反：请求的字号比最大档还大时
 * 返回最大档，而不是最小档——后者会让 hero 级的标题突然变成角标大小。
 */
export function levelAtLeast(px: number): TypeLevel {
  for (let i = SCALE.length - 1; i >= 0; i -= 1) {
    if (SCALE[i].size >= px) {
      return SCALE[i];
    }
  }
  return SCALE[0];
}

/** 量不到字宽时的经验平均字宽：全角汉字算 1，其余按拉丁估算。 */
export function emWidthFallback(text: string): number {
  const chars = Array.from(String(text));
  let wide = 0;
  for (const ch of chars) {
    if (isCJK(ch)) {
      wide += 1;
    }
  }
  return chars.length ? (wide + (chars.length - wide) * 0.55) / chars.length : 1;
}

/** 去掉换行符后的代码点序列：用于「字符不丢不增」的比对与稳定签名。 */
export function significant(text: string | null | undefined): string {
  return Array.from(String(text ?? ''))
    .filter((ch) => ch !== '\n')
    .join('');
}

/** 测量函数：给定文本，返回它的宽度（单位是 em，乘以字号就是像素）。 */
export type Measure = (text: string) => number;

export function isBreakOpportunity(chars: string[], index: number): boolean {
  const prev = chars[index - 1];
  const next = chars[index];
  if (next === undefined) {
    return false;
  }
  if (NO_LINE_START.indexOf(next) >= 0) {
    return false;
  }
  if (NO_LINE_END.indexOf(prev) >= 0) {
    return false;
  }
  if (isCJK(prev) || isCJK(next)) {
    return true;
  }
  return prev === ' ' || next === ' ';
}

/**
 * 把文本断成最多 `maxCharsPerLine` 字的行，行数最少且尽量均衡。
 *
 * 规则（按优先级）：
 *   1. 显式 `\n` 是硬换行，永不重排；
 *   2. 末行不得只剩一个字或一个标点（孤字）；
 *   3. 标点不出现在行首（避头尾）；
 *   4. 各行字数尽量均衡，而不是「第一行塞满」。
 */
export function balance(text: string | null | undefined, maxCharsPerLine: number): string[] {
  const paragraphs = String(text ?? '').split('\n');
  const out: string[] = [];
  const limit = Math.max(2, Math.floor(maxCharsPerLine) || 2);

  for (const paragraph of paragraphs) {
    const chars = Array.from(paragraph);
    if (!chars.length) {
      out.push('');
      continue;
    }
    const lineCount = Math.max(1, Math.ceil(chars.length / limit));
    let start = 0;
    for (let line = 0; line < lineCount; line += 1) {
      const remainingLines = lineCount - line;
      const remainingChars = chars.length - start;
      if (remainingLines === 1) {
        out.push(chars.slice(start).join(''));
        break;
      }
      // 末行至少要留两个字，避免孤字
      const minTake = Math.max(2, remainingChars - limit * (remainingLines - 1));
      let maxTake = Math.min(limit, remainingChars - 2 * (remainingLines - 1));
      if (maxTake < minTake) {
        maxTake = minTake;
      }
      const ideal = Math.round(remainingChars / remainingLines);
      let take = -1;
      // 先向后找（宁可略长，避免把标点甩到下一行行首），再向前找
      for (let ahead = 0; ahead <= 3 && take < 0; ahead += 1) {
        const candidate = Math.min(maxTake, ideal + ahead);
        if (
          candidate >= minTake &&
          candidate < remainingChars &&
          isBreakOpportunity(chars, start + candidate)
        ) {
          take = candidate;
        }
      }
      for (let behind = 1; behind <= 3 && take < 0; behind += 1) {
        const back = ideal - behind;
        if (back >= minTake && isBreakOpportunity(chars, start + back)) {
          take = back;
        }
      }
      if (take < 0) {
        take = Math.min(maxTake, Math.max(minTake, ideal));
      }
      out.push(chars.slice(start, start + take).join(''));
      start += take;
    }
  }
  return out;
}

/**
 * 按可用宽度换算「单行最多几个字」，供 `balance` 使用。
 *
 * 用**待排文本自身**的平均字宽，而不是固定按全角汉字估：拉丁文的字宽只有
 * 汉字的六成，按汉字算会把「一行放得下 20 个字母」当成只放得下 12 个，
 * 凭空多断出一行。测不到字宽时退回按汉字估算。
 */
export function charsPerLine(
  measure: Measure,
  fontSize: number,
  availableWidth: number,
  sample?: string,
): number {
  const text = sample == null || sample === '' ? '汉' : String(sample);
  const count = Math.max(1, Array.from(text).length);
  let average = measure(text) / count;
  if (!Number.isFinite(average) || average <= 0) {
    average = emWidthFallback(text);
  }
  return Math.max(2, Math.floor(availableWidth / (average * fontSize)));
}

export interface FitResult {
  level: string;
  fontSize: number;
  lineHeight: number;
  letterSpacing: number;
  lines: string[];
  lineCount: number;
  fits: boolean;
  /** 是否逐字实测过宽度；false 表示走了估算路径 */
  measured: boolean;
  reason: 'no-width' | 'overflows-at-min-size' | null;
}

export interface FitOptions {
  text: string | null | undefined;
  /** 可用宽度（px）。≤0 表示元素还没挂载好，不能假装排好了 */
  availableWidth: number;
  /** 测宽函数：返回 em 数（乘字号得像素） */
  measure: Measure;
  /** 可接受的最大档位名（默认 hero） */
  maxLevel?: string;
  /** 可接受的最小字号（默认正文下限 36px） */
  minPx?: number;
}

function result(
  level: TypeLevel,
  lines: string | string[],
  lineCount: number,
  measured: boolean,
  fits: boolean,
  reason: FitResult['reason'],
): FitResult {
  return {
    level: level.name,
    fontSize: level.size,
    lineHeight: level.leading,
    letterSpacing: level.tracking,
    lines: Array.isArray(lines) ? lines : [String(lines)],
    lineCount,
    fits,
    measured,
    reason,
  };
}

/**
 * 为一段文本在字号阶上取档。
 *
 * 算法（与旧实现逐行相同）：从上限档往下试，第一个放得下的档就是结果；
 * 触到正文下限仍放不下时停止下探，把断行结果与 `fits: false` 一起返回。
 */
export function fit(options: FitOptions): FitResult {
  const raw = String(options.text ?? '');
  const measure = options.measure;
  const maxIndex = maxLevelIndex(options.maxLevel);
  const minPx = options.minPx === undefined ? MIN_BODY_PX : options.minPx;
  const minIndex = Math.max(0, SCALE.indexOf(levelAtLeast(minPx)));
  const availableWidth = options.availableWidth;

  if (!availableWidth || availableWidth <= 0) {
    // 元素尚未挂载或宽度为 0：不能假装排好了
    return result(SCALE[Math.max(maxIndex, minIndex)], raw, 1, false, false, 'no-width');
  }

  const hardLines = raw.split('\n');
  let level: TypeLevel | null = null;
  let lines: string[] = [];
  let measured = true;

  for (let i = maxIndex; i < SCALE.length; i += 1) {
    const candidate = SCALE[i];
    // 硬换行必须保留：逐段落算，取最长段
    let advance = 0;
    let anyUnknown = false;
    for (const hardLine of hardLines) {
      const piece = measure(hardLine);
      // 空段落不算「量不到」：组件里有些可选文本位平时是空的，
      // 把空串记成量测失败会让整个元素被标成未实测，属于误报
      if (!piece && Array.from(hardLine).length) {
        anyUnknown = true;
      }
      advance = Math.max(advance, piece);
    }
    if (anyUnknown) {
      measured = false;
    }
    let width = advance * candidate.size;
    let longest = 0;
    let longestIndex = 0;
    hardLines.forEach((hardLine, index) => {
      const length = Array.from(hardLine).length;
      if (length > longest) {
        longest = length;
        longestIndex = index;
      }
    });
    width += Math.max(0, longest - 1) * candidate.tracking * candidate.size;

    /*
     * 断行上限按**可用宽度**算，不再直接用「原文最长行的字数」。
     *
     * 用原文最长行当上限时，作者没手动断行的长段落会原样留下一整行，而下面的
     * fits 又正是拿这些行去量的：一段其实断成两行就放得下的文案会被判成
     * 「缩到下限仍放不下」。按宽度算则两头兼顾——已断好的段落每行都不超过
     * 这个上限（取档正是因为它们放得下才被接受），因此保持原样；没断行的
     * 长段落才会在这里被均衡地断开。
     */
    const limit = charsPerLine(measure, candidate.size, availableWidth, hardLines[longestIndex]);
    if (width <= availableWidth) {
      level = candidate;
      lines = balance(raw, limit);
      break;
    }
    if (i >= minIndex) {
      /*
       * 已经到正文下限：不再往下缩。
       * 旧实现的条件是 `candidate.size <= minPx`，而 SCALE 往下第一个满足它的是
       * label(34px) —— 于是溢出的文案会被缩到 34px，比规范写死的 36px 下限还小，
       * 而且 fits 的判断又挂在同一个条件上，结果连「放不下」都不报。
       */
      level = candidate;
      lines = balance(raw, limit);
      break;
    }
  }
  if (!level) {
    const last = SCALE[SCALE.length - 1];
    level = last;
    lines = balance(raw, Array.from(raw).length);
  }

  /*
   * fits 一律按**断行之后的实际行宽**判定，不挂在「是否触到下限」上：
   * 触到下限不等于放不下（断行之后可能正好放得下），没触到下限也不等于放得下。
   */
  let widest = 0;
  for (const line of lines) {
    widest = Math.max(widest, measure(line) * level.size);
  }
  const fits = widest <= availableWidth;
  return result(level, lines, lines.length, measured, fits, fits ? null : 'overflows-at-min-size');
}

/**
 * 取档入口：**未启用预设时不取档**。
 *
 * 旧路径里这件事由「共享页面只在预设生效时才调用 `autofit`」保证，
 * 是一条接线纪律；接错线的症状是未启用预设的既有作品**字号整体变了一档**，
 * 而校验、渲染、成片全部照常通过。
 *
 * 这里把纪律变成函数：调用方必须把那一幕的 `visual.preset` 原样传进来，
 * 没有预设就拿不到结果，只能按组件自己的字号兜底。
 *
 * 组件仍须把结果写成 `data-a2v-fit` 属性：那是量测与体检读取「这一档是什么」
 * 的锚点，改名会让闸门**静默跳过**这一处（不是报错）。
 */
export function fitForPreset(
  preset: string | undefined,
  options: FitOptions,
): FitResult | null {
  if (preset !== 'keynote') {
    return null;
  }
  return fit(options);
}
