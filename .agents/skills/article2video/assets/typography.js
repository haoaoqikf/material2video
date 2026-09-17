/*
 * article2video 排版引擎（可选）
 *
 * 解决的问题：中文视频里「一行放得下几个字」目前是靠人工试错 ——
 * 先写字、看效果、再回来改字号或手工插换行。项目里甚至沉淀过一条经验：
 * 「衬线字体下单字宽约 1.02 × 字号，14 字一行必须降到 66px」。
 * 那是量出来的结论，却只能靠人记住并手工复用；换字体、换主题、换语言就要重来一遍。
 *
 * 这一层把它变成计算：用真实测量得到的字宽，在**设计语言的字号阶**上取档，
 * 并按语义把长文本断成均衡的行。它不改变渲染契约，也不改变画面由帧号推导的性质 ——
 * 排版结果只由「文本 + 可用宽度 + 字体 + 字号阶」决定，同样的输入永远得到同样的输出。
 *
 * 降级策略：字体尚未加载或测量不可用时，取档退回「按字数与经验字宽估算」，
 * 并把结果标记为 measured: false。闸门据此报告「未实测」，而不是假装通过。
 *
 * 加载顺序：必须在 timeline.js 与 keynote.css 之后、figures.js 之前或之后均可。
 */
(function (global) {
  'use strict';

  var A2V = global.A2V;
  if (!A2V) {
    throw new Error('typography.js 需要先加载 timeline.js（A2V 未定义）');
  }

  /* 与 keynote.css 的 --a2v-size-* 一一对应。测试会对照两处，漂移即失败。 */
  var SCALE = [
    { name: 'hero', size: 140, leading: 1.06, tracking: -0.03 },
    { name: 'display', size: 120, leading: 1.1, tracking: -0.025 },
    { name: 'headline', size: 96, leading: 1.14, tracking: -0.02 },
    { name: 'title', size: 76, leading: 1.2, tracking: -0.015 },
    { name: 'lead', size: 60, leading: 1.32, tracking: -0.005 },
    { name: 'body', size: 40, leading: 1.47, tracking: 0 },
    { name: 'label', size: 34, leading: 1.4, tracking: 0.14 },
    { name: 'caption', size: 28, leading: 1.45, tracking: 0.06 }
  ];

  /* 正文下限：低于此值的文字在竖屏上不可读，规范要求「拆场景」而不是「缩字号」。
   * 引擎因此不会取到比它更小的档，而是报告 fits: false。 */
  var MIN_BODY_PX = 36;

  /* 中文标点：不参与单字宽度统计（它们本来就窄），也是断行时的语义边界。 */
  var CJK_PUNCT = '，。！？；：、）」』】》〉·…—～!?,.;:)]}\'"';
  var OPEN_PUNCT = '「『【（(《〈[{';
  /* 允许断到下一行开头的标点（避头尾：这些不能出现在行首） */
  var NO_LINE_START = '，。！？；：、）』」】》〉·…～!?,.;:)]}%';
  /* 允许留在行尾的标点（避尾：这些不能出现在行末） */
  var NO_LINE_END = '「『【（(《〈[{';

  function isCJK(ch) {
    var code = ch.codePointAt(0);
    return (
      (code >= 0x2e80 && code <= 0x9fff) ||
      (code >= 0xf900 && code <= 0xfaff) ||
      (code >= 0xff00 && code <= 0xff60) ||
      (code >= 0xffe0 && code <= 0xffe6)
    );
  }

  function fontSignature(el) {
    var cs = global.getComputedStyle(el);
    return [
      cs.fontFamily,
      cs.fontSize,
      cs.fontWeight,
      cs.fontStyle || 'normal',
      cs.fontFeatureSettings || 'normal'
    ].join('|');
  }

  /* ---------------------------------------------------------------
   * 测量：真实字宽
   *
   * 用 canvas 的 measureText 量每个字符在 100px 下的宽度，再按比例换算到
   * 任意字号。按「字体签名 + 字符」缓存，避免每帧重复测量造成截图抖动。
   * 可变字体的字重会影响宽度，因此签名里带上 fontWeight。
   * --------------------------------------------------------------- */
  var emCache = Object.create(null);
  var probe = null;

  function probeContext(font) {
    if (!probe) {
      probe = global.document.createElement('canvas');
      probe.width = 8;
      probe.height = 8;
    }
    var ctx = probe.getContext('2d');
    ctx.font = '400 100px ' + font;
    return ctx;
  }

  /**
   * 单个字符在当前字体下的「em 宽度」（字宽 / 字号）。
   * @returns {number|null} 测不到时返回 null，由调用方走估算路径
   */
  function emWidth(ch, font) {
    if (!ch) return 0;
    var key = font + '\u0000' + ch;
    if (key in emCache) return emCache[key];
    var width = null;
    try {
      var ctx = probeContext(font);
      width = ctx.measureText(ch).width / 100;
    } catch (error) {
      width = null;
    }
    if (!isFinite(width) || width <= 0) {
      /* 量不到就按经验值：汉字满宽、拉丁与数字约 0.55、标点约 0.4 */
      width = isCJK(ch) ? 1 : CJK_PUNCT.indexOf(ch) >= 0 ? 0.4 : 0.55;
    }
    emCache[key] = width;
    return width;
  }

  function emWidths(text, font) {
    var total = 0;
    var chars = Array.from(String(text == null ? '' : text));
    for (var i = 0; i < chars.length; i += 1) total += emWidth(chars[i], font);
    return total;
  }

  /**
   * 实测一段 HTML 内容的排版宽度（em 单位）。用于量出 font-size: 1em 下
   * 整句的真实宽度，从而把「拟合」变成一次除法而不是反复试排。
   * 测量期间临时禁止换行，测完立即还原。
   */
  function measureAdvance(el) {
    if (!el || !el.isConnected) return null;
    var previous = el.style.whiteSpace;
    var previousWidth = el.style.width;
    try {
      el.style.whiteSpace = 'nowrap';
      el.style.width = 'auto';
      var range = global.document.createRange();
      range.selectNodeContents(el);
      var rect = range.getBoundingClientRect();
      range.detach && range.detach();
      var advance = rect.width;
      var fontSize = parseFloat(global.getComputedStyle(el).fontSize) || 0;
      if (!advance || !fontSize) return null;
      return advance / fontSize;
    } catch (error) {
      return null;
    } finally {
      el.style.whiteSpace = previous;
      el.style.width = previousWidth;
    }
  }

  /* ---------------------------------------------------------------
   * 字号取档
   * --------------------------------------------------------------- */

  /**
   * 解析可用宽度。
   *
   * 不能用 el.getBoundingClientRect().width 当默认值：元素此刻可能是空的、
   * 且处在 align-items: center 的 flex 列里，宽度会是 0 —— 那会让取档一路
   * 掉到最小档，而且不报错。因此向上找第一个有确定宽度的祖先（通常是 .a2v-safe），
   * 再减去元素自身的水平内边距与边框。
   */
  function resolveAvailableWidth(el, override) {
    if (override) return override;
    var horizontal = 0;
    var node = el;
    var guard = 0;
    while (node && guard < 12) {
      var cs = global.getComputedStyle(node);
      var padding = parseFloat(cs.paddingLeft || 0) + parseFloat(cs.paddingRight || 0);
      var border = parseFloat(cs.borderLeftWidth || 0) + parseFloat(cs.borderRightWidth || 0);
      horizontal += (isFinite(padding) ? padding : 0) + (isFinite(border) ? border : 0);
      var width = node.clientWidth || 0;
      if (width > 0) return Math.max(1, width - horizontal);
      node = node.parentElement;
      guard += 1;
    }
    return 0;
  }

  function levelByName(name) {
    for (var i = 0; i < SCALE.length; i += 1) {
      if (SCALE[i].name === name) return SCALE[i];
    }
    return null;
  }

  /** 不小于给定字号的最近档（向上取档，例如下限 36px 会落到 body 40px） */
  function levelAtLeast(px) {
    for (var i = SCALE.length - 1; i >= 0; i -= 1) {
      if (SCALE[i].size >= px) return SCALE[i];
    }
    return SCALE[SCALE.length - 1];
  }

  function estimateLines(text, fontSize, tracking, availableWidth) {
    var font = 'sans-serif';
    var advance = emWidths(text, font) * fontSize;
    advance += Math.max(0, Array.from(String(text)).length - 1) * tracking * fontSize;
    return { lines: Math.max(1, Math.ceil(advance / availableWidth)), advance: advance };
  }

  /**
   * 为一段文本在字号阶上取档。
   *
   * @param {Object} options
   * @param {Element} options.el        参考元素（用于取字体与实测宽度）
   * @param {string}  options.text      要排版的文本（可含 \n 硬换行，硬换行优先）
   * @param {number}  [options.availableWidth] 可用宽度（px），省略则用 el 的客户区宽度
   * @param {number}  [options.maxLevel]  可接受的最大档位下标（默认 0 = hero）
   * @param {number}  [options.minPx]     可接受的最小字号（默认 36px 正文下限）
   * @param {boolean} [options.preferBalanced] 是否允许为了均衡断行而多占一行
   * @returns {{level: string, fontSize: number, lineHeight: number, letterSpacing: number,
   *            lines: Array<string>, fits: boolean, measured: boolean, reason: (string|null)}}
   */
  function fit(options) {
    var el = options.el;
    if (!el) throw new Error('typography.fit 需要 el');
    var raw = String(options.text == null ? '' : options.text);
    var maxIndex = options.maxLevel === undefined ? 0 : options.maxLevel;
    var minPx = options.minPx === undefined ? MIN_BODY_PX : options.minPx;
    var minIndex = SCALE.indexOf(levelAtLeast(minPx));

    var availableWidth = resolveAvailableWidth(el, options.availableWidth);
    if (!availableWidth || availableWidth <= 0) {
      /* 元素尚未挂载或宽度为 0：不能假装排好了 */
      var fallbackLevel = SCALE[Math.max(maxIndex, minIndex)];
      return result(fallbackLevel, raw, 1, false, false, 'no-width');
    }

    var fontSpec = fontSignature(el).split('|')[0];
    var hardLines = raw.split('\n');

    /* 从最大档往下试，取第一个放得下的档。 */
    var level = null;
    var lines = null;
    var measured = true;
    for (var i = maxIndex; i < SCALE.length; i += 1) {
      var candidate = SCALE[i];
      /* 硬换行必须保留：逐段落算，取最长段 */
      var advance = 0;
      var anyUnknown = false;
      for (var p = 0; p < hardLines.length; p += 1) {
        var piece = emWidths(hardLines[p], fontSpec);
        if (!piece) anyUnknown = true;
        advance = Math.max(advance, piece);
      }
      if (anyUnknown) measured = false;
      var width = advance * candidate.size;
      var longest = 0;
      for (var q = 0; q < hardLines.length; q += 1) {
        longest = Math.max(longest, Array.from(hardLines[q]).length);
      }
      width += Math.max(0, longest - 1) * candidate.tracking * candidate.size;
      if (width <= availableWidth || candidate.size <= minPx) {
        level = candidate;
        lines = balance(raw, longest);
        break;
      }
    }
    if (!level) {
      level = SCALE[SCALE.length - 1];
      lines = balance(raw, Array.from(raw).length);
    }

    /* 取到的档放不下，说明文案本身就超了：如实报告，由调用方决定拆场景。 */
    var fits = true;
    if (level.size <= minPx) {
      var widest = 0;
      for (var r = 0; r < lines.length; r += 1) {
        widest = Math.max(widest, emWidths(lines[r], fontSpec) * level.size);
      }
      fits = widest <= availableWidth;
    }

    return result(level, lines, lines.length, measured, fits, fits ? null : 'overflows-at-min-size');
  }

  function result(level, lines, lineCount, measured, fits, reason) {
    return {
      level: level.name,
      fontSize: level.size,
      lineHeight: level.leading,
      letterSpacing: level.tracking,
      lines: Array.isArray(lines) ? lines : [String(lines)],
      lineCount: lineCount,
      fits: !!fits,
      measured: !!measured,
      reason: reason || null
    };
  }

  /* ---------------------------------------------------------------
   * 均衡断行
   *
   * 规则（按优先级）：
   *   1. 显式 \n 是硬换行，永不重排；
   *   2. 末行不得只剩一个字或一个标点（孤字）；
   *   3. 标点不出现在行首（避头尾）；
   *   4. 各行字数尽量均衡，而不是「第一行塞满」。
   * --------------------------------------------------------------- */
  function isBreakOpportunity(chars, index) {
    var prev = chars[index - 1];
    var next = chars[index];
    if (next === undefined) return false;
    if (NO_LINE_START.indexOf(next) >= 0) return false;
    if (NO_LINE_END.indexOf(prev) >= 0) return false;
    if (isCJK(prev) || isCJK(next)) return true;
    return prev === ' ' || next === ' ';
  }

  /**
   * 把文本断成最多 maxCharsPerLine 字的行，行数最少且尽量均衡。
   * @param {string} text
   * @param {number} maxCharsPerLine 单行字数上限（由调用方按可用宽度换算）
   * @returns {Array<string>}
   */
  function balance(text, maxCharsPerLine) {
    var paragraphs = String(text == null ? '' : text).split('\n');
    var out = [];
    var limit = Math.max(2, Math.floor(maxCharsPerLine) || 2);
    for (var p = 0; p < paragraphs.length; p += 1) {
      var chars = Array.from(paragraphs[p]);
      if (!chars.length) {
        out.push('');
        continue;
      }
      var lineCount = Math.max(1, Math.ceil(chars.length / limit));
      /* 均衡目标：每行 ceil(总数/行数)。断点在该目标附近寻找语义位置。 */
      var target = Math.ceil(chars.length / lineCount);
      var start = 0;
      for (var line = 0; line < lineCount; line += 1) {
        var remainingLines = lineCount - line;
        var remainingChars = chars.length - start;
        if (remainingLines === 1) {
          out.push(chars.slice(start).join(''));
          break;
        }
        /* 末行至少要留两个字，避免孤字 */
        var minTake = Math.max(2, remainingChars - limit * (remainingLines - 1));
        var maxTake = Math.min(limit, remainingChars - 2 * (remainingLines - 1));
        if (maxTake < minTake) maxTake = minTake;
        var ideal = Math.round(remainingChars / remainingLines);
        var take = -1;
        /* 先向后找（宁可略长，避免把标点甩到下一行行首），再向前找 */
        for (var ahead = 0; ahead <= 3 && take < 0; ahead += 1) {
          var candidate = Math.min(maxTake, ideal + ahead);
          if (candidate >= minTake && candidate < remainingChars && isBreakOpportunity(chars, start + candidate)) {
            take = candidate;
          }
        }
        for (var behind = 1; behind <= 3 && take < 0; behind += 1) {
          var back = ideal - behind;
          if (back >= minTake && isBreakOpportunity(chars, start + back)) take = back;
        }
        if (take < 0) take = Math.min(maxTake, Math.max(minTake, ideal));
        out.push(chars.slice(start, start + take).join(''));
        start += take;
      }
    }
    return out;
  }

  /** 按可用宽度换算「单行最多几个字」，供 balance 使用。 */
  function charsPerLine(el, fontSize, availableWidth) {
    var fontSpec = fontSignature(el).split('|')[0];
    var em = emWidths('汉', fontSpec) || 1;
    return Math.max(2, Math.floor(availableWidth / (em * fontSize)));
  }

  /**
   * 把 fit 的结果写到元素上。
   * 用内联样式而不是类名，是因为字号是按幕计算的，无法预先枚举成 CSS 类。
   * @returns {Object} fit 的结果（含 lines / lineCount / fits / measured）
   */
  function applyFit(el, options) {
    var spec = Object.assign({}, options, { el: el });
    var fitted = fit(spec);
    el.style.fontSize = fitted.fontSize + 'px';
    el.style.lineHeight = String(fitted.lineHeight);
    el.style.letterSpacing = fitted.letterSpacing + 'em';
    if (options && options.balance !== false) {
      el.textContent = fitted.lines.join('\n');
      el.style.whiteSpace = 'pre-line';
    }
    el.dataset.a2vFitLevel = fitted.level;
    el.dataset.a2vFitMeasured = fitted.measured ? 'true' : 'false';
    return fitted;
  }

  /* ---------------------------------------------------------------
   * 光学修正：行首标点悬挂
   *
   * 中文排版里以「「」『』（（ 开头的一行，标点会明显把正文推右。
   * 把标点向左拉出文本块，是「看起来对齐」与「数学上对齐」的差别。
   * --------------------------------------------------------------- */
  var HANG_RATIO = { '「': 0.5, '『': 0.5, '（': 0.5, '(': 0.5, '【': 0.5, '《': 0.5, '〈': 0.5, '“': 0.5, '"': 0.25, '‘': 0.5 };

  function optical(el) {
    if (!el) return 0;
    var first = String(el.textContent || '').charAt(0);
    var ratio = HANG_RATIO[first];
    if (!ratio) {
      el.style.textIndent = '';
      return 0;
    }
    var fontSize = parseFloat(global.getComputedStyle(el).fontSize) || 0;
    var offset = -ratio * fontSize;
    el.style.textIndent = offset + 'px';
    return offset;
  }

  /* ---------------------------------------------------------------
   * 声明式拟合入口
   *
   * 组件画完之后调用一次：扫描 [data-a2v-fit]，按声明的角色（字号档上限）
   * 逐元素取档。**只在内容签名变化时重算**，因此每帧调用也只是几次字符串比较，
   * 不会在逐帧截图里制造抖动或拖慢渲染。
   *
   * 元素上的声明：
   *   data-a2v-fit="headline"   可选上限档位（hero/display/headline/title/lead/body/label/caption）
   *   data-a2v-fit-min="40"     可选字号下限（px）
   * --------------------------------------------------------------- */
  function maxLevelIndex(name) {
    if (!name) return 0;
    for (var i = 0; i < SCALE.length; i += 1) {
      if (SCALE[i].name === name) return i;
    }
    return 0;
  }

  function autofit(root, options) {
    var scope = root || global.document;
    var nodes = scope.querySelectorAll('[data-a2v-fit]');
    var applied = [];
    for (var i = 0; i < nodes.length; i += 1) {
      var el = nodes[i];
      var text = el.textContent || '';
      var signature = text + '\u0000' + el.dataset.a2vFit;
      if (el.dataset.a2vFitFor === signature) continue;
      var fitted = applyFit(el, {
        text: text,
        maxLevel: maxLevelIndex(el.dataset.a2vFit),
        minPx: el.dataset.a2vFitMin ? parseFloat(el.dataset.a2vFitMin) : undefined,
        availableWidth: (options && options.availableWidth) || 0,
        balance: !(options && options.balance === false)
      });
      el.dataset.a2vFitFor = signature;
      applied.push({ el: el, fitted: fitted });
    }
    return applied;
  }

  /** 供调试与文档对照：当前字号阶的快照。 */
  function scale() {
    return SCALE.map(function (item) {
      return {
        name: item.name,
        size: item.size,
        leading: item.leading,
        tracking: item.tracking
      };
    });
  }

  /** 清空宽度缓存（换字体后调用；正常渲染流程不需要） */
  function reset() {
    emCache = Object.create(null);
    probe = null;
  }

  A2V.type = {
    scale: scale,
    levels: SCALE,
    minBodyPx: MIN_BODY_PX,
    emWidth: emWidth,
    emWidths: emWidths,
    measureAdvance: measureAdvance,
    charsPerLine: charsPerLine,
    levelAtLeast: levelAtLeast,
    fit: fit,
    applyFit: applyFit,
    autofit: autofit,
    balance: balance,
    optical: optical,
    reset: reset
  };
})(typeof window !== 'undefined' ? window : globalThis);
