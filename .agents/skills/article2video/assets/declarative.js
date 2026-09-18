(function () {
  'use strict';

  // 与 scripts/a2v/catalog.py 的 DEFAULT_KINDS 由测试对照。
  var DEFAULT_FIGURES = {
    title: 'balance', quote: 'gap', comparison: 'versus', list: 'iceberg',
    diagram: 'loop', timeline: 'stairs', conclusion: 'exchange', number: 'number'
  };

  var source = new URLSearchParams(location.search).get('a2v-storyboard');
  if (!source || !source.startsWith('/') || source.startsWith('//')) {
    throw new Error('缺少有效的 a2v-storyboard 路径');
  }

  A2V.fetchStoryboard(source).then(function (storyboard) {
    var visual = storyboard.visual || {};
    document.documentElement.dataset.a2vTheme = visual.theme || 'dark';
    /*
     * 设计语言预设：只有分镜显式声明 visual.preset 时才启用。
     * 未声明时不加 data-a2v-preset，keynote.css 里的主题块与版式规则都不生效，
     * 页面结构与样式与引入预设之前完全一致，既有视频逐帧不变。
     */
    var preset = visual.preset || '';
    if (preset) document.documentElement.dataset.a2vPreset = preset;

    document.documentElement.style.setProperty('--a2v-width', (storyboard.width || 1080) + 'px');
    document.documentElement.style.setProperty('--a2v-height', (storyboard.height || 1920) + 'px');

    var stage = document.querySelector('[data-a2v-stage]');
    storyboard.scenes.forEach(function (scene, index) {
      var section = document.createElement('section');
      section.setAttribute('data-a2v-scene', '');
      section.dataset.sceneId = scene.id;
      section.dataset.layout = (scene.visual || {}).layout || 'center';
      var host = document.createElement('div');
      host.className = 'a2v-safe';
      host.setAttribute('data-a2v-figure', '');
      section.appendChild(host);
      if (preset) section.appendChild(sceneIndexBar(storyboard, index));
      stage.appendChild(section);
    });

    A2V.mount({ storyboard: storyboard, render: function (state, api) {
      A2V.figures.renderScene(state, api, { defaults: DEFAULT_FIGURES });
      if (preset && A2V.type) {
        /*
         * 组件画完之后按字号阶取档。排在组件之后是必须的：文本内容与元素尺寸
         * 都由组件决定，先量就会量到空元素。autofit 只在内容签名变化时重算，
         * 因此逐帧调用不会带来抖动，也不会重复触发重排。
         *
         * 可用宽度必须显式传容器（`.a2v-safe`）：要回答的是「这一行放得进画面吗」，
         * 而画面宽度由容器决定。让引擎退回元素自身的宽度是循环论证——收缩适应的
         * 元素宽度就等于自己那行文字，永远除得尽。
         */
        var section = state.scene.id ? sceneById(state.scene.id) : null;
        A2V.type.autofit(section, {
          availableWidth: section ? section.querySelector('.a2v-safe') : 0
        });
      }
    } });
    return window.__A2V__.ready();
  }).catch(function (error) {
    document.body.textContent = '页面初始化失败：' + error.message;
    throw error;
  });

  /** 幕角标：**作者写的定位词** + 幕号/总幕数。给画面一个稳定锚点，不参与构图。
   *
   * 这里原先直接写 `scene.type`，于是画面左上角显示的是分镜的**内部类型名**：
   * TITLE / LIST / TIMELINE / NUMBER / CONCLUSION。那是 schema 字段名，
   * 不是给读者看的字——既没有信息量（读者不需要知道"这是一条时间线"），
   * 也和整屏中文格格不入。现在角标只能来自 `visual.kicker`。
   *
   * 没写 `kicker` 时把这一格留空，而**不回落到类型名**：
   * 一个内部标识符永远不该出现在画面上。留空而不是删掉整个 span，
   * 是因为这一行是 `justify-content: space-between`——少一个子元素会把幕号
   * 从右边甩到左边，那是版式变化，不是"少了一个角标"。 */
  function sceneIndexBar(storyboard, index) {
    var scene = storyboard.scenes[index];
    var bar = document.createElement('div');
    bar.className = 'a2v-scene-index';

    var kind = document.createElement('span');
    kind.textContent = String((scene.visual || {}).kicker || '').trim();
    var number = document.createElement('span');
    number.className = 'a2v-scene-number';
    number.textContent = pad(index + 1) + ' / ' + pad(storyboard.scenes.length);

    bar.appendChild(kind);
    bar.appendChild(number);
    return bar;
  }

  function sceneById(id) {
    return document.querySelector('[data-scene-id="' + id + '"]');
  }

  function pad(value) {
    return (value < 10 ? '0' : '') + value;
  }
})();
