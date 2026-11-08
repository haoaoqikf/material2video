/** 合成层转场；代码场景不依赖 Remotion hooks。 */
import {linearTiming, type TransitionTiming, type TransitionPresentation} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide, type SlideDirection} from '@remotion/transitions/slide';
import {wipe, type WipeDirection} from '@remotion/transitions/wipe';
import {iris} from '@remotion/transitions/iris';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import registry from './transitions.json';

export type SceneTransition = keyof typeof registry;

// 官方工厂已将组件与其 props 成对绑定；组合不同工厂时仅擦除泛型，不改运行时配对。
function presentation<P extends Record<string, unknown>>(value: TransitionPresentation<P>) {
  return value as unknown as TransitionPresentation<Record<string, unknown>>;
}

export function transitionPresentation(name: Exclude<SceneTransition, 'cut'>, width: number, height: number) {
  const entry = registry[name];
  switch (entry.presentation) {
    case 'slide': return presentation(slide({direction: (entry as {direction: SlideDirection}).direction}));
    case 'wipe': return presentation(wipe({direction: (entry as {direction: WipeDirection}).direction}));
    case 'iris': return presentation(iris({width, height}));
    case 'clock-wipe': return presentation(clockWipe({width, height}));
    case 'fade': return presentation(fade());
    default: throw new Error(`未知转场：${name}`);
  }
}

/** 总长度仍为 N 帧，进度在 N-1 达到 1；单帧直接落在完成态。 */
export function transitionTiming(frames: number): TransitionTiming {
  const timing = linearTiming({durationInFrames: frames});
  return {...timing, getProgress: args => frames === 1 ? (args.frame < 0 ? 0 : 1)
    : timing.getProgress({...args, frame: args.frame * frames / (frames - 1)})};
}
