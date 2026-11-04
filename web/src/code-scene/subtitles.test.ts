import {describe, expect, it} from 'vitest';
import {
  activeScreenSubtitle, screenSubtitleEnvelope, splitEmphasis, splitScreenSubtitle, screenSubtitleCharacters,
} from './subtitles';

describe('屏幕字幕时间与切分', () => {
  it('字符使用绝对帧间隔，长句末字不会被整句包络提前拉出', () => {
    const args = {text: '积累，继续生长', startFrame: 10, staggerFrames: 2, revealFrames: 8, punctuationFrames: 3};
    const start = screenSubtitleCharacters({...args, frame: 10});
    expect(start.map(x => x.startFrame)).toEqual([10, 12, 14, 19, 21, 23, 25]);
    expect(screenSubtitleCharacters({...args, frame: 18})[3].progress).toBe(0);
    expect(screenSubtitleCharacters({...args, frame: 32}).at(-1)?.progress).toBeLessThan(1);
    expect(screenSubtitleCharacters({...args, frame: 33}).every(x => x.progress === 1)).toBe(true);
    const later = screenSubtitleCharacters({...args, frame: 21});
    screenSubtitleCharacters({...args, frame: 80});
    expect(screenSubtitleCharacters({...args, frame: 21})).toEqual(later);
  });
  const items = [
    {startFrame: 10, endFrame: 20, text: '第一行\nFirst line'},
    {startFrame: 30, endFrame: 40, text: '第二行\nSecond line'},
  ];

  it('激活窗口左闭右开', () => {
    expect(activeScreenSubtitle(items, 9)).toBeNull();
    expect(activeScreenSubtitle(items, 10)?.text).toContain('第一行');
    expect(activeScreenSubtitle(items, 19)?.text).toContain('第一行');
    expect(activeScreenSubtitle(items, 20)).toBeNull();
    expect(activeScreenSubtitle(items, 30)?.text).toContain('第二行');
  });

  it('按换行切行，超出上限明确失败', () => {
    expect(splitScreenSubtitle('中文\nEnglish', 2)).toEqual(['中文', 'English']);
    expect(() => splitScreenSubtitle('一\n二\n三', 2)).toThrow('最多 2 行');
    expect(() => splitScreenSubtitle('  ', 2)).toThrow('不能为空');
  });

  it('进出包络在窗口外为 0，窗口内保留量测下限', () => {
    expect(screenSubtitleEnvelope({frame: 9, startFrame: 10, endFrame: 20})).toBe(0);
    expect(screenSubtitleEnvelope({frame: 20, startFrame: 10, endFrame: 20})).toBe(0);
    expect(screenSubtitleEnvelope({frame: 10, startFrame: 10, endFrame: 20})).toBeGreaterThanOrEqual(0.2);
    expect(screenSubtitleEnvelope({frame: 15, startFrame: 10, endFrame: 20})).toBe(1);
    expect(screenSubtitleEnvelope({frame: 19, startFrame: 10, endFrame: 20})).toBeGreaterThanOrEqual(0.2);
  });

  it('关键词切分不改变原文，只标记 emphasis', () => {
    const segments = splitEmphasis('从 3 到 1000，标准误约小 18 倍。', /3|1000|18/);
    expect(segments.map(segment => segment.text).join('')).toBe('从 3 到 1000，标准误约小 18 倍。');
    expect(segments.filter(segment => segment.emphasis).map(segment => segment.text)).toEqual(['3', '1000', '18']);
  });

  it('无关键模式返回整段非强调', () => {
    expect(splitEmphasis('普通字幕')).toEqual([{text: '普通字幕', emphasis: false}]);
  });
});
