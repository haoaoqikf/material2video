import { describe, expect, it } from 'vitest';
import { activeSubtitleCues, sceneOpacityAtFrame, type GeneralScene } from './GeneralVideo';

const incoming = {
  id: 'second', type: 'graphic', durationInFrames: 60, startFrame: 48, endFrame: 108,
  transitionFrames: 12,
} as GeneralScene;

describe('general video timeline rendering', () => {
  it('fades the incoming scene over a fully visible outgoing scene', () => {
    expect(sceneOpacityAtFrame(incoming, 48)).toBe(0);
    expect(sceneOpacityAtFrame(incoming, 53)).toBeCloseTo(5 / 11);
    expect(sceneOpacityAtFrame(incoming, 59)).toBe(1);
    expect(sceneOpacityAtFrame(incoming, 60)).toBe(1);
    expect(sceneOpacityAtFrame({ ...incoming, transitionFrames: 0 }, 48)).toBe(1);
  });

  it('selects every subtitle active on the global frame, including overlap frames', () => {
    const cues = [
      { startFrame: 40, endFrame: 55, text: '前一幕' },
      { startFrame: 48, endFrame: 62, text: '后一幕' },
    ];
    expect(activeSubtitleCues(cues, 48).map(cue => cue.text)).toEqual(['前一幕', '后一幕']);
    expect(activeSubtitleCues(cues, 55).map(cue => cue.text)).toEqual(['后一幕']);
    expect(activeSubtitleCues(cues, 62)).toEqual([]);
  });
});
