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
  it('缓动的端点固定、单调，且线性控制点等于旧行为', () => {
    const velvet = [0.37, 0, 0.63, 1];
    expect(revealProgress(0, 0, 36, velvet)).toBe(0);
    expect(revealProgress(36, 0, 36, velvet)).toBe(1);
    const eased = Array.from({length: 37}, (_, frame) => revealProgress(frame, 0, 36, velvet));
    for (let frame = 1; frame < eased.length; frame++) expect(eased[frame]).toBeGreaterThanOrEqual(eased[frame - 1]);
    // `[0,0,1,1]` 即线性：必须与不传缓动时逐帧相等，既有画面才可能不变
    for (let frame = 0; frame <= 36; frame++) {
      expect(revealProgress(frame, 0, 36, [0, 0, 1, 1])).toBe(revealProgress(frame, 0, 36));
    }
  });
  it('缓动在进场前段慢于线性、后段快于线性', () => {
    const velvet = [0.37, 0, 0.63, 1];
    const quarter = revealProgress(9, 0, 36, velvet);
    const threeQuarters = revealProgress(27, 0, 36, velvet);
    expect(quarter).toBeGreaterThan(0.1);
    expect(quarter).toBeLessThan(0.25);
    expect(threeQuarters).toBeGreaterThan(0.75);
    expect(threeQuarters).toBeLessThan(0.9);
  });
  it('图位置仅依赖预编译分层', () => {
    const scene: ExplainerScene = {id: 'cause', template: 'cause', startFrame: 0, endFrame: 72, durationInFrames: 72, transitionFrames: 0,
      content: {title: '原因', nodes: ['a', 'b', 'c'].map(id => ({id, text: id, segmentId: 'line'}))},
      segmentWindows: {line: {startFrame: 0, endFrame: 60}}, levels: {a: 0, b: 1, c: 1}};
    const first = graphPositions(scene); expect(graphPositions(scene)).toEqual(first);
    expect(first.b.y).toBe(first.c.y); expect(first.a.y).toBeLessThan(first.b.y);
  });
});
