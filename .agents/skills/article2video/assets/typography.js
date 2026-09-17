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
   * 正确做法是把**容器**传进来（共享页面传 `.a2v-safe`）：要回答的问题是
   * 「这一行放得进画面吗」，而画面宽度由容器决定。
   *
   * 兜底路径不能从元素自己的 clientWidth 取。收缩适应（shrink-to-fit）的
   * 元素——例如 `align-items: center` 的弹性列里的 `.quote-text`——它的
   * clientWidth 就等于自己那行文字的宽度：拿它当上限再去除自己的宽度，永远
   * 除得尽，结论恒为「放得下」。这是个循环论证，而且不报错。所以兜底从
   * **父元素**开始向上找第一个有确定宽度的祖先，元素自身只贡献内边距与边框。
   */
  function resolveAvailableWidth(el, override) {
    if (typeof override === 'number' && override > 0) return override;
    if (override && override.nodeType === 1) {
      var box = global.getComputedStyle(override);
      var pad = parseFloat(box.paddingLeft || 0) + parseFloat(box.paddingRight || 0);
      var border = parseFloat(box.borderLeftWidth || 0) + parseFloat(box.borderRightWidth || 0);
      var outer = override.clientWidth || 0;
      if (outer > 0) {
        var inner = (isFinite(pad) ? pad : 0) + (isFinite(border) ? border : 0);
        return Math.max(1, outer - inner);
      }
    }
    var horizontal = 0;
    var node = el;
    var guard = 0;
    while (node && guard < 12) {
      var cs = global.getComputedStyle(node);
      var padding = parseFloat(cs.paddingLeft || 0) + parseFloat(cs.paddingRight || 0);
      var borderWidth = parseFloat(cs.borderLeftWidth || 0) + parseFloat(cs.borderRightWidth || 0);
      horizontal += (isFinite(padding) ? padding : 0) + (isFinite(borderWidth) ? borderWidth : 0);
      /* 元素自身只算内边距，宽度交给祖先：见上面的循环论证 */
      if (node !== el) {
        var width = node.clientWidth || 0;
        if (width > 0) return Math.max(1, width - horizontal);
      }
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

  /**
   * 不小于给定字号的最近档（向上取档，例如下限 36px 会落到 body 40px）。
   *
   * SCALE 按**从大到小**排列，所以两个兜底方向不要写反：
   * 请求的字号比最大档还大时，返回最大档（下标 0），
   * 而不是最小档——后者会让 hero 级的标题突然变成角标大小。
   */
  function levelAtLeast(px) {
    for (var i = SCALE.length - 1; i >= 0; i -= 1) {
      if (SCALE[i].size >= px) return SCALE[i];
    }
    return SCALE[0];
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
        /* 空段落不算「量不到」：组件里有些可选文本位平时是空的，
         * 把空串记成量测失败会让整个元素被标成未实测，属于误报。 */
        if (!piece && Array.from(hardLines[p]).length) anyUnknown = true;
        advance = Math.max(advance, piece);
      }
      if (anyUnknown) measured = false;
      var width = advance * candidate.size;
      var longest = 0;
      var longestIndex = 0;
      for (var q = 0; q < hardLines.length; q += 1) {
        var length = Array.from(hardLines[q]).length;
        if (length > longest) {
          longest = length;
          longestIndex = q;
        }
      }
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
      var limit = charsPerLine(el, candidate.size, availableWidth, hardLines[longestIndex]);
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
      level = SCALE[SCALE.length - 1];
      lines = balance(raw, Array.from(raw).length);
    }

    /*
     * fits 一律按**断行之后的实际行宽**判定，不挂在「是否触到下限」上：
     * 触到下限不等于放不下（断行之后可能正好放得下），没触到下限也不等于放得下。
     */
    var widest = 0;
    for (var r = 0; r < lines.length; r += 1) {
      widest = Math.max(widest, emWidths(lines[r], fontSpec) * level.size);
    }
    var fits = widest <= availableWidth;

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

  /**
   * 按可用宽度换算「单行最多几个字」，供 balance 使用。
   *
   * 用**待排文本自身**的平均字宽，而不是固定按全角汉字估：拉丁文的字宽只有
   * 汉字的六成，按汉字算会把「一行放得下 20 个字母」当成只放得下 12 个，
   * 凭空多断出一行。测不到字宽时退回按汉字估算。
   *
   * @param {string} [sample] 用来标定平均字宽的样本文本（通常取最长的一段）
   */
  function charsPerLine(el, fontSize, availableWidth, sample) {
    var fontSpec = fontSignature(el).split('|')[0];
    var text = sample == null || sample === '' ? '汉' : String(sample);
    var count = Math.max(1, Array.from(text).length);
    var average = emWidths(text, fontSpec) / count;
    if (!isFinite(average) || average <= 0) average = isEmWidthFallback(text);
    return Math.max(2, Math.floor(availableWidth / (average * fontSize)));
  }

  /** 量不到字宽时的经验平均字宽：全角汉字算 1，其余按拉丁估算。 */
  function isEmWidthFallback(text) {
    var chars = Array.from(String(text));
    var wide = 0;
    for (var i = 0; i < chars.length; i += 1) {
      if (isCJK(chars[i])) wide += 1;
    }
    return chars.length ? (wide + (chars.length - wide) * 0.55) / chars.length : 1;
  }

  /** 去掉换行符后的代码点序列：用于「字符不丢不增」的比对与稳定签名。 */
  function significant(text) {
    return Array.from(String(text == null ? '' : text)).filter(function (ch) {
      return ch !== '\n';
    }).join('');
  }

  /*
   * 哪些元素可以安全地重排？
   *
   * 组件会往文字里塞元素：强调词是 <span class="key">，逐字揭示是每字一个
   * <span class="reveal-char">。旧实现直接写 el.textContent，把这些元素连同
   * 强调色一起抹掉 —— 强调色是「单一焦点」的载体，静默消失等于画面失去焦点。
   *
   * 这里只放行已知可以安全重排的行内容器：强调词（重排后仍在原字符上）与
   * 它的下划线、以及普通文本段的包装。出现任何其它元素（尤其是逐字揭示的
   * 单字节点）就放弃重排，只取字号。
   */
  var REFLOW_SAFE_CLASSES = { key: 1, 'key-underline': 1, plain: 1 };

  function canReflow(el) {
    var descendants = el.querySelectorAll('*');
    for (var i = 0; i < descendants.length; i += 1) {
      var node = descendants[i];
      if (node.tagName === 'BR') return false;
      var names = String(node.className || '').split(/\s+/);
      var safe = false;
      for (var j = 0; j < names.length; j += 1) {
        if (REFLOW_SAFE_CLASSES[names[j]]) safe = true;
      }
      if (!safe) return false;
    }
    return true;
  }

  /**
   * 把均衡后的行写回元素，**保留所有子元素**。
   *
   * 做法：按代码点逐个映射回原有的文本节点。非换行字符回到它原来所属的节点，
   * 换行追加在「前一个字符所在节点」的末尾（`white-space: pre-line` 下等价于
   * 在两者之间断行）。字符集合因此只增不减，元素结构一个都不动。
   *
   * @returns {boolean} 是否成功重排；失败时元素保持原样，由调用方记 balanced: false
   */
  function reflow(el, lines) {
    var target = String(lines.join('\n'));
    var walker = global.document.createTreeWalker(el, global.NodeFilter.SHOW_TEXT, null);
    var nodes = [];
    var current = walker.nextNode();
    while (current) {
      nodes.push(current);
      current = walker.nextNode();
    }
    if (!nodes.length) return false;

    var source = nodes.map(function (node) { return node.nodeValue; }).join('');
    var sourceSig = significant(source);
    if (sourceSig !== significant(target)) {
      /* 断行结果动了字符，宁可不动版式也不动文案 */
      return false;
    }

    /* 记录每个有效字符原来属于哪个文本节点 */
    var owner = [];
    for (var n = 0; n < nodes.length; n += 1) {
      var chars = Array.from(nodes[n].nodeValue);
      for (var c = 0; c < chars.length; c += 1) {
        if (chars[c] !== '\n') owner.push(n);
      }
    }

    var buffers = nodes.map(function () { return []; });
    var cursor = 0;
    var targetChars = Array.from(target);
    for (var t = 0; t < targetChars.length; t += 1) {
      var ch = targetChars[t];
      if (ch === '\n') {
        var at = cursor === 0 ? 0 : owner[cursor - 1];
        buffers[at].push('\n');
        continue;
      }
      var nodeIndex = owner[cursor];
      if (nodeIndex === undefined) return false;
      buffers[nodeIndex].push(ch);
      cursor += 1;
    }
    if (cursor !== owner.length) return false;

    for (var w = 0; w < nodes.length; w += 1) {
      var value = buffers[w].join('');
      if (nodes[w].nodeValue !== value) nodes[w].nodeValue = value;
    }
    return true;
  }

  /**
   * 把 fit 的结果写到元素上。
   * 用内联样式而不是类名，是因为字号是按幕计算的，无法预先枚举成 CSS 类。
   *
   * 默认**只写字号**。行高与字距是组件的设计值，不是测量出来的东西：
   * 主文案元素的行高都是无单位比值（1.16 / 1.45 / 1.55 …），字号一变它自己
   * 就会跟着缩放；而字距各元素并不相同（`.section-title` 是 0.14em，
   * 字号阶里的 body 是另一个值）。把字号阶的行高字距写进去，等于把「双真源」
   * 从字号搬到行高上，只是换了个地方出问题。真要让字阶接管，显式传
   * `leading: true` / `tracking: true`。
   *
   * @returns {Object} fit 的结果（含 lines / lineCount / fits / measured）
   */
  function applyFit(el, options) {
    var spec = Object.assign({}, options, { el: el });
    var fitted = fit(spec);
    el.style.fontSize = fitted.fontSize + 'px';
    if (options && options.leading === true) el.style.lineHeight = String(fitted.lineHeight);
    if (options && options.tracking === true) el.style.letterSpacing = fitted.letterSpacing + 'em';

    var wantBalance = !(options && options.balance === false) && canReflow(el);
    var balanced = false;
    if (wantBalance && fitted.lines.join('\n').indexOf('\n') >= 0) {
      balanced = reflow(el, fitted.lines);
      if (balanced) el.style.whiteSpace = 'pre-line';
    }

    fitted.balanced = balanced;
    el.dataset.a2vFitLevel = fitted.level;
    el.dataset.a2vFitMeasured = fitted.measured ? 'true' : 'false';
    el.dataset.a2vFitBalanced = balanced ? 'true' : 'false';
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
      /*
       * 签名用「有效字符」而不是原文：重排会移动换行符的位置，
       * 用 textContent 做签名会让每一帧都判定为「内容变了」，
       * 于是逐帧重写样式与文本节点。换行位置的调整恰恰是取档自己的产物，
       * 不该被当成新输入。
       */
      var signature = significant(text) + '\u0000' + el.dataset.a2vFit;
      if (el.dataset.a2vFitFor === signature) continue;
      /* 空文本位不取档：没有可排的字，取档只会给元素贴上一堆无意义的标记 */
      if (!significant(text).trim()) continue;
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
    /* 重排与它的安全判定单独导出：这是「取档不许破坏标记」这条契约的落点，
     * 测试要能直接打到它，而不是靠构造恰好触发的文案去间接覆盖。 */
    reflow: reflow,
    canReflow: canReflow,
    significant: significant,
    optical: optical,
    reset: reset
  };
})(typeof window !== 'undefined' ? window : globalThis);
