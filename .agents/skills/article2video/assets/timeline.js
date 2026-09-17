/**
 * article2video 时间轴运行时（浏览器端，可选辅助库）
 *
 * 这一层只做「确定性」相关的脏活：
 *   1. 把分镜 JSON 换算成帧到场景的映射；
 *   2. 暴露渲染脚本要求的 window.__A2V__ 契约；
 *   3. 提供预览播放控制（播放/暂停/重播/拖动）。
 *
 * 它不决定任何视觉表达。画面全部由调用方传入的 render(state, api) 决定，
 * 只要遵守两条规则：
 *   - 画面只由 state.frame 推导，禁止读取 Date.now、performance.now、
 *     Math.random，也不要依赖 CSS animation/transition 的播放时间；
 *   - 同一帧重复渲染必须得到同一画面。
 *
 * 动效原语（全部是纯函数，不保存任何跨帧状态）：
 *   progress / stagger / enter    基础：进度、逐项起始帧、透明度 + 位移 + 缩放
 *   spring / range / breath       进阶：微过冲、数值映射、常驻呼吸位移
 *   drawPath / revealChars        专项：SVG 描边动画、逐字揭示
 * 配方与推荐帧数见 references/visual-spec.md。
 *
 * 为什么不用 CSS 动画：渲染脚本按帧号截图，CSS 动画由浏览器时钟驱动，
 * 截图时刻与动画时间无法对齐，导出的视频会出现随机闪烁。
 */
