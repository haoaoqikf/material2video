/** 用户要求重做字体与背景：同一结果内容的三种静态设计，每三帧一幅。 */
import {useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import EditorialPoster from './components/editorial-posters';
import type {EditorialVariant} from './components/editorial-stage';

export default function TypographyRedesign(config: CodeSceneProps) {
  const clock = useSceneContext();
  const index = Math.min(2, Math.floor((clock.elapsedSeconds * config.fps + .001) / 3));
  return <EditorialPoster variant={index as EditorialVariant} density={config.captureScale ?? 1} ready={clock.ready}/>;
}
