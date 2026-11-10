/** 本片全帧驱动场景的诊断取样入口；不作为正式录制或完整预演。 */
import {SceneContextProvider, useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import Journey from './journey';
import {trialConfig} from './trial-config';

export default function Inspection(config: CodeSceneProps) {
  const clock = useSceneContext();
  const frames = config.props.inspectionFrames as number[];
  const index = Math.min(frames.length - 1, Math.max(0, Math.round(clock.elapsedSeconds * config.fps)));
  const frame = frames[index];
  const scene = trialConfig(config);
  const duration = scene.durationInFrames;
  return <SceneContextProvider.Provider value={{...clock, elapsedSeconds: frame / 60, progress: frame / duration}}>
    <Journey {...scene} fps={60}/>
  </SceneContextProvider.Provider>;
}
