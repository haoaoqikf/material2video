/** 原生局部试制：保留正式场景与绝对时钟，只截取指定窗口，不另做样片画面。 */
import {SceneContextProvider, useSceneContext, type CodeSceneProps} from '../src/code-scene/context';
import Journey from './journey';
import {trialConfig} from './trial-config';

export default function Trial(config: CodeSceneProps) {
  const clock = useSceneContext();
  const start = Number(config.props.windowStartFrame ?? 0);
  const scene = trialConfig(config);
  const total = scene.durationInFrames;
  const frame = start + Math.round(clock.elapsedSeconds * config.fps);
  return <SceneContextProvider.Provider value={{...clock, elapsedSeconds: frame / config.fps,
    progress: frame / total, globalFrame: frame, globalSeconds: frame / config.fps}}>
    <Journey {...scene}/>
  </SceneContextProvider.Provider>;
}
