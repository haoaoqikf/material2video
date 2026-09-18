/**
 * 视觉组件库：把「一幕画面」做成可复用、可选择的组件。
 *
 * 为什么要它：让 AI 做导演而不是设计师——从目录里挑一个组件、给几段短标注、
 * 指定一个节奏，而不是每次从零画一遍。页面只声明挂载点：
 *
 *   <section data-a2v-scene data-scene-id="fear-source">
 *     <div class="a2v-safe" data-a2v-figure></div>
 *   </section>
 *
 * 组件契约（与 references/render-contract.md 一致）：
 *   - `update(state, api)` 必须是 (帧, 组件) 的纯函数：同一帧永远给出同一棵 DOM；
 *   - 组件自带 DOM（markup），页面不写任何图形元素；
 *   - 所有文案来自分镜的 data 与 labels（由 renderScene 解析后传入），组件不保存默认文案；
 *   - 几何由常量与 params 推导，不读实时布局；测量只在构建后做一次并缓存；
 *   - 禁止 Date.now / performance.now / Math.random，禁止 CSS animation / transition。
 *
 * 依赖 timeline.js（提供 A2V 与动效原语），必须在它之后加载。
 */
(function (global) {
  'use strict';

  var A2V = global.A2V;
  if (!A2V) {
    throw new Error('figures.js 必须在 timeline.js 之后加载：它复用 A2V 的动效原语');
  }

  /* ---------------- 动效曲线：只走三条 ---------------- */
  var SVG_NS = 'http://www.w3.org/2000/svg';

  /* 时间只走三条曲线：出场 outQuint、双向变化 inOutCubic、逐项门控 outCubic。
     混用更多曲线会让画面显得杂，详见 references/visual-spec.md。 */
  var EASE_OUT = 'outQuint';
  var EASE_SOFT = 'outCubic';
  var EASE_SYMMETRIC = 'inOutCubic';

  /* 数字滚动的最少步数。
   *
   * 低于这个步数，滚动读不出"在滚动"，只读得出"跳了一下"——而跳的那一下
   * 显示的是一个**不是最终值**的数字。实测数字幕（value: 1，180 帧）：
   * 第 15–23 帧，350px 的强调色数字以最高 0.86 的不透明度显示 **"0"**，
   * 第 24 帧跳成 "1"。那一幕讲的正是一"只保留 1 个"，先显示 0 是错的。
   *
   * 10 步是"读得出在数数"的下限：滚动时长约为幕长的 26%（1.5–2s），
   * 10 步约合 5–7 步/秒。滚动**不足 10 步就不滚**，直接显示最终值，
   * 位移与淡入交给弹簧入场——它本来就在做这件事，不需要数字再"帮忙"。 */
  var ROLL_MIN = 10;

  /*
   * 动效配方由运行时提供（timeline.js 的 A2V.motion）：入场用哪条曲线、
   * 弹性多大、什么时候收敛、常驻微动多快，都写在那一处。
   * 组件只声明「这是什么元素、移动多远」——手感参数散在六个组件里就没法整体调。
   */
  var motion = A2V.motion;

  /** 按帧号取「场景内的某个进度点」：比例而非绝对帧，且随该幕节奏缩放。 */
  function beat(state, fraction) {
    return motion.beat(state, fraction);
  }

  /* ---------------- 文字与 DOM 工具 ---------------- */
  function escapeHtml(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /**
   * 把分镜里的重点短语包成强调样式。
   * 只替换第一处出现，避免同一短语在句中多处被点亮而分散注意力。
   * underline 为 true 时额外挂一条按帧画出的底横线（金句幕用）。
   */
  function emphasize(text, phrases, underline) {
    var html = escapeHtml(text);
    (phrases || []).forEach(function (phrase) {
      var safe = escapeHtml(phrase);
      if (safe && html.indexOf(safe) !== -1) {
        html = html.replace(
          safe,
          '<span class="key">' + safe + (underline ? '<span class="key-underline"></span>' : '') + '</span>'
        );
      }
    });
    return html;
  }

  /** 文本类场景的统一写法：内容来自分镜，样式类由页面决定。 */
  function setText(node, value, emphasis, underline) {
    if (!node) {
      return;
    }
    var next = emphasize(value, emphasis, underline);
    if (node.innerHTML !== next) {
      node.innerHTML = next;
    }
  }

  /** 给 SVG 元素写 transform 属性（SVG 用属性而不是 CSS 变量，避免布局抖动）。 */
  function svgT(node, tx, ty, rotate, scale) {
    if (!node) {
      return;
    }
    var value = 'translate(' + tx.toFixed(2) + ' ' + ty.toFixed(2) + ')';
    if (rotate) {
      value += ' rotate(' + rotate.toFixed(4) + ')';
    }
    if (scale !== undefined && scale !== null) {
      value += ' scale(' + scale.toFixed(4) + ')';
    }
    node.setAttribute('transform', value);
  }

  function svgO(node, value) {
    if (node) {
      node.setAttribute('opacity', String(value < 0 ? 0 : value > 1 ? 1 : value));
    }
  }

  function svgEl(name, attrs) {
    var node = document.createElementNS(SVG_NS, name);
    Object.keys(attrs || {}).forEach(function (key) {
      node.setAttribute(key, attrs[key]);
    });
    return node;
  }

  function clearNode(node) {
    while (node && node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  /** 只在内容变化时重建结构：签名一致就跳过，保证同一帧永远得到同一棵 DOM。 */
  function buildOnce(host, signature, build) {
    if (!host || host.dataset.built === signature) {
      return false;
    }
    host.dataset.built = signature;
    clearNode(host);
    build(host);
    return true;
  }

  /**
   * HTML 元素的入场 + 常驻微动。
   *
   * 具体配方（弹性、收敛时机、呼吸幅度）由运行时的 A2V.motion 决定；
   * 这里只保留组件侧的调用形状，五个组件都走同一条路径，手感才不会各自漂移。
   *
   * `seconds` 是距入场起点的秒数（api.since），不是 0..1 的进度：
   * 弹簧本身就是曲线，喂给它一条已经缓动过的进度，它的自然周期就失去意义。
   */
  function enterAlive(state, api, el, seconds, options) {
    motion.enter(state, el, seconds, options);
  }

  /** SVG 分组的入场（同上，但写的是 SVG transform 属性）。 */
  function enterFig(state, api, node, seconds, options) {
    motion.enterSvg(state, node, seconds, options);
  }

  /** 与运行时语义一致的钳制，避免为一个小工具再暴露一层接口。 */
  function clampStatic(value, min, max) {
    return value < min ? min : value > max ? max : value;
  }

  /**
   * 设计语言预设是否生效。
   *
   * CSS 侧用 `[data-a2v-preset="keynote"]` 作用域，JS 侧必须读同一个开关：
   * 「内容驱动几何」会改变画面的排版结果，如果无条件生效，就会改到
   * **未启用预设的既有作品**——而那是一条硬承诺（逐帧不变，有成片哈希与逐像素
   * 比对守着）。因此这类改动一律挂在预设上。
   */
  function presetActive() {
    var root = document.documentElement;
    return !!(root && root.getAttribute('data-a2v-preset') === 'keynote');
  }

  /** 把 chars 均衡切成 count 行：行数固定，各行的字数差不超过 1。 */
  function balanceChars(chars, count) {
    var lines = [];
    var size = Math.ceil(chars.length / count);
    for (var i = 0; i < chars.length; i += size) {
      lines.push(chars.slice(i, i + size).join(''));
    }
    return lines;
  }

  /**
   * 把一段标签装进圆形节点：**几何由内容测量结果决定**，而不是先写死半径再塞字。
   *
   * 飞轮节点原先半径 76px（直径 152px），而 `.loop-node-text` 在预设下取
   * `--a2v-ink-value` = 44px，四个汉字带字距约 183px——比直径还宽 31px，
   * 文字必然穿出圆。K7 只比安全区、且显式排除 SVG 宿主文本，所以没有任何检查
   * 会发现它；先写死容器、再放文字这个顺序本身就是缺陷。
   *
   * 判据取「矩形内接于圆」：宽 w、高 h 的文字块居中放进半径 r 的圆，
   * 需要 r ≥ sqrt((w/2)² + (h/2)²)。逐行数试算，取所需半径最小的一种装法
   * （行数相同则取行数更少的），再与最小半径取大。
   *
   * 宽度用 `getComputedTextLength()` **实测**。运行时在首次 seek 之前
   * await 过 `document.fonts.ready`，因此量到的一定是最终字体，
   * 结果逐帧可复现，不依赖时钟或随机数。
   *
   * 量不出来时（无布局、字体未就绪）返回 `measured: false` 并保留单行原文，
   * 由调用方按原样绘制——降级路径要让画面仍然成立，而不是抛错。
   */
  function fitLabelToCircle(textEl, label, minRadius, pad) {
    var text = String(label == null ? '' : label);
    var chars = Array.prototype.slice.call(text);
    if (!textEl || !chars.length) {
      return { lines: [], radius: minRadius, measured: false };
    }
    var style = window.getComputedStyle(textEl);
    var fontPx = parseFloat(style.fontSize) || 44;
    var linePx = parseFloat(style.lineHeight);
    if (!isFinite(linePx) || linePx <= 0) {
      linePx = fontPx * 1.15;
    }
    function widthOf(candidate) {
      textEl.textContent = candidate;
      try {
        return textEl.getComputedTextLength();
      } catch (error) {
        return 0;
      }
    }
    var widest = 0;
    var best = null;
    for (var count = 1; count <= chars.length; count += 1) {
      var lines = balanceChars(chars, count);
      var maxWidth = 0;
      for (var i = 0; i < lines.length; i += 1) {
        maxWidth = Math.max(maxWidth, widthOf(lines[i]));
      }
      if (!maxWidth) {
        textEl.textContent = text;
        return { lines: [text], radius: minRadius, measured: false };
      }
      widest = Math.max(widest, maxWidth);
      var blockH = lines.length * linePx;
      var needed =
        Math.sqrt(Math.pow(maxWidth / 2, 2) + Math.pow(blockH / 2, 2)) + pad;
      if (
        best === null ||
        needed < best.radius - 0.5 ||
        (Math.abs(needed - best.radius) <= 0.5 && lines.length < best.lines.length)
      ) {
        best = { lines: lines, radius: needed };
      }
      if (lines.length === 1) {
        break;
      }
    }
    textEl.textContent = text;
    return {
      lines: best.lines,
      radius: Math.max(minRadius, best.radius),
      lineHeight: linePx,
      measured: true
    };
  }

  /** 读一个自定义属性的像素值；取不到或不是正数就用兜底值。 */
  function tokenPx(el, name, fallback) {
    if (!el || !window.getComputedStyle) {
      return fallback;
    }
    var parsed = parseFloat(window.getComputedStyle(el).getPropertyValue(name));
    return isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  /** 按测量结果把标签写成单行或多行 tspan，并让整块在 (cx, cy) 上垂直居中。 */
  function paintLabelLines(textEl, layout, cx, cy) {
    clearNode(textEl);
    var lines = layout.lines || [];
    var linePx = layout.lineHeight || 0;
    lines.forEach(function (line, index) {
      var node = svgEl('tspan', { x: cx });
      if (lines.length > 1) {
        node.setAttribute('y', cy + (index - (lines.length - 1) / 2) * linePx);
      } else {
        node.setAttribute('y', cy);
      }
      node.textContent = line;
      textEl.appendChild(node);
    });
  }

  /* ---------------- 组件注册表 ---------------- */

  var KINDS = {};

  /** 注册一个组件。definition：{ labels, markup, create(ctx) -> { update } }。 */
  function register(kind, definition) {
    KINDS[kind] = definition;
  }

  function known() {
    return Object.keys(KINDS);
  }

  /** 把 src 里的 renderXxx 包装成组件：注入作用域到挂载点内的 pick。 */
  function define(kind, labels, markup, update) {
    register(kind, {
      labels: labels,
      markup: markup,
      /*
       * pick 收窄到组件自己的挂载点：组件只认识自己画的元素，
       * 即使同一页面上有多个同类组件也不会互相取错。
       *
       * 标注也从这里注入：分镜的 figure.labels 与旧的 annotations 在 renderScene
       * 合流后进 spec，组件只认这一份，不直接读分镜字段——组件自己解析字段，
       * 就会出现「换了写法但只有一部分组件跟着变」的静默错位。
       */
      create: function (ctx) {
        var host = ctx.host;
        var ann = (ctx.spec && ctx.spec.labels) || {};
        function pick(name) {
          return host.querySelector('[data-el="' + name + '"]');
        }
        return {
          update: function (state, api) {
            update(state, api, pick, ann);
          }
        };
      }
    });
  }

  /* ---------------- 01 天平 ---------------- */

  /* 几何常量：位置全部由常量算出，不读取布局，因此逐帧稳定。 */
  var SCALE = {
    PIVOT_X: 444,
    PIVOT_Y: 96,
    ARM: 300,
    TILT: -9
  };

  /** 横梁倾角 → 两个吊盘挂点的坐标（吊盘始终垂直，靠平移跟随横梁端点）。 */
  function panAnchors(theta) {
    var rad = (theta * Math.PI) / 180;
    var cos = Math.cos(rad);
    var sin = Math.sin(rad);
    return {
      left: {
        x: SCALE.PIVOT_X - SCALE.ARM * cos,
        y: SCALE.PIVOT_Y - SCALE.ARM * sin
      },
      right: {
        x: SCALE.PIVOT_X + SCALE.ARM * cos,
        y: SCALE.PIVOT_Y + SCALE.ARM * sin
      }
    };
  }

  /**
   * 开场：先把「害怕」压下去，再证明它只是个空壳。
   *
   * 天平的左盘放上「命运的考试」时明显下沉（恐惧的重量），随后那块重物变成虚线
   * 空壳、横梁弹回水平；右盘「一次上场」亮起强调色，同时标题里的「害怕」褪回墨色。
   * 颜色本身就是叙事：恐惧退场，动作上场。
   */
  function updateBalance(state, api, pick, labels) {
    var f = state.localFrame;
    var data = state.scene.data;
    var ann = labels || {};

    var title = pick('text');
    var sub1 = pick('sub1');
    var sub2 = pick('sub2');
    var lines = String(data.subtitle || '').split('\n');

    setText(title, data.text, data.emphasis, false);
    if (sub1) {
      sub1.textContent = lines[0] || '';
    }
    if (sub2) {
      sub2.textContent = lines[1] || '';
    }
    setPlainText(pick('loadLeftText'), ann.leftPan);
    setPlainText(pick('loadLeftTextHollow'), ann.leftPan);
    setPlainText(pick('loadRightText'), ann.rightPan);

    enterAlive(state, api, title,api.since(f, beat(state, 0.03)), {
      distance: 58,
      amplitude: 4
    });
    enterAlive(state, api, sub1,api.since(f, beat(state, 0.46)), {
      distance: 24,
      amplitude: 3,
      periodFrames: 150,
      phase: 20
    });
    enterAlive(state, api, sub2,api.since(f, beat(state, 0.7)), {
      distance: 24,
      amplitude: 3,
      periodFrames: 150,
      phase: 60
    });

    // 支架：立柱自下而上画出，底座与斜撑随后
    api.drawPath(pick('pillar'), api.progress(f, beat(state, 0.15), 26, EASE_OUT), { length: 276 });
    api.drawPath(pick('legL'), api.progress(f, beat(state, 0.22), 20, EASE_OUT), { length: 88 });
    api.drawPath(pick('legR'), api.progress(f, beat(state, 0.22), 20, EASE_OUT), { length: 88 });
    api.drawPath(pick('base'), api.progress(f, beat(state, 0.24), 20, EASE_OUT), { length: 160 });
    svgO(pick('pivot'), api.progress(f, beat(state, 0.24), 18, EASE_OUT));

    // 倾角：恐惧压下左盘 → 看穿空壳 → 弹回水平
    var press = api.progress(f, beat(state, 0.42), beat(state, 0.14), EASE_SYMMETRIC);
    var relief = motion.spring(api.since(f, beat(state, 0.62)), 'snap');
    var theta = SCALE.TILT * press * (1 - relief);
    var anchors = panAnchors(theta);

    var beamP = api.progress(f, beat(state, 0.25), 26, EASE_OUT);
    // 弹簧要的是线性秒数，透明度要的是 0..1 进度：同一个起点、两种输入，各自取用。
    // beamP 还要当透明度用，所以不能就地改掉它。
    var beamSeconds = api.since(f, beat(state, 0.25));
    var beamSettle = api.progress(f, beat(state, 0.7), 40, EASE_SYMMETRIC);
    var beamDrift = motion.idle(f, { amplitude: 2 }) * beamSettle;
    svgT(
      pick('beam'),
      SCALE.PIVOT_X,
      SCALE.PIVOT_Y + beamDrift,
      theta,
      api.range(motion.spring(beamSeconds, 'firm'), 0.55, 1, { clamp: false })
    );
    svgO(pick('beam'), beamP);

    // 吊盘：跟着横梁端点平移，落位后保持垂直
    var panP = motion.spring(api.since(f, beat(state, 0.28)), 'firm');
    var panSettle = api.progress(f, beat(state, 0.28), 40, EASE_SYMMETRIC);
    var dropIn = (1 - panP) * 60;
    var driftL = motion.idle(f, { amplitude: 2.4 }) * panSettle;
    var driftR = motion.idle(f, { amplitude: 2.4, phase: 50 }) * panSettle;
    svgT(pick('panLeft'), anchors.left.x, anchors.left.y + dropIn + driftL);
    svgO(pick('panLeft'), api.clamp(panP * 1.5, 0, 1));
    svgT(pick('panRight'), anchors.right.x, anchors.right.y + dropIn + driftR);
    svgO(pick('panRight'), api.clamp(panP * 1.5, 0, 1));

    // 左盘的重物落下
    var loadP = motion.spring(api.since(f, beat(state, 0.34)), 'lively');
    var loadDrop = (1 - loadP) * -170;
    var reveal = api.progress(f, beat(state, 0.54), beat(state, 0.16), EASE_SYMMETRIC);
    svgO(pick('loadLeft'), api.clamp(loadP, 0, 1));
    svgT(pick('loadLeft'), 0, loadDrop, 0, 1 - reveal * 0.06);
    svgO(pick('loadLeftSolid'), 1 - reveal);
    svgO(pick('loadLeftHollow'), reveal);

    // 右盘的「一次上场」：轻，但它是最后亮起来的那一个
    var tokenP = motion.spring(api.since(f, beat(state, 0.3)), 'lively');
    svgO(pick('loadRight'), api.clamp(tokenP, 0, 1));
    svgT(pick('loadRight'), 0, (1 - tokenP) * -120, 0, api.range(tokenP, 0.9, 1, { clamp: false }));

    var glow = api.progress(f, beat(state, 0.66), beat(state, 0.16), EASE_SYMMETRIC);
    var halo = pick('rightHalo');
    var haloScale = api.range(glow, 0.6, 1.1, { clamp: false });
    // 光晕以自身圆心缩放，否则缩放会把圆心一起拖走
    svgT(halo, 0, 127 * (1 - haloScale), 0, haloScale);
    svgO(halo, glow * 0.85);
    var rect = pick('loadRightRect');
    if (rect) {
      // 描边颜色取主题令牌而不是写死暖红：写死的颜色不跟主题走，
      // 只换主题时会原地留一抹红。alpha 逐帧来自 glow，仍由本帧决定。
      rect.setAttribute(
        'stroke',
        'color-mix(in srgb, var(--a2v-accent-deep) ' + Math.round((0.28 + 0.62 * glow) * 100) + '%, transparent)'
      );
    }
    // 文字用内联 style 而不是 SVG 属性：CSS 类会盖过表现属性，属性写不进去
    var tokenText = pick('loadRightText');
    if (tokenText) {
      tokenText.style.fill =
        'color-mix(in srgb, var(--a2v-accent-deep) ' + Math.round(api.range(glow, 28, 100)) + '%, #4a4a4a)';
    }

    // 标题里的「害怕」随空壳一起褪色：恐惧退场，动作上场。
    //
    // 颜色写成**自定义属性**而不是 `color`：行内样式的优先级高于任何样式表规则，
    // 直接写 `style.color` 会让设计语言层永远覆盖不了这个元素（表现是
    // 「预设改了强调色，只有这一处不变」）。自定义属性最后由样式表决定怎么用，
    // 组件仍然掌握「什么时候褪、褪到哪一档」。两套主题各自的落点见 keynote.css。
    var key = title ? title.querySelector('.key') : null;
    if (key) {
      var cool = api.progress(f, beat(state, 0.62), beat(state, 0.16), EASE_SYMMETRIC);
      key.style.setProperty('--a2v-emphasis-mix', api.range(cool, 0, 1).toFixed(4));
    }
  }

  function setPlainText(node, value) {
    if (node) {
      node.textContent = value == null ? '' : String(value);
    }
  }

  /** balance 的画面结构：文案元素留空，由分镜注入。 */
  var MARKUP_BALANCE = `<h1 class="title-text" data-el="text" data-a2v-fit="display"></h1>
<p class="title-sub">
  <span class="title-sub-line" data-el="sub1"></span>
  <span class="title-sub-line" data-el="sub2"></span>
</p>
<!-- 天平：恐惧把「命运的考试」压下去，随后证明它只是个空壳 -->
<svg class="fig fig-scale" viewBox="0 0 888 430" aria-hidden="true">
  <defs>
    <radialGradient id="scale-halo">
      <stop offset="0" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 45%, transparent)"></stop>
      <stop offset="1" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"></stop>
    </radialGradient>
  </defs>
  <path class="ln" data-el="pillar" d="M444 372 L444 96"></path>
  <path class="ln" data-el="legL" d="M444 368 L364 404"></path>
  <path class="ln" data-el="legR" d="M444 368 L524 404"></path>
  <path class="ln" data-el="base" d="M364 404 L524 404"></path>
  <circle class="scale-pivot" data-el="pivot" cx="444" cy="96" r="13"></circle>
  <g data-el="beam">
    <path class="ln" d="M-300 0 L300 0"></path>
  </g>
  <g data-el="panLeft">
    <path class="scale-rope" d="M0 0 L0 168"></path>
    <path class="scale-plate" d="M-130 168 L130 168 L110 198 L-110 198 Z"></path>
    <g data-el="loadLeft">
      <g data-el="loadLeftSolid">
        <rect class="load-solid" x="-116" y="52" width="232" height="116" rx="16"></rect>
        <text class="load-text" data-el="loadLeftText" x="0" y="112"></text>
      </g>
      <g data-el="loadLeftHollow">
        <rect class="load-hollow" x="-116" y="52" width="232" height="116" rx="16"></rect>
        <text class="load-text is-ink" data-el="loadLeftTextHollow" x="0" y="112"></text>
      </g>
    </g>
  </g>
  <g data-el="panRight">
    <circle class="scale-halo" data-el="rightHalo" cx="0" cy="127" r="118"></circle>
    <path class="scale-rope" d="M0 0 L0 168"></path>
    <path class="scale-plate" d="M-130 168 L130 168 L110 198 L-110 198 Z"></path>
    <g data-el="loadRight">
      <rect class="load-token a2v-surface" data-a2v-state="focus" data-el="loadRightRect" x="-84" y="86" width="168" height="82" rx="14"></rect>
      <text class="load-text is-ink" data-el="loadRightText" x="0" y="128"></text>
    </g>
  </g>
</svg>`;

  define('balance', ["leftPan", "rightPan"], MARKUP_BALANCE, updateBalance);

  /* ---------------- 02 落差尺 ---------------- */

  var TRACK_H = 268;

  /**
   * 金句：把「失去」画成一截可测量的落差。
   *
   * 左边先演一遍恐惧的剧本——拥有、被拿走、落差拉满；右边才是事实：柱子里本来就
   * 没有东西，括号塌成一条贴着 0 的短线。两栏共用同一把竖尺，观众可以自己比。
   */
  function updateGap(state, api, pick, labels) {
    var f = state.localFrame;
    var data = state.scene.data;
    var ann = labels || {};
    var text = pick('text');
    var rule = pick('rule');
    var mark = pick('mark');

    setText(text, data.text, data.emphasis, true);
    setPlainText(pick('capA'), ann.assumption);
    setPlainText(pick('capB'), ann.fact);
    setPlainText(pick('labelA'), ann.dropLabel);
    setPlainText(pick('labelB'), ann.noDropLabel);

    if (rule) {
      var ruleP = api.progress(f, 0, 20, EASE_OUT);
      rule.style.transform = 'scaleY(' + ruleP.toFixed(4) + ')';
      rule.style.opacity = String(ruleP);
    }
    if (mark) {
      var markP = api.progress(f, beat(state, 0.02), 24, EASE_OUT);
      mark.style.opacity = String(markP * 0.14);
      mark.style.transform = 'translateY(' + api.range(markP, -26, 0).toFixed(1) + 'px)';
    }

    enterAlive(state, api, text,api.since(f, beat(state, 0.04)), {
      distance: 50,
      amplitude: 3
    });
    enterAlive(state, api, pick('panelA'),api.since(f, beat(state, 0.16)), {
      distance: 40,
      amplitude: 2.5,
      phase: 0
    });
    enterAlive(state, api, pick('panelB'),api.since(f, beat(state, 0.22)), {
      distance: 40,
      amplitude: 2.5,
      phase: 40
    });

    // 左边：拥有 → 被拿走 → 落差拉满
    var ownP = api.progress(f, beat(state, 0.26), beat(state, 0.09), EASE_OUT);
    var dropP = api.progress(f, beat(state, 0.38), beat(state, 0.08), EASE_SYMMETRIC);
    var aFill = ownP * (1 - dropP);
    var aGhost = ownP;
    applyDrop(pick('fillA'), aFill);
    applyDrop(pick('ghostA'), aGhost);

    var gapP = api.progress(f, beat(state, 0.48), beat(state, 0.1), EASE_SYMMETRIC);
    placeBracket(pick('bracketA'), pick('labelA'), aFill, (aGhost - aFill) * gapP, false);

    // 右边：本来就没有，所以没有可失去的
    applyDrop(pick('fillB'), 0);
    applyDrop(pick('ghostB'), 0);
    var flatP = api.progress(f, beat(state, 0.56), beat(state, 0.1), EASE_SYMMETRIC);
    var bracketB = pick('bracketB');
    var labelB = pick('labelB');
    placeBracket(bracketB, labelB, 0, flatP * 0.012, true);
    if (bracketB) {
      bracketB.style.opacity = String(flatP);
    }
    if (labelB) {
      labelB.style.opacity = String(flatP);
    }

    // 左边淡出为「假设」：它只是观众脑内的剧本，不是事实
    var panelA = pick('panelA');
    if (panelA) {
      var fade = api.progress(f, beat(state, 0.54), beat(state, 0.14), EASE_SYMMETRIC);
      panelA.style.opacity = String(1 - fade * 0.55);
    }

    // 关键短语：底横线在句子读完后画出，颜色同步加深
    emphasizeKey(state, api, text);
  }

  /**
   * 关键短语的强调：底横线在句子读完后画出，同步加深颜色与光晕。
   *
   * 抽出来是因为「正文 + 图形」这类组件都要它，各写一份必然会有一处忘记
   * 把底横线一起画出来——那种缺失在成片里只是一条线没出现，很难被发现。
   */
  function emphasizeKey(state, api, node, options) {
    var o = options || {};
    var key = node ? node.querySelector('.key') : null;
    if (!key) {
      return;
    }
    var at = o.at === undefined ? 0.7 : o.at;
    var span = o.span === undefined ? 0.1 : o.span;
    var p = api.progress(state.localFrame, beat(state, at), beat(state, span), EASE_SYMMETRIC);
    var underline = key.querySelector('.key-underline');
    if (underline) {
      underline.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    }
    key.style.textShadow =
      '0 0 ' + api.range(p, 0, o.glow === undefined ? 26 : o.glow).toFixed(1) + 'px rgba(var(--a2v-accent-rgb), ' +
      api.range(p, 0, o.alpha === undefined ? 0.22 : o.alpha).toFixed(3) + ')';
  }

  /** 竖尺填充：高度按比例写，圆角底部保持贴地。 */
  function applyDrop(node, ratio) {
    if (node) {
      node.style.height = (clampStatic(ratio, 0, 1) * TRACK_H).toFixed(1) + 'px';
    }
  }

  /**
   * 落差括号：从「现在还剩多少」量到「曾经有多少」。
   * flat 为真时（本来就没有）把括号压成贴着 0 线的一小段，标签跟在它右边，
   * 这样「失去全部」和「无可失去」在同一把尺上可以直接比长度。
   */
  function placeBracket(bracket, label, fillRatio, gapRatio, flat) {
    var top = clampStatic(fillRatio, 0, 1) * TRACK_H;
    var height = clampStatic(gapRatio, 0, 1) * TRACK_H;
    if (flat) {
      top = TRACK_H - 6;
      height = 6;
    }
    if (bracket) {
      bracket.style.top = top.toFixed(1) + 'px';
      bracket.style.height = height.toFixed(1) + 'px';
    }
    if (label) {
      var center = flat ? TRACK_H : top + height / 2;
      label.style.top = (clampStatic(center, 44, TRACK_H - 16) - 20).toFixed(1) + 'px';
    }
  }

  /** gap 的画面结构：文案元素留空，由分镜注入。 */
  var MARKUP_GAP = `<div class="quote-block">
  <span class="quote-mark" data-el="mark">&ldquo;</span>
  <span class="quote-rule" data-el="rule"></span>
  <p class="quote-text" data-el="text" data-a2v-fit="lead"></p>
</div>
<!-- 落差尺：左边是「先拥有再被拿走」，右边是「本来就没有」 -->
<div class="drop-board">
  <div class="drop-panel" data-el="panelA">
    <div class="drop-cap" data-el="capA"></div>
    <div class="drop-stage">
      <div class="drop-track">
        <span class="drop-ghost" data-el="ghostA"></span>
        <span class="drop-fill" data-el="fillA"></span>
        <span class="drop-zero"></span>
      </div>
      <div class="drop-bracket-wrap">
        <span class="drop-bracket" data-el="bracketA"></span>
        <span class="drop-label" data-el="labelA"></span>
      </div>
    </div>
  </div>
  <div class="drop-panel is-fact" data-el="panelB">
    <div class="drop-cap" data-el="capB"></div>
    <div class="drop-stage">
      <div class="drop-track">
        <span class="drop-ghost" data-el="ghostB"></span>
        <span class="drop-fill" data-el="fillB"></span>
        <span class="drop-zero"></span>
      </div>
      <div class="drop-bracket-wrap">
        <span class="drop-bracket is-flat" data-el="bracketB"></span>
        <span class="drop-label is-flat" data-el="labelB"></span>
      </div>
    </div>
  </div>
</div>`;

  define('gap', ["assumption", "fact", "dropLabel", "noDropLabel"], MARKUP_GAP, updateGap);

  /* ---------------- 双栏对照 ---------------- */

  /**
   * 两种反应 / 两条路：左栏是现状，右栏是该转去的方向，中间用箭头连起来。
   *
   * 为什么不做成「左右对称」：对称只说明「有两个选项」，而这类内容想说的是
   * 「从左边转向右边」。箭头承担了这句话，右栏的强调色只是把落点标出来。
   */
  function updateVersus(state, api, pick, labels) {
    var f = state.localFrame;
    var data = state.scene.data;
    var ann = labels || {};

    setPlainText(pick('title'), data.title);
    // 对照的两句话优先取分镜的 left / right（comparison 场景的正式字段），
    // 其他场景类型（例如 quote + versus）没有这两个字段，就退回标注
    setPlainText(pick('leftText'), data.left || ann.left);
    setPlainText(pick('rightText'), data.right || ann.right);
    setPlainText(pick('note'), ann.note);

    // 引子：论点是「不是 A，而是 B」时，正文先立起来，两栏才是它的注解。
    // comparison 场景没有 text，这一段整个不占位。
    var lead = pick('lead');
    if (lead) {
      setText(pick('leadText'), data.text, data.emphasis, true);
      lead.style.display = data.text ? '' : 'none';
    }

    enterAlive(state, api, lead,api.since(f, beat(state, 0.02)), {
      distance: 48,
      amplitude: 3
    });
    enterAlive(state, api, pick('title'),api.since(f, beat(state, 0.03)), {
      distance: 44,
      amplitude: 3
    });
    enterAlive(state, api, pick('leftSide'),api.since(f, beat(state, 0.16)), {
      distance: -46,
      axis: 'x',
      amplitude: 2.2
    });
    enterAlive(state, api, pick('rightSide'),api.since(f, beat(state, 0.24)), {
      distance: 46,
      axis: 'x',
      amplitude: 2.2,
      phase: 40
    });

    // 箭头：先长出来，再点亮右栏
    var line = pick('line');
    if (line) {
      var lineP = api.progress(f, beat(state, 0.4), beat(state, 0.1), EASE_SYMMETRIC);
      line.style.transform = 'scaleX(' + lineP.toFixed(4) + ')';
    }
    var head = pick('head');
    if (head) {
      head.style.opacity = String(api.progress(f, beat(state, 0.46), 12, EASE_OUT));
    }

    var heat = api.progress(f, beat(state, 0.52), beat(state, 0.14), EASE_SYMMETRIC);
    var rightSide = pick('rightSide');
    if (rightSide) {
      // 用自定义属性而不是再写一次 opacity：入场动画刚写过 opacity，
      // 覆盖它会让入场在末段跳一下
      rightSide.style.setProperty('--vs-heat', heat.toFixed(3));
    }
    var note = pick('note');
    if (note) {
      note.style.opacity = String(api.progress(f, beat(state, 0.62), 20, EASE_OUT) * 0.9);
    }
    emphasizeKey(state, api, lead, { at: 0.72, glow: 22, alpha: 0.18 });
  }

  var MARKUP_VERSUS = `<div class="quote-block" data-el="lead">
  <span class="quote-mark" data-el="mark">&ldquo;</span>
  <span class="quote-rule" data-el="rule"></span>
  <p class="quote-text" data-el="leadText" data-a2v-fit="lead"></p>
</div>
<h2 class="section-title" data-el="title" data-a2v-fit="title"></h2>
<div class="vs-board">
  <div class="vs-side is-left" data-el="leftSide">
    <p class="vs-text" data-el="leftText"></p>
  </div>
  <div class="vs-link" aria-hidden="true">
    <span class="vs-line" data-el="line"></span>
    <span class="vs-head" data-el="head"></span>
  </div>
  <div class="vs-side is-right" data-el="rightSide">
    <p class="vs-text" data-el="rightText"></p>
  </div>
</div>
<p class="vs-note" data-el="note" data-a2v-fit="caption"></p>`;

  define('versus', ["left", "right", "note"], MARKUP_VERSUS, updateVersus);

  /* ---------------- 03 冰山 ---------------- */

  var BERG = {
    CALLOUT_X: 452,
    CALLOUT_W: 428,
    CALLOUT_H: 132,
    CALLOUT_Y: [84, 316, 548],
    TARGETS: [
      { x: 300, y: 172 },
      { x: 300, y: 384 },
      { x: 344, y: 566 }
    ]
  };

  /**
   * 恐惧来源：把「失去」和「被看见的不足」放进同一座冰山。
   *
   * 水面之上那个小三角是能被说出口的那部分恐惧；真正压着人的那一大团在水下，
   * 直到一束光扫过去才显形——而光扫过之后，从水里升起的东西才是「变强」。
   */
  function updateIceberg(state, api, pick, labels) {
    var f = state.localFrame;
    var data = state.scene.data;
    var ann = labels || {};
    var items = data.items || [];

    setPlainText(pick('title'), data.title);
    setPlainText(pick('surfaceNote'), ann.surface);

    buildOnce(pick('callouts'), JSON.stringify([items, ann]), function (host) {
      items.forEach(function (item, index) {
        var entry = typeof item === 'string' ? { label: item } : item;
        var isAccent = index === items.length - 1;
        var y = BERG.CALLOUT_Y[index];
        var target = BERG.TARGETS[index];
        var group = svgEl('g', { 'data-callout': String(index) });

        var link = svgEl('path', {
          class: 'berg-link' + (isAccent ? ' is-accent' : ''),
          d:
            'M' + BERG.CALLOUT_X + ' ' + (y + BERG.CALLOUT_H / 2) +
            ' C ' + (BERG.CALLOUT_X - 44) + ' ' + (y + BERG.CALLOUT_H / 2) +
            ', ' + (target.x + 70) + ' ' + target.y +
            ', ' + target.x + ' ' + target.y
        });
        group.appendChild(link);

        group.appendChild(
          svgEl('rect', {
            /* 焦点标注的表面走基元 + 状态，而不是临场的 `.is-accent`。
             * 原先 `.berg-callout.is-accent` 只把描边换成 2px、50% 透明的强调色——
             * 折算到判据图上细到几乎量不到，画面里也读不出"这一块是重点"。
             * 现在由 `focus` 态给表面一个克制的强调色填充（`--a2v-accent-soft-solid`），
             * 描边同时换成不透明的强调色；标签仍是强调色（`.is-accent` 保留），
             * 于是"填充定焦点、文字说清是什么"。 */
            class: 'berg-callout a2v-surface',
            'data-a2v-state': isAccent ? 'focus' : 'rest',
            x: BERG.CALLOUT_X,
            y: y,
            width: BERG.CALLOUT_W,
            height: BERG.CALLOUT_H,
            rx: 28
          })
        );

        var label = svgEl('text', {
          class: 'berg-callout-label' + (isAccent ? ' is-accent' : ''),
          x: BERG.CALLOUT_X + 32,
          y: y + 50
        });
        label.textContent = entry.label || '';
        group.appendChild(label);

        var desc = svgEl('text', {
          class: 'berg-callout-desc',
          x: BERG.CALLOUT_X + 32,
          y: y + 96
        });
        desc.textContent = entry.desc || '';
        group.appendChild(desc);

        host.appendChild(group);
      });
    });

    buildOnce(pick('sparks'), 'sparks', function (host) {
      // 5 颗上浮粒子：一致的小半径 + 收窄的横向抖动，读起来才是「一股上升」而不是噪点
      for (var i = 0; i < 5; i += 1) {
        host.appendChild(svgEl('circle', { class: 'berg-spark', r: 8, cx: 0, cy: 0 }));
      }
    });

    // 水面先画出来，再露出水上的一角
    api.drawPath(pick('waterLine'), api.progress(f, beat(state, 0.02), beat(state, 0.1), EASE_OUT), {
      length: 888
    });
    svgO(pick('waterBody'), api.progress(f, beat(state, 0.06), beat(state, 0.14), EASE_SYMMETRIC));
    svgO(pick('surfaceNote'), api.progress(f, beat(state, 0.1), beat(state, 0.08), EASE_SOFT));

    enterFig(state, api, pick('tip'),api.since(f, beat(state, 0.1)), {
      distance: 34,
      amplitude: 2
    });

    // 水下那一大团：从深处升上来，这是本幕的转折
    var massP = motion.spring(api.since(f, beat(state, 0.3)), 'enter');
    svgT(pick('massGroup'), 0, (1 - massP) * 150, 0, api.range(massP, 0.94, 1, { clamp: false }));
    svgO(pick('massGroup'), api.clamp(massP, 0, 1));

    // 三条标注按「先水上、再水下、最后出路」的顺序出现
    var callouts = pick('callouts') ? pick('callouts').children : [];
    var starts = [0.2, 0.5, 0.72];
    Array.prototype.forEach.call(callouts, function (group, index) {
      var start = beat(state, starts[index] === undefined ? 0.72 : starts[index]);
      var p = motion.spring(api.since(f, start), 'firm');
      var link = group.firstChild;
      if (link) {
        if (!link.dataset.length) {
          link.dataset.length = String(link.getTotalLength());
        }
        api.drawPath(link, api.progress(f, start - 8, 22, EASE_SOFT), { length: Number(link.dataset.length) });
      }
      var body = group.children[1];
      var label = group.children[2];
      var desc = group.children[3];
      svgT(body, (1 - p) * 34, 0);
      svgO(body, api.clamp(p, 0, 1));
      svgT(label, (1 - p) * 34, 0);
      svgO(label, api.clamp(p, 0, 1));
      svgT(desc, (1 - p) * 34, 0);
      svgO(desc, api.clamp(p * 1.1, 0, 1));
    });

    // 光照：一束光扫过水下那团，被藏起来的部分显形
    var band = pick('lightBand');
    if (band) {
      var sweep = api.progress(f, beat(state, 0.56), beat(state, 0.2), EASE_SYMMETRIC);
      band.setAttribute('x', String(api.range(sweep, -320, 900)));
      svgO(band, api.progress(f, beat(state, 0.56), 20, EASE_SOFT) * (1 - api.progress(f, beat(state, 0.78), 24, EASE_SOFT) * 0.35));
    }

    // 光扫过之后浮出水面的一股上升：位置固定在冰山右侧的空白水域，不压到山体与标注
    var sparks = pick('sparks') ? pick('sparks').children : [];
    Array.prototype.forEach.call(sparks, function (spark, index) {
      var start = beat(state, 0.62) + index * 9;
      var life = api.progress(f, start, beat(state, 0.28), 'linear');
      var y = api.range(life, 620, 168);
      var x = 344 + ((index % 3) - 1) * 30 + Math.sin(life * Math.PI) * 10;
      spark.setAttribute('cx', x.toFixed(1));
      spark.setAttribute('cy', y.toFixed(1));
      svgO(spark, Math.sin(clampStatic(life, 0, 1) * Math.PI) * 0.9);
    });
  }

  /** iceberg 的画面结构：文案元素留空，由分镜注入。 */
  var MARKUP_ICEBERG = `<h2 class="section-title" data-el="title" data-a2v-fit="title"></h2>
<!-- 冰山：看得见的「失去」只是一角，水面下那团才是本体 -->
<svg class="fig fig-berg" viewBox="0 0 888 760" aria-hidden="true">
  <defs>
    <clipPath id="berg-clip">
      <path d="M138 300 L296 300 L392 452 L348 632 L150 692 L34 500 Z"></path>
    </clipPath>
    <linearGradient id="berg-light" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"></stop>
      <stop offset="0.5" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 55%, transparent)"></stop>
      <stop offset="1" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"></stop>
    </linearGradient>
    <linearGradient id="berg-depth" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="rgba(45, 78, 120, 0.17)"></stop>
      <stop offset="0.75" stop-color="rgba(45, 78, 120, 0.06)"></stop>
      <stop offset="1" stop-color="rgba(45, 78, 120, 0)"></stop>
    </linearGradient>
  </defs>
  <rect class="berg-water" data-el="waterBody" x="0" y="300" width="888" height="460"></rect>
  <path class="ln" data-el="waterLine" d="M0 300 L888 300"></path>
  <text class="berg-surface-note" data-el="surfaceNote" x="24" y="274"></text>
  <path class="berg-tip" data-el="tip" d="M215 64 L138 300 L296 300 Z"></path>
  <g data-el="massGroup">
    <path class="berg-mass" d="M138 300 L296 300 L392 452 L348 632 L150 692 L34 500 Z"></path>
    <g clip-path="url(#berg-clip)">
      <rect data-el="lightBand" x="-320" y="260" width="320" height="480" fill="url(#berg-light)"></rect>
    </g>
  </g>
  <g data-el="sparks"></g>
  <g data-el="callouts"></g>
</svg>`;

  define('iceberg', ["surface"], MARKUP_ICEBERG, updateIceberg);

  /* ---------------- 04 飞轮 ---------------- */

  var LOOP = {
    CX: 444,
    CY: 290,
    R: 200,
    NODE_R: 76,
    SEGMENTS: 6,
    LAPS: 2
  };

  function loopPoint(travel) {
    var angle = ((-90 + travel * 120) * Math.PI) / 180;
    return {
      x: LOOP.CX + LOOP.R * Math.cos(angle),
      y: LOOP.CY + LOOP.R * Math.sin(angle)
    };
  }

  /**
   * 反馈循环：不做三个静止的方块加箭头，而是让一个点真的转起来。
   *
   * 每转一格，下面的「准备度」就抬高一截；两次完整循环之后条满。运动本身
   * 就是论点——上场不是一个动作，而是一个会自己加速的轮子。
   */
  function updateLoop(state, api, pick, labels) {
    var f = state.localFrame;
    var data = state.scene.data;
    var ann = labels || {};
    var nodes = data.nodes || [];

    setPlainText(pick('title'), data.title);
    setPlainText(pick('gaugeLabel'), ann.gauge);

    buildOnce(pick('arcs'), JSON.stringify(nodes), function (host) {
      nodes.forEach(function (name, index) {
        var from = loopPoint(index + 0);
        var to = loopPoint(index + 1);
        host.appendChild(
          svgEl('path', {
            class: 'loop-arc',
            'data-arc': String(index),
            d:
              'M' + from.x.toFixed(2) + ' ' + from.y.toFixed(2) +
              ' A ' + LOOP.R + ' ' + LOOP.R + ' 0 0 1 ' + to.x.toFixed(2) + ' ' + to.y.toFixed(2)
          })
        );
      });
    });

    buildOnce(pick('nodes'), JSON.stringify(nodes), function (host) {
      nodes.forEach(function (name, index) {
        var label = typeof name === 'string' ? name : name.label || name.id;
        var point = loopPoint(index);
        var group = svgEl('g', { 'data-node': String(index) });
        var text = svgEl('text', {
          class: 'loop-node-text a2v-label',
          'data-a2v-state': 'rest',
          /* 声明这段文字装在哪个容器里：观感闸门 K8 据此判定「有没有穿出圆」。
           * 只能由组件声明——阶梯的注写在柱子上方，同为近邻却不装在容器里，
           * 几何上无法自动区分。 */
          'data-a2v-inside': '.loop-node-disc',
          x: point.x,
          y: point.y
        });
        text.textContent = label;
        group.appendChild(text);
        /* 先挂进文档再测量：getComputedTextLength 需要一个已排版的环境。
         * 运行时在首次 seek 之前 await 过 document.fonts.ready，
         * 因此这里量到的就是最终字体。 */
        host.appendChild(group);
        var radius = LOOP.NODE_R;
        if (presetActive()) {
          /* 半径与内边距都取自令牌（`--fig-node-r-min` / `--fig-surface-pad`），
           * 不在 JS 里另立一份数值——否则「几何只有一处真源」又变成空话。 */
          var layout = fitLabelToCircle(
            text,
            label,
            tokenPx(text, '--fig-node-r-min', LOOP.NODE_R),
            tokenPx(text, '--fig-surface-pad', 16)
          );
          radius = layout.radius;
          paintLabelLines(text, layout, point.x, point.y);
        }
        group.insertBefore(
          svgEl('circle', { class: 'loop-node-shadow', cx: point.x, cy: point.y + 12, r: radius }),
          text
        );
        group.insertBefore(
          svgEl('circle', {
            class: 'loop-node-disc a2v-surface',
            'data-a2v-state': 'rest',
            cx: point.x,
            cy: point.y,
            r: radius
          }),
          text
        );
      });
    });

    // 轨道先淡入
    var track = pick('track');
    if (track) {
      track.style.opacity = String(api.progress(f, beat(state, 0.06), beat(state, 0.08), EASE_OUT));
    }

    // 小球：每格 SEG 帧，走满 6 格正好把「准备度」填满
    var travelStart = beat(state, 0.2);
    var segFrames = Math.max((state.sceneDurationFrames - travelStart) / LOOP.SEGMENTS, 1);
    var travel = clampStatic((f - travelStart) / segFrames, 0, LOOP.SEGMENTS);
    var point = loopPoint(travel);
    var arrived = Math.floor(travel);
    var frac = travel - arrived;

    /*
     * 节点只有一个 transform 写入点：入场位移、缩放入场与「到达时鼓一下」
     * 必须合成同一条 transform，否则后写的那条会把先写的覆盖掉。
     */
    var nodeGroups = pick('nodes') ? pick('nodes').children : [];
    var nodeStart = beat(state, 0.12);
    Array.prototype.forEach.call(nodeGroups, function (group, index) {
      var enterP = motion.spring(api.since(f, nodeStart + index * 8), 'enter');
      var nodePoint = loopPoint(index);
      /* 小球到达的那个节点就是当前的环节——它已经有"鼓一下"的脉冲，
       * 但状态一直是 rest，所以整幕没有任何强调色（实测 35% 帧只有 0.0015）。
       * 把到达的节点设为 focus：一个画面仍然只有一个焦点，
       * 但它随小球前进，而不是永不出现。
       * 与阶梯同一条规则：**焦点跟着行进走**。 */
      var isFocus = index === arrived % nodeGroups.length;
      var disc = group.querySelector('.loop-node-disc');
      var nodeLabel = group.querySelector('.loop-node-text');
      var nextState = isFocus ? 'focus' : 'rest';
      if (disc && disc.getAttribute('data-a2v-state') !== nextState) {
        disc.setAttribute('data-a2v-state', nextState);
      }
      if (nodeLabel && nodeLabel.getAttribute('data-a2v-state') !== nextState) {
        nodeLabel.setAttribute('data-a2v-state', nextState);
      }
      var pulse = isFocus ? clampStatic(1 - frac / 0.5, 0, 1) : 0;
      var scale = api.range(enterP, 0.94, 1, { clamp: false }) * (1 + pulse * 0.09);
      svgT(
        group,
        nodePoint.x * (1 - scale),
        nodePoint.y * (1 - scale) + (1 - clampStatic(enterP, 0, 1)) * 26,
        0,
        scale
      );
      svgO(group, api.clamp(enterP, 0, 1));
    });

    var arcs = pick('arcs') ? pick('arcs').children : [];
    Array.prototype.forEach.call(arcs, function (path, index) {
      if (!path.dataset.length) {
        path.dataset.length = String(path.getTotalLength());
      }
      api.drawPath(path, clampStatic(travel - index, 0, 1), { length: Number(path.dataset.length) });
    });

    var token = pick('token');
    var halo = pick('tokenHalo');
    var tokenIn = api.progress(f, travelStart - 6, 18, EASE_OUT);
    svgO(token, tokenIn);
    svgO(halo, tokenIn * 0.55);
    if (token) {
      token.setAttribute('cx', point.x.toFixed(2));
      token.setAttribute('cy', point.y.toFixed(2));
    }
    if (halo) {
      halo.setAttribute('cx', point.x.toFixed(2));
      halo.setAttribute('cy', point.y.toFixed(2));
    }

    // 到达节点时节点鼓一下，让「一圈」有落点（与入场 transform 已在上方合成）
    var gaugeFill = pick('gaugeFill');
    if (gaugeFill) {
      gaugeFill.style.width = (clampStatic(travel / LOOP.SEGMENTS, 0, 1) * 100).toFixed(2) + '%';
    }
  }

  /** loop 的画面结构：文案元素留空，由分镜注入。 */
  var MARKUP_LOOP = `<h2 class="section-title" data-el="title" data-a2v-fit="title"></h2>
<!-- 飞轮：一个小球沿着「上场→暴露→反馈」转圈，每转一格准备度就抬高一截 -->
<svg class="fig fig-loop" viewBox="0 0 888 560" aria-hidden="true">
  <defs>
    <radialGradient id="loop-halo">
      <stop offset="0" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 35%, transparent)"></stop>
      <stop offset="1" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"></stop>
    </radialGradient>
  </defs>
  <circle class="loop-track" data-el="track" cx="444" cy="290" r="200"></circle>
  <g data-el="arcs"></g>
  <circle class="loop-token-halo" data-el="tokenHalo" cx="444" cy="90" r="86"></circle>
  <circle class="loop-token" data-el="token" cx="444" cy="90" r="20"></circle>
  <g data-el="nodes"></g>
</svg>
<div class="gauge">
  <span class="gauge-label" data-el="gaugeLabel"></span>
  <span class="gauge-track"><span class="gauge-fill" data-el="gaugeFill"></span></span>
</div>`;

  define('loop', ["gauge"], MARKUP_LOOP, updateLoop);

  /* ---------------- 05 阶梯 ---------------- */

  var STAIRS = {
    BASE: 545,
    BAR_W: 152,
    GAP: 64,
    HEIGHTS: [100, 210, 330, 460],
    START: [0.07, 0.24, 0.48, 0.73]
  };

  function stairCenter(index) {
    var total = STAIRS.HEIGHTS.length * STAIRS.BAR_W + (STAIRS.HEIGHTS.length - 1) * STAIRS.GAP;
    return (888 - total) / 2 + index * (STAIRS.BAR_W + STAIRS.GAP) + STAIRS.BAR_W / 2;
  }

  /**
   * 上场的复利：把四个阶段画成四根越站越高的柱子。
   *
   * 柱子高度是「你在面试里的位置」，小球一跳一格；最后一格柱子转成强调色，
   * 顶部的标签从「公司在挑你」翻成「你在挑公司」——主动权换手，是本片的落点。
   */
  function updateStairs(state, api, pick, labels) {
    var f = state.localFrame;
    var data = state.scene.data;
    var ann = labels || {};
    var items = data.items || [];

    setPlainText(pick('title'), data.title);
    setPlainText(pick('axisLabel'), ann.axis);

    buildOnce(pick('bars'), JSON.stringify(items), function (host) {
      items.forEach(function (item, index) {
        var entry = typeof item === 'string' ? { label: item } : item;
        var cx = stairCenter(index);
        var group = svgEl('g', { 'data-bar': String(index) });

        var bar = svgEl('rect', {
          class: 'stair-bar a2v-surface',
          x: cx - STAIRS.BAR_W / 2,
          y: STAIRS.BASE,
          width: STAIRS.BAR_W,
          height: 0,
          rx: 20
        });
        group.appendChild(bar);

        var note = svgEl('text', { class: 'stair-note a2v-label', x: cx, y: STAIRS.BASE - STAIRS.HEIGHTS[index] - 44 });
        note.textContent = entry.note || '';
        group.appendChild(note);

        var label = svgEl('text', { class: 'stair-label', x: cx, y: STAIRS.BASE + 52 });
        label.textContent = entry.label || '';
        group.appendChild(label);

        host.appendChild(group);
      });
    });

    api.drawPath(pick('baseline'), api.progress(f, beat(state, 0.04), beat(state, 0.12), EASE_OUT), {
      length: 842
    });
    api.drawPath(pick('axis'), api.progress(f, beat(state, 0.05), beat(state, 0.14), EASE_OUT), {
      length: 467
    });

    /* 「口播念到哪一句，屏幕上就是哪一句」——这条规则原先只用在了说明文字上，
     * 视觉焦点却是另一套：`index === 最后一根 && p > 0.95`，也就是要等最上面那一级
     * 长到 95% 才点亮。时间轴是 STAIRS.START = [0.07, 0.24, 0.48, 0.73]，
     * 所以前 73% 的帧整屏没有任何焦点——实测 K2 在 35% 帧量到 0.0011。
     *
     * 现在焦点跟着口播走：**当前这一级就是焦点**，走到最后一级时收尾结论仍是焦点。
     * 一个画面仍然只有一个焦点，只是它随叙述前进，而不是只在结尾出现一次。 */
    var activeStep = 0;
    items.forEach(function (item, index) {
      if (f >= beat(state, STAIRS.START[index] === undefined ? 0.73 : STAIRS.START[index])) {
        activeStep = index;
      }
    });

    var groups = pick('bars') ? pick('bars').children : [];
    Array.prototype.forEach.call(groups, function (group, index) {
      var start = beat(state, STAIRS.START[index] === undefined ? 0.73 : STAIRS.START[index]);
      var p = motion.spring(api.since(f, start), 'firm');

      var bar = group.children[0];
      var note = group.children[1];
      var label = group.children[2];
      var height = (STAIRS.HEIGHTS[index] || 120) * clampStatic(p, 0, 1);
      bar.setAttribute('y', String(STAIRS.BASE - height));
      bar.setAttribute('height', String(height));
      var isFocus = index === activeStep;
      bar.setAttribute('data-a2v-state', isFocus ? 'focus' : 'rest');
      note.setAttribute('data-a2v-state', isFocus ? 'focus' : 'rest');
      note.setAttribute('y', String(STAIRS.BASE - height - 44));
      svgO(note, clampStatic((p - 0.55) * 2.2, 0, 1));
      svgO(label, clampStatic((p - 0.3) * 2, 0, 1));
    });

    // 说明文字跟着小球走：口播念到哪一句，屏幕上就是哪一句
    var caption = pick('caption');
    if (caption) {
      var entry = typeof items[activeStep] === 'string'
        ? { desc: items[activeStep] }
        : items[activeStep] || {};
      setPlainText(caption, entry.desc);
      var captionP = api.progress(f, beat(state, 0.03), 22, EASE_OUT);
      caption.style.opacity = String(api.clamp(captionP, 0, 1) * 0.94);
    }

    // 小球：逐格跳，落点就是那一格的柱顶
    var marker = pick('marker');
    var halo = pick('markerHalo');
    var firstStart = beat(state, STAIRS.START[0]);
    var markerIn = api.progress(f, firstStart, 20, EASE_OUT);
    var pos = { x: stairCenter(0), y: STAIRS.BASE - STAIRS.HEIGHTS[0] };
    for (var i = 1; i < groups.length; i += 1) {
      var hopStart = beat(state, STAIRS.START[i]) - beat(state, 0.05);
      var hop = api.progress(f, hopStart, beat(state, 0.05), EASE_SYMMETRIC);
      if (f >= hopStart) {
        var prev = { x: stairCenter(i - 1), y: STAIRS.BASE - STAIRS.HEIGHTS[i - 1] };
        var next = { x: stairCenter(i), y: STAIRS.BASE - STAIRS.HEIGHTS[i] };
        pos = {
          x: api.lerp(prev.x, next.x, hop),
          y: api.lerp(prev.y, next.y, hop) - Math.sin(hop * Math.PI) * 96
        };
      }
    }
    if (marker) {
      marker.setAttribute('cx', pos.x.toFixed(1));
      marker.setAttribute('cy', pos.y.toFixed(1));
    }
    if (halo) {
      halo.setAttribute('cx', pos.x.toFixed(1));
      halo.setAttribute('cy', pos.y.toFixed(1));
      svgO(halo, markerIn * 0.9);
    }
    svgO(marker, markerIn);

    // 主动权换手
    var flip = pick('flip');
    var flipP = api.progress(f, beat(state, 0.84), beat(state, 0.1), EASE_SYMMETRIC);
    if (flip) {
      flip.classList.toggle('is-after', flipP > 0.5);
      flip.style.opacity = String(api.progress(f, beat(state, 0.8), 20, EASE_OUT));
    }
    var arrow = pick('flipArrow');
    if (arrow) {
      arrow.className = 'flip-arrow ' + (flipP > 0.5 ? 'is-right' : 'is-left');
    }
    setPlainText(pick('flipText'), flipP > 0.5 ? ann.after : ann.before);
  }

  /** stairs 的画面结构：文案元素留空，由分镜注入。 */
  var MARKUP_STAIRS = `<h2 class="section-title" data-el="title" data-a2v-fit="title"></h2>
<!-- 阶梯：每一根柱子是一次上场之后的「位置」，小球沿着柱顶往上跳 -->
<div class="stair-caption" data-el="caption" data-a2v-fit="body"></div>
<svg class="fig fig-stairs" viewBox="0 0 888 640" aria-hidden="true">
  <defs>
    <radialGradient id="stair-halo">
      <stop offset="0" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 32%, transparent)"></stop>
      <stop offset="1" stop-color="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"></stop>
    </radialGradient>
  </defs>
  <text class="stair-axis-label" data-el="axisLabel" x="24" y="44"></text>
  <path class="stair-axis" data-el="axis" d="M26 545 L26 78"></path>
  <path class="stair-base" data-el="baseline" d="M26 545 L868 545"></path>
  <g data-el="bars"></g>
  <circle class="stair-marker-halo" data-el="markerHalo" cx="0" cy="0" r="64"></circle>
  <circle class="stair-marker" data-el="marker" cx="0" cy="0" r="22"></circle>
</svg>
<div class="stair-flip" data-el="flip">
  <span class="flip-arrow is-left" data-el="flipArrow"></span>
  <span data-el="flipText"></span>
</div>`;

  define('stairs', ["axis", "before", "after"], MARKUP_STAIRS, updateStairs);

  /* ---------------- 06 双向选择 ---------------- */

  /**
   * 收束：两支箭头同时存在，才叫「互相挑」。
   *
   * 先用逐字揭示把结论读出来，再让两端的节点和两条反向箭头成立；最后一条
   * 强调色箭头是「你也在挑公司」，与开场的天平形成同一支片子的呼应。
   */
  //: 结论句的排版边界。宽度与 .fig / .a2v-safe 一致（1080 − 96 × 2）。
  var EXCHANGE = { WIDTH: 888, MAX: 96, MIN: 54 };

  /**
   * 按最长一行算出能放下的字号。
   *
   * 中日韩字形宽度≈字号，因此「一行能放几个字」约等于 `宽度 / 字号`；
   * 用字符数而不是测量：测量既拖慢逐帧渲染，也会把布局抖动带进画面。
   * 短句原样保持设计字号，只有放不下时才缩。
   */
  function fitFontSize(text, spec) {
    var lines = String(text || '').split('\n');
    var longest = 1;
    lines.forEach(function (line) {
      if (line.length > longest) {
        longest = line.length;
      }
    });
    return Math.max(spec.MIN, Math.min(spec.MAX, Math.floor(spec.WIDTH / longest)));
  }
  function updateExchange(state, api, pick, labels) {
    var f = state.localFrame;
    var data = state.scene.data;
    var ann = labels || {};
    var text = pick('text');
    var action = pick('action');

    setPlainText(pick('nodeLeftText'), ann.leftNode);
    setPlainText(pick('nodeRightText'), ann.rightNode);

    if (action) {
      action.textContent = data.action || '';
      action.style.display = data.action ? '' : 'none';
    }

    if (text) {
      // 结论句长短差别很大（六字的金句与十几字的行动句都常见），
      // 字号跟着最长一行收缩，否则长句会在中间断开成「…的环 / 节，」
      text.style.fontSize = fitFontSize(data.text, EXCHANGE) + 'px';
      revealKeyChars(text, data.text || '', f, data.emphasis || [], {
        startFrame: beat(state, 0.02),
        staggerFrames: 2
      });
    }

    enterFig(state, api, pick('nodeLeft'),api.since(f, beat(state, 0.2)), {
      distance: 34,
      amplitude: 2.5,
      axis: 'x',
      scale: 0.94
    });
    enterFig(state, api, pick('nodeRight'),api.since(f, beat(state, 0.26)), {
      distance: -34,
      amplitude: 2.5,
      axis: 'x',
      scale: 0.94
    });

    var arcTo = pick('arcTo');
    var arcBack = pick('arcBack');
    api.drawPath(arcTo, api.progress(f, beat(state, 0.36), beat(state, 0.1), EASE_SOFT), { length: 392 });
    api.drawPath(arcBack, api.progress(f, beat(state, 0.44), beat(state, 0.1), EASE_SOFT), { length: 392 });
    /*
     * 箭头朝向取曲线末端的切线方向：二次贝塞尔在终点的切向是「终点 − 控制点」。
     * 硬编码角度会在改曲线端点时静默错位，所以这里由同一组常量算出来。
     */
    placeArrow(pick('arrowTo'), 628, 118, Math.atan2(118 - 66, 628 - 445) * 180 / Math.PI,
      api.progress(f, beat(state, 0.46), 14, EASE_OUT));
    placeArrow(pick('arrowBack'), 264, 182, Math.atan2(182 - 234, 264 - 445) * 180 / Math.PI,
      api.progress(f, beat(state, 0.54), 14, EASE_OUT));

    var key = text ? text.querySelector('.key') : null;
    if (key) {
      var highlight = api.progress(f, beat(state, 0.56), beat(state, 0.1), EASE_SYMMETRIC);
      key.style.textShadow =
        '0 0 ' + api.range(highlight, 0, 30).toFixed(1) + 'px rgba(var(--a2v-accent-rgb), ' +
        api.range(highlight, 0, 0.24).toFixed(3) + ')';
    }

    var actionP = api.progress(f, beat(state, 0.64), 28, EASE_OUT);
    if (action) {
      var actionSeconds = api.since(f, beat(state, 0.64));
      var shift = api.range(motion.spring(actionSeconds, 'enter'), 34, 0, { clamp: false });
      var drift = motion.idle(f, { amplitude: 3 }) *
        api.progress(f, beat(state, 0.64), 40, EASE_SYMMETRIC);
      action.style.transform = 'translate3d(' + shift.toFixed(2) + 'px,' + drift.toFixed(2) + 'px,0)';
      action.style.opacity = String(api.clamp(actionP, 0, 1));
    }
  }

  /** 箭头头部：一个按切线方向旋转的三角形，位置与朝向都由常量算出。 */
  function placeArrow(node, x, y, angleDeg, opacity) {
    if (!node) {
      return;
    }
    svgT(node, x, y, angleDeg);
    node.setAttribute('d', 'M0 0 L-34 -16 L-34 16 Z');
    svgO(node, opacity);
  }

  /** exchange 的画面结构：文案元素留空，由分镜注入。 */
  var MARKUP_EXCHANGE = `<p class="closing-text" data-el="text"></p>
<!-- 双向箭头：挑人不是单向的 -->
<svg class="fig fig-exchange" viewBox="0 0 888 300" aria-hidden="true">
  <g data-el="nodeLeft">
    <circle class="ex-node-disc" cx="150" cy="150" r="88"></circle>
    <text class="ex-node-text" data-el="nodeLeftText" x="150" y="150"></text>
  </g>
  <g data-el="nodeRight">
    <circle class="ex-node-disc is-accent" cx="738" cy="150" r="88"></circle>
    <text class="ex-node-text" data-el="nodeRightText" x="738" y="150"></text>
  </g>
  <path class="ex-arc" data-el="arcTo" d="M262 118 Q445 66 628 118"></path>
  <path class="ex-arrow" data-el="arrowTo" d="M0 0 L0 0"></path>
  <path class="ex-arc is-accent" data-el="arcBack" d="M626 182 Q445 234 264 182"></path>
  <path class="ex-arrow is-accent" data-el="arrowBack" d="M0 0 L0 0"></path>
</svg>
<p class="closing-action" data-el="action" data-a2v-fit="body"></p>`;

  define('exchange', ["leftNode", "rightNode"], MARKUP_EXCHANGE, updateExchange);

  /* ---------------- 结论幕的逐字揭示 ---------------- */
  /* ---------------- 结论幕的逐字揭示 ---------------- */

  /**
   * 逐字揭示 + 强调短语。
   *
   * 文本结构只在内容变化时重建，之后每帧只改各字的不透明度，因此同一帧永远
   * 得到同一画面；强调短语整体比正文晚 6 帧出现，读起来有轻重。
   */
  function revealKeyChars(el, text, frame, phrases, options) {
    var o = options || {};
    var start = o.startFrame === undefined ? 0 : o.startFrame;
    var stagger = Math.max(o.staggerFrames === undefined ? 2 : o.staggerFrames, 1);
    var value = text == null ? '' : String(text);
    var units = splitEmphasis(value, phrases);
    var signature = value + '|' + units.map(function (unit) {
      return (unit.key ? 'k' : '_') + unit.text;
    }).join('');

    if (el.getAttribute('data-a2v-emphasis-text') !== signature) {
      el.textContent = '';
      var frag = document.createDocumentFragment();
      units.forEach(function (unit) {
        var holder = document.createElement('span');
        holder.className = unit.key ? 'key' : 'plain';
        Array.prototype.slice.call(unit.text).forEach(function (ch) {
          var span = document.createElement('span');
          span.className = ch === '\n' ? 'reveal-char is-break' : 'reveal-char';
          span.textContent = ch;
          holder.appendChild(span);
        });
        frag.appendChild(holder);
      });
      el.appendChild(frag);
      el.setAttribute('data-a2v-emphasis-text', signature);
    }

    var spans = el.querySelectorAll('.reveal-char');
    var index = 0;
    Array.prototype.forEach.call(spans, function (span) {
      if (span.classList.contains('is-break')) {
        return;
      }
      var isKey = !!span.closest('.key');
      var charStart = start + index * stagger + (isKey ? 6 : 0);
      span.style.opacity = String(clampStatic((frame - charStart) / stagger, 0, 1));
      index += 1;
    });
  }

  /** 把文本切成「普通片段 / 强调片段」，强调片段是 phrases 中第一处命中的部分。 */
  function splitEmphasis(text, phrases) {
    var list = phrases || [];
    for (var i = 0; i < list.length; i += 1) {
      var phrase = list[i];
      if (typeof phrase !== 'string' || !phrase) {
        continue;
      }
      var at = text.indexOf(phrase);
      if (at === -1) {
        continue;
      }
      return [
        { text: text.slice(0, at), key: false },
        { text: phrase, key: true },
        { text: text.slice(at + phrase.length), key: false }
      ].filter(function (unit) {
        return unit.text !== '';
      });
    }
    return [{ text: text, key: false }];
  }

  /* ---------------- 数字幕 ---------------- */
  function updateNumber(state, api, pick, labels) {
    var ann = labels || {};
    var data = state.scene.data || {};
    var value = pick('value');
    var label = pick('label');
    var caption = pick('caption');
    var progress = api.progress(state.localFrame, beat(state, 0.1), beat(state, 0.36), EASE_OUT);
    // 数字滚动要的是缓动过的进度，入场位移要的是线性秒数，同一个起点各取所需
    var rise = api.since(state.localFrame, beat(state, 0.1));
    if (value) {
      var raw = data.value;
      /* 只有滚得动的数值才滚：步数不足 ROLL_MIN 时直接给最终值。
       * 非数字（或不有限）一律原样显示，这一支与从前完全一致。 */
      var rollable = typeof raw === 'number' && Number.isFinite(raw) && Math.abs(raw) >= ROLL_MIN;
      value.textContent = rollable
        ? String(Math.round(raw * progress))
        : String(raw == null ? '' : raw);
      enterAlive(state, api, value, rise, { distance: 42, scale: 0.92 });
    }
    setPlainText(label, data.label);
    setPlainText(caption, data.caption);
    enterAlive(state, api, label, api.since(state.localFrame, beat(state, 0.22)));
    enterAlive(state, api, caption, api.since(state.localFrame, beat(state, 0.38)));
  }

  var MARKUP_NUMBER = `<div class="fig-number" data-el="value" data-a2v-fit="numeral"></div>
<div class="fig-number-label" data-el="label" data-a2v-fit="title"></div>
<p class="fig-number-caption" data-el="caption" data-a2v-fit="body"></p>`;

  define('number', [], MARKUP_NUMBER, updateNumber);

  /* ---------------- 挂载与渲染 ---------------- */

  /** 稳定的签名：只有标注或参数变了才重建 DOM。 */
  function signature(kind, spec) {
    return kind + '|' + JSON.stringify(spec.labels || {}) + '|' + JSON.stringify(spec.params || {});
  }

  /**
   * 把 kind 组件挂到 host 上，返回可复用的实例。
   * 签名不变就复用现有 DOM：逐帧调用不会反复重建，也不会丢掉已缓存的路径长度。
   */
  function mount(kind, host, spec) {
    var definition = KINDS[kind];
    if (!definition) {
      throw new Error('视觉组件未注册: ' + kind + '（已注册：' + known().join('、') + '）');
    }
    var sig = signature(kind, spec || {});
    if (host.__a2vFigure && host.getAttribute('data-fig-signature') === sig) {
      return host.__a2vFigure;
    }
    host.innerHTML = definition.markup;
    host.setAttribute('data-fig-kind', kind);
    host.setAttribute('data-fig-signature', sig);
    host.__a2vFigure = definition.create({ host: host, spec: spec || {} });
    return host.__a2vFigure;
  }

  /**
   * 单帧渲染入口：找到当前场景的挂载点，按分镜声明的 kind 更新。
   * defaults 是页面给出的「场景类型 → 默认组件」映射，用于还没有声明
   * data.figure 的分镜，保证旧分镜继续可渲染。
   */
  function renderScene(state, api, options) {
    var opts = options || {};
    var defaults = opts.defaults || {};
    var scenes = document.querySelectorAll('[data-a2v-scene]');
    var sceneEl = scenes[state.sceneIndex];
    if (!sceneEl) {
      return;
    }
    var host = sceneEl.querySelector('[data-a2v-figure]');
    if (!host) {
      return;
    }
    var data = state.scene.data || {};
    var declared = data.figure || {};
    var kind = declared.kind || defaults[state.scene.type];
    if (!kind) {
      throw new Error(
        '场景 ' + state.scene.id + ' 未声明 data.figure.kind，类型 ' + state.scene.type + ' 也没有默认组件'
      );
    }
    /*
     * labels 优先取 data.figure.labels；过渡期兼容 P0 的 data.annotations，
     * 两种写法都指向同一件事：这幅图上的短标签写什么。两者在这里合流成一份，
     * 由 define 的包装注入给组件。
     */
    var labels = declared.labels || data.annotations || {};
    var instance = mount(kind, host, {
      kind: kind,
      labels: labels,
      params: declared.params || {},
      motion: declared.motion || 'normal'
    });
    instance.update(state, api);
  }

  /** 组件目录：kind -> 它认识的标注键，供文档与校验器对齐。 */
  function describe() {
    var out = {};
    Object.keys(KINDS).forEach(function (kind) {
      out[kind] = { labels: KINDS[kind].labels || [] };
    });
    return out;
  }

  A2V.figures = {
    register: register,
    known: known,
    mount: mount,
    renderScene: renderScene,
    describe: describe,
    /** 节奏名 -> 速度倍率。配方本体在运行时的 A2V.motion，这里只是转发。 */
    tempo: motion.tempo
  };
})(window);
