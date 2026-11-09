/** 三张静态设计的同源网页入口；编码只验证原生输出，不表示动画、节奏或声音通过。 */
import {useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import CapitalStage from './components/capital-stage';
import {designFrame} from './capital-state';
import CapitalTitles from './components/capital-titles';

export default function CapitalTrial(config: CodeSceneProps) {
  const clock = useSceneContext();
  const panel = Math.min(2, Math.floor((clock.elapsedSeconds * config.fps + .001) / 3));
  const state = designFrame(panel);
  return <div style={{width: config.width, height: config.height, position: 'relative', overflow: 'hidden', background: '#0c0e13'}}>
    <CapitalStage state={state} width={config.width} height={config.height}
      density={config.captureScale ?? 1} onReady={clock.ready}/>
    <CapitalTitles state={state}/>
  </div>;
}
