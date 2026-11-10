import storyboard from '../storyboard.json';
import journey from './journey-plan.json';
import type {CodeSceneProps} from '../src/code-scene/context';

/** 试制直接读取正式分镜，避免把整条相机路径放进Windows命令行。 */
export function trialConfig(config: CodeSceneProps): CodeSceneProps {
  const scene = storyboard.scenes[0];
  let cursor = scene.leadInFrames;
  const windows: CodeSceneProps['segmentWindows'] = {};
  for (let index = 0; index < scene.narrationSegments.length; index++) {
    const segment = scene.narrationSegments[index];
    const measured = journey.stations[index];
    if (segment.id !== `${measured.body}-line` || segment.text !== measured.text) {
      throw new Error(`试制旁白与行程量测不一致：${segment.id}`);
    }
    windows[segment.id] = {startFrame: cursor, endFrame: cursor + measured.frames};
    cursor += measured.frames + (segment.holdFrames ?? 0);
  }
  return {...config, props: {...scene.content.props, ...config.props},
    durationInFrames: scene.durationFrames, segmentWindows: windows};
}