(function (global) {
  'use strict';

  //: 只走这三条曲线，混用更多会让整支片子的手感不一致（见设计宪法 C4）。
  var EASE = { enter: 'outQuint', gate: 'outCubic', both: 'inOutCubic' };

  /** 缓动函数集合。只在帧位置已知时使用，因此结果可复现。 */
  var easing = {
    linear: function (t) {
      return t;
    },
    outCubic: function (t) {
      return 1 - Math.pow(1 - t, 3);
    },
    inOutCubic: function (t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    },
    outQuint: function (t) {
      return 1 - Math.pow(1 - t, 5);
    },
    outBack: function (t) {
      var c1 = 1.70158;
      var c3 = c1 + 1;
      return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    }
  };

  function clamp(value, min, max) {
    return value < min ? min : value > max ? max : value;
  }

  function lerp(from, to, t) {
    return from + (to - from) * t;
  }

  /**
   * 计算动画片段进度。
   * @param {number} localFrame 场景内帧号
   * @param {number} startFrame 片段起始帧
   * @param {number} durationFrames 片段持续帧数
   * @param {string} [easingName] 缓动名，默认 linear
   * @returns {number} 0..1
   */
  function progress(localFrame, startFrame, durationFrames, easingName) {
    if (durationFrames <= 0) {
      return localFrame >= startFrame ? 1 : 0;
    }
    var t = clamp((localFrame - startFrame) / durationFrames, 0, 1);
    var fn = easing[easingName] || easing.linear;
    return fn(t);
  }

  /** 逐项呈现时第 index 项的起始帧。 */
  function stagger(index, stepFrames, baseFrame) {
    return (baseFrame || 0) + index * (stepFrames || 0);
  }

  /**
   * 统一的入场动效：按进度设置透明度与位移。
   * 直接写内联样式而不是切换 class，确保同一帧得到同一结果。
   */
  function enter(el, p, options) {
    if (!el) {
      return;
    }
    var o = options || {};
    var distance = o.distance === undefined ? 48 : o.distance;
    var axis = o.axis || 'y';
    var fromScale = o.scale === undefined ? 1 : o.scale;
    var maxOpacity = o.opacity === undefined ? 1 : o.opacity;
    var shift = (1 - p) * distance;
    el.style.opacity = String(p * maxOpacity);
    el.style.transform =
      'translate3d(' +
      (axis === 'x' ? shift : 0) +
      'px,' +
      (axis === 'y' ? shift : 0) +
      'px,0) scale(' +
      lerp(fromScale, 1, p) +
      ')';
  }

  /**
   * 解析式阻尼振子：把 0..1 的线性进度映射为带微过冲的位移/缩放进度。
   *
   * 为什么用解析公式而不是迭代积分：逐帧渲染要求「同一帧永远同一结果」，
   * 解析式只依赖入参，不保存速度、不依赖调用顺序，天然满足契约。
   *
   * 默认参数在 30fps 下约 0.6 秒收敛，峰值过冲约 1.5%——刚好让画面「有弹性」
   * 而不显得晃。想要更明显的回弹可降低 damping（4–5），想要更稳可用 8–10。
   *
   * @param {number} t 进度，通常来自 progress()
   * @param {Object} [options]
   * @param {number} [options.damping=6] 阻尼系数，越小回弹越明显
   * @param {number} [options.frequency=1.2] 振动频率，越大越快到位
   * @returns {number} 进度值，峰值可能略大于 1
   */
  function spring(t, options) {
    var o = options || {};
    var x = clamp(t, 0, 1);
    if (x <= 0) {
      return 0;
    }
    if (x >= 1) {
      return 1;
    }
    var damping = o.damping === undefined ? 6 : o.damping;
    var frequency = o.frequency === undefined ? 1.2 : o.frequency;
    return 1 - Math.exp(-damping * x) * Math.cos(frequency * Math.PI * x);
  }

  /**
   * 把 0..1 的进度线性映射到任意数值区间，作为位移、缩放、透明度、光晕强度的
   * 统一驱动。默认把结果钳制在区间内，避免 spring 的过冲把数值推出合理范围。
   *
   * @param {number} t 进度
   * @param {number} from 起点值
   * @param {number} to 终点值
   * @param {Object} [options]
   * @param {boolean} [options.clamp=true] 是否把 t 钳制到 0..1
   * @returns {number}
   */
  function range(t, from, to, options) {
    var o = options || {};
    var x = o.clamp === false ? t : clamp(t, 0, 1);
    return from + (to - from) * x;
  }

  /**
   * 常驻微动：让画面在「入场动画已经结束」的后半段仍有一点活性。
   * 配音会把场景拉长，如果后段完全静止，成片会显得卡住。
   *
   * 只依赖帧号与常量，因此逐帧可复现；振幅建议 ≤ 6px，周期建议 90–150 帧。
   *
   * @param {number} localFrame 场景内帧号
   * @param {Object} [options]
   * @param {number} [options.periodFrames=120] 一个完整呼吸的帧数
   * @param {number} [options.amplitude=4] 振幅（px）
   * @param {number} [options.phase=0] 相位偏移，用于错开多个元素
   * @returns {number} 当帧的位移量（px），正负交替
   */
  function breath(localFrame, options) {
    var o = options || {};
    var period = o.periodFrames === undefined ? 120 : o.periodFrames;
    var amplitude = o.amplitude === undefined ? 4 : o.amplitude;
    if (!period) {
      return 0;
    }
    return Math.sin(((localFrame + (o.phase || 0)) / period) * Math.PI * 2) * amplitude;
  }

  /* ==================== 动效配方 ==================== */

  /*
   * 配方层解决的问题：入场动效由「弹性曲线 + 收敛时机 + 常驻微动」三件事组成，
   * 这三件事决定整支片子的手感。如果每个组件自己写阻尼、频率、收敛帧数，
   * 手感就会随组件漂移，而且没有一处可以整体调整。
   *
   * 所以：**数字只写在这里，组件只说「这是什么元素、移动多远」**。
   *
   * 两档配方按元素的落点分：
   *   surface —— 画面上的表面（卡片、文字块），位移略大、呼吸略快；
   *   figure  —— 图形本体（SVG 分组），位移略小，避免与几何线条打架。
   */
  var RECIPES = {
    surface: {
      distance: 44,
      scale: 1,
      periodFrames: 130,
      amplitude: 3,
      springDamping: 6,
      springFrequency: 1.1,
      settleAt: 0.24,
      settleFrames: 36
    },
    figure: {
      distance: 40,
      scale: 1,
      periodFrames: 140,
      amplitude: 2.5,
      springDamping: 6,
      springFrequency: 1.1,
      settleAt: 0.24,
      settleFrames: 36
    }
  };

  //: 节奏名 → 速度倍率。分镜只写名字，节拍由运行时算。
  var TEMPO_SPEED = { calm: 0.82, normal: 1, impact: 1.24 };

  /*
   * 弹性预设。组件里写 `{ damping: 5.5, frequency: 1.3 }` 这种数字时，
   * 读者看不出它和别处的 `{ damping: 6, frequency: 1.2 }` 有什么意图差别，
   * 改一处也想不到别处还有几处。给它们起名之后，「这个元素该有多弹」就成了可讨论的事。
   */
  var SPRINGS = {
    enter: { damping: 6, frequency: 1.1 }, // 温和入场，几乎看不出回弹
    firm: { damping: 6, frequency: 1.2 }, // 图形主体到位（默认）
    lively: { damping: 5.5, frequency: 1.3 }, // 有分量的落点，回弹看得出来
    snap: { damping: 5, frequency: 1.5 } // 小元素快速归位
  };

  //: 幕内常驻微动的周期。振幅按元素分档，周期统一，否则同屏各晃各的。
  var DRIFT_PERIOD = 150;

  function recipe(name) {
    return RECIPES[name] || RECIPES.surface;
  }

  /** 按预设名取弹性值；未知名字用 firm，不抛错。 */
  function springBy(p, name) {
    return spring(p, SPRINGS[name] || SPRINGS.firm);
  }

  /** 幕内常驻微动：周期统一，只按元素给振幅与相位。 */
  function idle(localFrame, options) {
    var o = options || {};
    return breath(localFrame, {
      periodFrames: o.periodFrames === undefined ? DRIFT_PERIOD : o.periodFrames,
      amplitude: o.amplitude === undefined ? 3 : o.amplitude,
      phase: o.phase || 0
    });
  }

  /** 节奏名对应的速度倍率；未知名字按正常速度处理，不抛错。 */
  function tempo(name) {
    return TEMPO_SPEED[name] || TEMPO_SPEED.normal;
  }

  /**
   * 当前场景的组件声明（kind / labels / motion）。
   *
   * `state.scene` 是场景对象本身，声明写在它的 `data` 里；
   * 兼容直接传 data 的写法，避免运行时的两种状态形状各自踩一次。
   */
  function sceneFigure(state) {
    var scene = (state && state.scene) || {};
    var data = scene.data || scene;
    return data.figure || {};
  }

  /**
   * 当前场景的节奏倍率。
   *
   * 从 state 里读，而不是模块级变量：节奏是这一幕的属性，
   * 用隐藏状态会让「同一帧同一结果」依赖于调用顺序。
   */
  function tempoOf(state) {
    return tempo(sceneFigure(state).motion);
  }

  /**
   * 场景内的比例点换算成绝对帧号，并按该幕的节奏缩放。
   *
   * 用比例而不是绝对帧：配音把场景拉长后，入场节奏保持不变。
   * 节奏越快，同一个比例点越早到达，后半段自然留出更长的停留。
   */
  function motionBeat(state, fraction) {
    if (!state || !state.sceneDurationFrames) {
      return 0;
    }
    return (fraction * state.sceneDurationFrames) / tempoOf(state);
  }

  /**
   * 入场收敛度：入场结束后把缩放钉在 1，并让常驻微动淡入。
   *
   * 没有这一步，弹性曲线的过冲会把元素长期留在一个略大的尺寸上，
   * 常驻微动也会在入场阶段就开始晃。
   */
  function settle(state, options) {
    var o = options || {};
    return settleWith(state, recipe(o.recipe), o);
  }

  function settleWith(state, base, options) {
    var o = options || {};
    var at = o.at === undefined ? base.settleAt : o.at;
    var frames = o.frames === undefined ? base.settleFrames : o.frames;
    return progress(state.localFrame, motionBeat(state, at), frames, EASE.both);
  }

  /** 给 SVG 元素写 transform 属性（SVG 用属性而不是 CSS，避免布局抖动）。 */
  function svgTransform(node, tx, ty, rotate, scale) {
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

  /**
   * 入场配方的实现：弹性曲线 + 收敛 + 常驻微动，算完交给调用方去写属性。
   *
   * HTML 与 SVG 只有「最后怎么写」不同，因此参数解析只在这里写一次——
   * 两处各写一遍必然会慢慢走偏（曾经 SVG 一侧就漏掉了自己的呼吸周期）。
   *
   * @param {Object} state 运行时状态，用于取节奏与场景内帧号
   * @param {string} name 默认配方名（surface / figure）
   * @param {number} p 入场进度 0..1，通常来自 progress()
   * @param {Object} [options] distance / axis / scale / amplitude / periodFrames / phase / opacity / recipe
   */
  function enterRecipe(state, name, p, options) {
    var o = options || {};
    var base = recipe(o.recipe || name);
    var from = spring(p, { damping: base.springDamping, frequency: base.springFrequency });
    var pin = settleWith(state, base, o);
    return {
      from: from,
      axis: o.axis || 'y',
      shift: (1 - from) * (o.distance === undefined ? base.distance : o.distance),
      drift:
        breath(state.localFrame, {
          periodFrames: o.periodFrames === undefined ? base.periodFrames : o.periodFrames,
          amplitude: o.amplitude === undefined ? base.amplitude : o.amplitude,
          phase: o.phase || 0
        }) * pin,
      scale: o.scale === undefined ? base.scale : o.scale
    };
  }

  /**
   * HTML 元素的入场 + 常驻微动。
   *
   * @param {Object} state 运行时状态
   * @param {HTMLElement} el 目标元素
   * @param {number} p 入场进度 0..1
   * @param {Object} [options] 见 enterRecipe
   */
  function enterAlive(state, el, p, options) {
    if (!el) {
      return;
    }
    var o = options || {};
    var r = enterRecipe(state, 'surface', p, o);
    el.style.transform =
      'translate3d(' +
      (r.axis === 'x' ? r.shift : 0).toFixed(2) +
      'px,' +
      ((r.axis === 'y' ? r.shift : 0) + r.drift).toFixed(2) +
      'px,0) scale(' +
      range(r.from, r.scale, 1, { clamp: false }).toFixed(4) +
      ')';
    el.style.opacity = String(clamp(r.from, 0, 1) * (o.opacity === undefined ? 1 : o.opacity));
  }

  /** SVG 分组的入场：同上，写的是 SVG 的 transform 属性。 */
  function enterSvg(state, node, p, options) {
    if (!node) {
      return;
    }
    var r = enterRecipe(state, 'figure', p, options);
    svgTransform(
      node,
      r.axis === 'x' ? r.shift : 0,
      (r.axis === 'y' ? r.shift : 0) + r.drift,
      0,
      range(r.from, r.scale, 1, { clamp: false })
    );
    node.setAttribute('opacity', String(clamp(r.from, 0, 1)));
  }

  /** 配方表：只读快照，供文档与调试对照。 */
  function motionRecipes() {
    var out = {};
    Object.keys(RECIPES).forEach(function (name) {
      var entry = RECIPES[name];
      out[name] = {};
      Object.keys(entry).forEach(function (key) {
        out[name][key] = entry[key];
      });
    });
    return out;
  }

  /**
   * 动效配方层。
   *
   * 组件从这里取「入场怎么做」，而不是各自写阻尼、频率与收敛帧数：
   * 那些数字决定整支片子的手感，散落在各组件里就没人能整体调，
   * 新写的组件也会慢慢长成另一种手感。
   */
  var motion = {
    tempo: tempo,
    beat: motionBeat,
    settle: settle,
    spring: springBy,
    idle: idle,
    enter: enterAlive,
    enterSvg: enterSvg,
    recipes: motionRecipes,
    springs: function () {
      var out = {};
      Object.keys(SPRINGS).forEach(function (name) {
        out[name] = { damping: SPRINGS[name].damping, frequency: SPRINGS[name].frequency };
      });
      return out;
    }
  };

  /**
   * 描边动画：按进度画出 SVG 路径（箭头、连线、回环）。
   *
   * length 由调用方测量一次（path.getTotalLength()）后传入，运行时不测量：
   * 每帧测量既慢，又会把布局抖动带进画面。
   *
   * @param {SVGPathElement} path SVG 路径元素
   * @param {number} p 进度 0..1
   * @param {Object} [options]
   * @param {number} options.length 路径总长度，省略时读取 data-a2v-length
   */
  function drawPath(path, p, options) {
    if (!path) {
      return;
    }
    var o = options || {};
    var length = o.length;
    if (length === undefined) {
      var declared = parseFloat(path.getAttribute('data-a2v-length'));
      length = isFinite(declared) && declared > 0 ? declared : 1;
    }
    var x = clamp(p, 0, 1);
    if (!path.hasAttribute('data-a2v-length')) {
      path.setAttribute('data-a2v-length', String(length));
    }
    path.setAttribute('stroke-dasharray', String(length));
    path.setAttribute('stroke-dashoffset', String(length * (1 - x)));
    path.style.opacity = String(x);
  }

  /**
   * 逐字揭示：中文长句按帧号逐字点亮，比整句淡入更有「被读出来」的感觉。
   *
   * 文本节点结构只在内容变化时重建，之后每帧只改写各字的不透明度，
   * 因此同一帧永远得到同一画面；文本内容保持完整，不影响读屏与选取。
   *
   * 页面需要为单字节点提供基础样式（示例见 examples/why-effort-fails/index.html）：
   *
   *   .reveal-char { display: inline-block; white-space: pre; }
   *   .reveal-char.is-break { display: block; height: 0; }
   *
   * 两种用法（二选一）：
   *   revealChars(el, text, p);                                  // 按整体进度均分
   *   revealChars(el, text, 0, { frame: f, staggerFrames: 3 });  // 按帧号逐字
   *
   * @param {Element} el 目标元素
   * @param {string} text 文案
   * @param {number} p 进度 0..1（帧号模式可传 0，该值被忽略）
   * @param {Object} [options]
   * @param {number} [options.staggerFrames] 每字间隔帧数，与 frame 搭配启用帧号模式
   * @param {number} [options.frame] 场景内帧号
   * @param {number} [options.startFrame=0] 逐字起点帧
   * @param {number} [options.tailFade=0.35] 进度模式下每字自身淡入所占比例
   */
  function revealChars(el, text, p, options) {
    if (!el) {
      return;
    }
    var o = options || {};
    var value = text == null ? '' : String(text);
    var chars = Array.prototype.slice.call(value);

    if (el.getAttribute('data-a2v-text') !== value) {
      var frag = document.createDocumentFragment();
      chars.forEach(function (ch) {
        var span = document.createElement('span');
        span.className = ch === '\n' ? 'reveal-char is-break' : 'reveal-char';
        span.textContent = ch;
        // 换行符用块级占位，保持与父元素 white-space: pre-line 相同的断行语义
        frag.appendChild(span);
      });
      el.textContent = '';
      el.appendChild(frag);
      el.setAttribute('data-a2v-text', value);
    }

    el.style.opacity = '1';
    var spans = el.children;
    if (!chars.length) {
      return;
    }

    if (typeof o.staggerFrames === 'number' && typeof o.frame === 'number') {
      var step = Math.max(o.staggerFrames, 1);
      var base = o.startFrame || 0;
      for (var i = 0; i < spans.length; i += 1) {
        spans[i].style.opacity = String(clamp((o.frame - base - i * step) / step, 0, 1));
      }
      return;
    }

    var tailFade = o.tailFade === undefined ? 0.35 : o.tailFade;
    var span = chars.length > 1 ? (1 + tailFade) / chars.length : 1;
    var last = Math.max(1 - span, 0);
    for (var j = 0; j < spans.length; j += 1) {
      var start = chars.length > 1 ? (j / (chars.length - 1)) * last : 0;
      spans[j].style.opacity = String(clamp((p - start) / span, 0, 1));
    }
  }

  /** 读取内联分镜：<script type="application/json" data-a2v-storyboard> */
  function readInlineStoryboard(idOrNull) {
    var selector = idOrNull
      ? 'script[data-a2v-storyboard]#' + idOrNull
      : 'script[data-a2v-storyboard]';
    var node = document.querySelector(selector) || document.getElementById(idOrNull || '');
    if (!node) {
      throw new Error('未找到内联分镜脚本，请检查 <script type="application/json" data-a2v-storyboard>');
    }
    return JSON.parse(node.textContent);
  }

  /** 从相对路径读取分镜 JSON。需要 HTTP 环境，file:// 会被同源策略拒绝。 */
  function fetchStoryboard(url) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) {
        throw new Error('分镜脚本加载失败: HTTP ' + response.status + ' ' + url);
      }
      return response.json();
    }).then(function (storyboard) {
      var mediaUrl = new URLSearchParams(location.search).get('a2v-media');
      if (!mediaUrl) return storyboard;
      return fetch(mediaUrl, { cache: 'no-store' }).then(function (response) {
        if (!response.ok) throw new Error('媒体清单加载失败: ' + response.status);
        return response.json();
      }).then(function (media) {
        if (media.version !== 1 || stableJSON(media.source) !== stableJSON(storyboard)) {
          throw new Error('媒体与分镜不匹配，请重新 prepare');
        }
        if (!Array.isArray(media.scenes) || media.scenes.length !== storyboard.scenes.length || !Array.isArray(media.cues)) {
          throw new Error('媒体场景或字幕非法');
        }
        storyboard.scenes.forEach(function (scene, index) {
          var prepared = media.scenes[index];
          if (prepared.id !== scene.id || !Number.isInteger(prepared.durationInFrames) || prepared.durationInFrames < scene.durationInFrames) {
            throw new Error('媒体场景时长非法');
          }
          scene.durationInFrames = prepared.durationInFrames;
        });
        media.audioUrl = new URL(media.audio, mediaUrl).href;
        Object.defineProperty(storyboard, '_a2vMedia', { value: media });
        return storyboard;
      });
    });
  }

  function stableJSON(value) {
    if (Array.isArray(value)) return '[' + value.map(stableJSON).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(function (key) {
      return JSON.stringify(key) + ':' + stableJSON(value[key]);
    }).join(',') + '}';
    return JSON.stringify(value);
  }

  /** 把分镜展开为带起始帧的场景列表，并算出总帧数。 */
  function layoutStoryboard(storyboard) {
    var fps = storyboard.fps || 30;
    var scenes = [];
    var cursor = 0;
    (storyboard.scenes || []).forEach(function (scene, index) {
      var duration = scene.durationInFrames;
      if (typeof duration !== 'number' || duration <= 0) {
        throw new Error('scenes[' + index + '] 的 durationInFrames 必须是正数');
      }
      scenes.push({
        index: index,
        data: scene,
        startFrame: cursor,
        durationInFrames: duration,
        endFrame: cursor + duration
      });
      cursor += duration;
    });
    if (!scenes.length) {
      throw new Error('分镜脚本没有任何场景');
    }
    return {
      fps: fps,
      width: storyboard.width || 1080,
      height: storyboard.height || 1920,
      title: storyboard.title || '',
      scenes: scenes,
      totalFrames: cursor
    };
  }

  /** 返回包含 frame 的场景；越界时钳制到首末场景，保证 seek 稳定。 */
  function sceneAt(timeline, frame) {
    for (var i = 0; i < timeline.scenes.length; i += 1) {
      var scene = timeline.scenes[i];
      if (frame >= scene.startFrame && frame < scene.endFrame) {
        return scene;
      }
    }
    if (frame >= timeline.totalFrames) {
      return timeline.scenes[timeline.scenes.length - 1];
    }
    return timeline.scenes[0];
  }

  /** 构造供 render 使用的完整帧状态。 */
  function buildState(timeline, frame) {
    var scene = sceneAt(timeline, frame);
    var localFrame = frame - scene.startFrame;
    return {
      frame: frame,
      timeMs: (frame / timeline.fps) * 1000,
      fps: timeline.fps,
      totalFrames: timeline.totalFrames,
      durationMs: (timeline.totalFrames / timeline.fps) * 1000,
      progress: timeline.totalFrames ? frame / timeline.totalFrames : 0,
      scene: scene.data,
      sceneIndex: scene.index,
      sceneCount: timeline.scenes.length,
      sceneStartFrame: scene.startFrame,
      sceneDurationFrames: scene.durationInFrames,
      localFrame: localFrame,
      localProgress: scene.durationInFrames ? localFrame / scene.durationInFrames : 0
    };
  }

  /** 等待一次绘制提交；后台标签页 rAF 被节流时用定时器兜底。 */
  function nextPaint() {
    return new Promise(function (resolve) {
      var settled = false;
      function finish() {
        if (!settled) {
          settled = true;
          resolve();
        }
      }
      if (typeof requestAnimationFrame === 'function') {
        requestAnimationFrame(finish);
      }
      setTimeout(finish, 50);
    });
  }

  /** 等待字体与图片就绪，避免首帧用回退字体排版。 */
  function waitForAssets() {
    var tasks = [];
    if (document.fonts && document.fonts.ready) {
      tasks.push(document.fonts.ready);
    }
    var images = Array.prototype.slice.call(document.images || []);
    images.forEach(function (img) {
      if (img.complete) {
        return;
      }
      tasks.push(
        new Promise(function (resolve) {
          img.addEventListener('load', resolve, { once: true });
          img.addEventListener('error', resolve, { once: true });
        })
      );
    });
    return Promise.all(tasks);
  }

  function formatTime(seconds) {
    var total = Math.max(0, Math.round(seconds));
    var m = Math.floor(total / 60);
    var s = total % 60;
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  /**
   * 挂载时间轴并暴露 __A2V__ 契约。
   *
   * @param {Object} options
   * @param {Object} options.storyboard 分镜对象（必填）
   * @param {Function} options.render function(state, api) 绘制指定帧（必填）
   * @param {Element} [options.root] 舞台容器，默认 [data-a2v-stage]
   * @param {boolean} [options.isolateScenes] 由运行时切换场景容器显示，默认 true
   * @param {boolean} [options.controls] 绑定播放控件，默认 true
   */
  function mount(options) {
    var opts = options || {};
    if (!opts.storyboard) {
      throw new Error('mount 需要 storyboard');
    }
    if (typeof opts.render !== 'function') {
      throw new Error('mount 需要 render(state, api) 函数');
    }

    var timeline = layoutStoryboard(opts.storyboard);
    var root = opts.root || document.querySelector('[data-a2v-stage]') || document.body;
    var media = opts.storyboard._a2vMedia;
    var audio = media ? new Audio(media.audioUrl) : null;
    var audioReady = Promise.resolve();
    var audioLoaded = !media;
    var subtitle = null;
    if (media) {
      root.classList.add('a2v-with-subtitles');
      subtitle = document.createElement('div');
      subtitle.className = 'a2v-subtitle';
      subtitle.setAttribute('data-a2v-subtitle', '');
      root.appendChild(subtitle);
      audio.preload = 'auto';
      audio.hidden = true;
      audio.setAttribute('data-a2v-audio', '');
      root.appendChild(audio);
      audioReady = new Promise(function (resolve, reject) {
        var timer = setTimeout(function () { reject(new Error('配音加载超时')); }, 30000);
        audio.addEventListener('canplaythrough', function () {
          clearTimeout(timer);
          audioLoaded = true;
          resolve();
        }, { once: true });
        audio.addEventListener('error', function () { clearTimeout(timer); reject(new Error('配音加载失败')); }, { once: true });
        audio.load();
      });
      audio.addEventListener('ended', function () {
        currentFrame = timeline.totalFrames - 1;
        renderAt(currentFrame);
        pause();
      });
      audio.addEventListener('error', function () {
        pause();
        console.error('配音加载失败，请重新 prepare');
      });
    }
    var isolate = opts.isolateScenes !== false;
    var useControls = opts.controls !== false;
    var sceneNodes = isolate ? collectSceneNodes(root, timeline) : [];

    var currentFrame = 0;
    var playing = false;
    var rafId = null;
    var elapsedMs = 0;
    var lastTimestamp = 0;

    var api = {
      easing: easing,
      progress: progress,
      stagger: stagger,
      enter: enter,
      spring: spring,
      range: range,
      breath: breath,
      drawPath: drawPath,
      revealChars: revealChars,
      clamp: clamp,
      lerp: lerp,
      formatTime: formatTime,
      timeline: timeline,
      // 动效配方：入场 + 过冲 + 常驻微动，组件只说「移动多远」，不写手感参数
      motion: motion
    };

    function collectSceneNodes(container, tl) {
      var declared = Array.prototype.slice.call(container.querySelectorAll('[data-a2v-scene]'));
      if (!declared.length) {
        // 网页没有声明场景容器时退化为「全部渲染」，由 render 自行取舍，
        // 但仍返回空数组以便调用方知道隔离模式没有生效。
        return [];
      }
      var byId = {};
      declared.forEach(function (el) {
        var id = el.getAttribute('data-scene-id');
        if (id) {
          byId[id] = el;
        }
      });
      return tl.scenes.map(function (scene, index) {
        return byId[scene.data.id] || declared[index] || null;
      });
    }

    function applySceneVisibility(sceneIndex) {
      if (!sceneNodes.length) {
        return;
      }
      sceneNodes.forEach(function (node, index) {
        if (!node) {
          return;
        }
        var active = index === sceneIndex;
        node.style.display = active ? '' : 'none';
        // 非活动场景移出无障碍树，避免屏幕阅读器读到隐藏内容
        if (active) {
          node.removeAttribute('aria-hidden');
        } else {
          node.setAttribute('aria-hidden', 'true');
        }
      });
    }

    function renderAt(frame) {
      var state = buildState(timeline, frame);
      applySceneVisibility(state.sceneIndex);
      opts.render(state, api);
      if (subtitle) {
        var seconds = frame / timeline.fps;
        var cue = media.cues.find(function (item) { return seconds >= item.start && seconds < item.end; });
        subtitle.textContent = cue ? cue.text : '';
        subtitle.hidden = !cue;
      }
      updateReadout(state);
    }

    function seek(frame) {
      currentFrame = clamp(Math.round(frame), 0, timeline.totalFrames - 1);
      elapsedMs = (currentFrame / timeline.fps) * 1000;
      if (audio && !document.documentElement.classList.contains('a2v-rendering')) {
        audio.currentTime = currentFrame / timeline.fps;
      }
      renderAt(currentFrame);
      return nextPaint().then(function () {
        return currentFrame;
      });
    }

    function play() {
      if (!audioLoaded) return;
      if (audio && document.documentElement.classList.contains('a2v-rendering')) return;
      if (playing) {
        return;
      }
      if (currentFrame >= timeline.totalFrames - 1) {
        // 播放结束后再次点击播放，从头开始；必须同时重置累计时间，
        // 否则 tick 会立刻按旧时间算出末帧并再次停下（表现为「点了没反应」）。
        currentFrame = 0;
        elapsedMs = 0;
        renderAt(0);
      }
      playing = true;
      if (audio) {
        audio.currentTime = currentFrame / timeline.fps;
        audio.play().catch(function (error) { pause(); console.error('配音播放失败: ' + error.message); });
      }
      lastTimestamp = 0;
      setPlayButtonState(true);
      rafId = requestAnimationFrame(tick);
    }

    function pause() {
      if (audio) audio.pause();
      if (!playing) {
        return;
      }
      playing = false;
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      setPlayButtonState(false);
    }

    function tick(timestamp) {
      if (!playing) {
        return;
      }
      if (lastTimestamp) {
        elapsedMs += timestamp - lastTimestamp;
      }
      lastTimestamp = timestamp;
      if (audio) elapsedMs = audio.currentTime * 1000;
      var frame = Math.floor((elapsedMs / 1000) * timeline.fps);
      if (frame >= timeline.totalFrames) {
        // 播放结束停在末帧，重播由用户触发
        currentFrame = timeline.totalFrames - 1;
        renderAt(currentFrame);
        pause();
        return;
      }
      currentFrame = frame;
      renderAt(frame);
      rafId = requestAnimationFrame(tick);
    }

    function updateReadout(state) {
      if (!useControls) {
        return;
      }
      var timeNode = document.querySelector('[data-a2v-time]');
      if (timeNode) {
        timeNode.textContent =
          formatTime(state.frame / timeline.fps) + ' / ' + formatTime(timeline.totalFrames / timeline.fps);
      }
      var range = document.querySelector('[data-a2v-seek]');
      if (range && document.activeElement !== range) {
        range.value = String(state.frame);
      }
    }

    function setPlayButtonState(isPlaying) {
      if (!useControls) {
        return;
      }
      var button = document.querySelector('[data-a2v-play]');
      if (button) {
        button.textContent = isPlaying ? '暂停' : '播放';
        button.setAttribute('aria-label', isPlaying ? '暂停' : '播放');
      }
    }

    function bindControls() {
      if (!useControls) {
        return;
      }
      var playButton = document.querySelector('[data-a2v-play]');
      if (playButton) {
        playButton.addEventListener('click', function () {
          if (playing) {
            pause();
          } else {
            play();
          }
        });
      }
      var replayButton = document.querySelector('[data-a2v-replay]');
      if (replayButton) {
        replayButton.addEventListener('click', function () {
          pause();
          seek(0).then(play);
        });
      }
      var range = document.querySelector('[data-a2v-seek]');
      if (range) {
        range.min = '0';
        range.max = String(timeline.totalFrames - 1);
        range.step = '1';
        range.value = '0';
        range.addEventListener('input', function () {
          pause();
          seek(Number(range.value));
        });
      }
      // 切到后台自动暂停，回来由用户继续，避免离屏累计时间跳帧
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
          pause();
        }
      });
    }

    /**
     * 预览时把 1080 × 1920 的画布整体等比缩放到窗口内。
     * 只改 transform，不改内部布局，因此预览与导出使用同一套坐标。
     * 渲染模式下 base.css 会用 !important 取消缩放，保证像素精确。
     */
    function applyPreviewFit() {
      if (!root || root === document.body) {
        return;
      }
      if (document.documentElement.classList.contains('a2v-rendering')) {
        return;
      }
      var scale = Math.min(
        window.innerWidth / timeline.width,
        window.innerHeight / timeline.height
      );
      if (!isFinite(scale) || scale <= 0) {
        return;
      }
      if (scale >= 1) {
        root.style.transform = '';
        return;
      }
      var offsetX = (window.innerWidth - timeline.width * scale) / 2;
      var offsetY = (window.innerHeight - timeline.height * scale) / 2;
      root.style.transform =
        'translate(' + offsetX + 'px,' + offsetY + 'px) scale(' + scale + ')';
    }

    // 渲染脚本读取的契约。字段名与 references/render-contract.md 一致。
    var contract = {
      version: 1,
      fps: timeline.fps,
      width: timeline.width,
      height: timeline.height,
      durationInFrames: timeline.totalFrames,
      mediaFingerprint: media ? media.sourceFingerprint : null,
      ready: function () {
        return Promise.all([waitForAssets(), audioReady]).then(function () {
          return seek(0);
        });
      },
      seekToFrame: function (frame) {
        pause();
        return seek(frame);
      }
    };

    global.__A2V__ = contract;
    bindControls();
    setPlayButtonState(false);
    applyPreviewFit();
    window.addEventListener('resize', applyPreviewFit);

    var controller = {
      timeline: timeline,
      api: api,
      play: play,
      pause: pause,
      seek: seek,
      replay: function () {
        pause();
        return seek(0).then(play);
      },
      isPlaying: function () {
        return playing;
      },
      currentFrame: function () {
        return currentFrame;
      }
    };

    // 暴露控制器便于在浏览器控制台排查画面问题（A2V.controller.seek(300)）。
    // 渲染脚本只依赖 __A2V__ 契约，不使用这里的接口。
    global.A2V.controller = controller;

    // 首屏先画第 0 帧并保持暂停，避免打开页面就看到动画在跑
    renderAt(0);
    return controller;
  }

  global.A2V = {
    mount: mount,
    readInlineStoryboard: readInlineStoryboard,
    fetchStoryboard: fetchStoryboard,
    layoutStoryboard: layoutStoryboard,
    easing: easing,
    progress: progress,
    stagger: stagger,
    enter: enter,
    spring: spring,
    range: range,
    breath: breath,
    drawPath: drawPath,
    revealChars: revealChars,
    clamp: clamp,
    lerp: lerp,
    formatTime: formatTime,
    // 与传给 render 的 api.motion 是同一份：组件库直接取用，不必等 mount
    motion: motion
  };
})(window);
