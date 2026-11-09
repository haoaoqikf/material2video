/** 用户要求重新设计字体和背景：九帧编码三幅静态选案，不修改正式视频入口。 */
import {useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import RedesignPoster from './components/redesign-posters';
import type {RedesignVariant} from './components/redesign-stage';

export default function TypographyRedesign(config: CodeSceneProps) {
  const clock = useSceneContext();
  const index = Math.min(2, Math.floor((clock.elapsedSeconds * config.fps + .001) / 3)) as RedesignVariant;
  return <div style={{position: 'relative', width: config.width, height: config.height,
    overflow: 'hidden'}}>
    <RedesignPoster variant={index} density={config.captureScale ?? 1} ready={clock.ready}/>
  </div>;
}
