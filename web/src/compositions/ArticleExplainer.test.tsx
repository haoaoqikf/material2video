import {describe, expect, it} from 'vitest';
import {highlightParts, revealProgress, selectedStep, graphPositions, type ExplainerScene} from './ArticleExplainer';

describe('讲解的确定性展示', () => {
  it('在语音段起点渐入，8 帧后稳定；随机求帧结果相同', () => {
    const ordered = Array.from({length: 40}, (_, frame) => revealProgress(frame, 12));
    for (const frame of [25, 0, 12, 20, 13, 25]) expect(revealProgress(frame, 12)).toBe(ordered[frame]);
    expect(ordered[12]).toBe(0); expect(ordered[20]).toBe(1);
  });
  it('步骤跟随旁白并在阅读尾段保留最后一步', () => {
    const scene: ExplainerScene = {id: 'steps', template: 'steps', startFrame: 0, endFrame: 72, durationInFrames: 72, transitionFrames: 0,
      content: {title: '方法', items: [{text: '观察', segmentId: 'a'}, {text: '修正', segmentId: 'b'}]},
      segmentWindows: {a: {startFrame: 0, endFrame: 30}, b: {startFrame: 30, endFrame: 60}}};
    expect(selectedStep(scene, -1)).toBe(-1); expect(selectedStep(scene, 29)).toBe(0);
    expect(selectedStep(scene, 30)).toBe(1); expect(selectedStep(scene, 71)).toBe(1);
  });
  it('关键词按最长匹配，不生成 HTML', () => {
    expect(highlightParts('观察反馈再修正', ['反馈', '观察反馈'])).toEqual([
      {text: '观察反馈', highlight: true}, {text: '再修正', highlight: false}]);
    expect(highlightParts('<script>', [])).toEqual([{text: '<script>', highlight: false}]);
  });
  it('图位置仅依赖预编译分层', () => {
    const scene: ExplainerScene = {id: 'cause', template: 'cause', startFrame: 0, endFrame: 72, durationInFrames: 72, transitionFrames: 0,
      content: {title: '原因', nodes: ['a', 'b', 'c'].map(id => ({id, text: id, segmentId: 'line'}))},
      segmentWindows: {line: {startFrame: 0, endFrame: 60}}, levels: {a: 0, b: 1, c: 1}};
    const first = graphPositions(scene); expect(graphPositions(scene)).toEqual(first);
    expect(first.b.y).toBe(first.c.y); expect(first.a.y).toBeLessThan(first.b.y);
  });
});
