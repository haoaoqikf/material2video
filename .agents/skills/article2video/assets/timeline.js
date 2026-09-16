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
 *   - 画面只由 state.frame 推导，禁止读取 Date.now()、Math.random() 或
 *     依赖 CSS animation/transition 的播放时间；
 *   - 同一帧重复渲染必须得到同一画面。
 *
 * 为什么不用 CSS 动画：渲染脚本按帧号截图，CSS 动画由浏览器时钟驱动，
 * 截图时刻与动画时间无法对齐，导出的视频会出现随机闪烁。
 */
(function (global) {
  'use strict';

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
    });
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
      clamp: clamp,
      lerp: lerp,
      formatTime: formatTime,
      timeline: timeline
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
      updateReadout(state);
    }

    function seek(frame) {
      currentFrame = clamp(Math.round(frame), 0, timeline.totalFrames - 1);
      elapsedMs = (currentFrame / timeline.fps) * 1000;
      renderAt(currentFrame);
      return nextPaint().then(function () {
        return currentFrame;
      });
    }

    function play() {
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
      lastTimestamp = 0;
      setPlayButtonState(true);
      rafId = requestAnimationFrame(tick);
    }

    function pause() {
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
      var frame = Math.floor((elapsedMs / 1000) * timeline.fps);
      if (frame >= timeline.totalFrames - 1) {
        // 播放结束停在末帧，重播由用户触发
        renderAt(timeline.totalFrames - 1);
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
      ready: function () {
        return waitForAssets().then(function () {
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
    clamp: clamp,
    lerp: lerp,
    formatTime: formatTime
  };
})(window);
