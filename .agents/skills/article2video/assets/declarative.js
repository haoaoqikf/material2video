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
    document.documentElement.dataset.a2vTheme = (storyboard.visual || {}).theme || 'dark';
    document.documentElement.style.setProperty('--a2v-width', (storyboard.width || 1080) + 'px');
    document.documentElement.style.setProperty('--a2v-height', (storyboard.height || 1920) + 'px');
    var stage = document.querySelector('[data-a2v-stage]');
    storyboard.scenes.forEach(function (scene) {
      var section = document.createElement('section');
      section.setAttribute('data-a2v-scene', '');
      section.dataset.sceneId = scene.id;
      section.dataset.layout = (scene.visual || {}).layout || 'center';
      var host = document.createElement('div');
      host.className = 'a2v-safe';
      host.setAttribute('data-a2v-figure', '');
      section.appendChild(host);
      stage.appendChild(section);
    });
    A2V.mount({ storyboard: storyboard, render: function (state, api) {
      A2V.figures.renderScene(state, api, { defaults: DEFAULT_FIGURES });
    } });
    return window.__A2V__.ready();
  }).catch(function (error) {
    document.body.textContent = '页面初始化失败：' + error.message;
    throw error;
  });
})();
