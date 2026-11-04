import {describe, expect, it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import registry from './transitions.json';
import {transitionPresentation, transitionTiming, type SceneTransition} from './transitions';

describe('通用转场', () => {
  it('首末帧、单帧和总帧数保持既有窗口语义', () => {
    const timing = transitionTiming(12);
    expect(timing.getDurationInFrames({fps: 30})).toBe(12);
    expect(timing.getProgress({frame: 0, fps: 30})).toBe(0);
    expect(timing.getProgress({frame: 11, fps: 30})).toBe(1);
    expect(transitionTiming(1).getProgress({frame: 0, fps: 60})).toBe(1);
    expect(transitionTiming(1).getProgress({frame: -1, fps: 60})).toBe(0);
  });
  it('全部登记的呈现可在横竖屏重复求值，不产生无效几何', () => {
    for (const name of Object.keys(registry) as SceneTransition[]) {
      if (name === 'cut') continue;
      for (const [width, height] of [[1920, 1080], [1080, 1920]]) {
        const {component: Component, props} = transitionPresentation(name, width, height);
        const draw = () => renderToStaticMarkup(<Component passedProps={props} presentationProgress={.5}
          presentationDirection="entering" presentationDurationInFrames={12} bothEnteringAndExiting={false}
          onElementImage={() => undefined} onUnmount={() => undefined}>场景</Component>);
        expect(draw()).toBe(draw());
        expect(draw()).not.toMatch(/NaN|Infinity/);
      }
    }
  });
});
