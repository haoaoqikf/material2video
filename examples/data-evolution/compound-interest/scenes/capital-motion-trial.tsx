import {useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import {filmClock} from './capital-motion';
import MintFilmView from './components/mint-film-view';

export default function CapitalMotionTrial(config: CodeSceneProps) {
  const clock = useSceneContext();
  const origin = filmClock(0, config.fps);
  const frame = clock.elapsedSeconds * config.fps;
  const coreFrames = origin.at('compare-start') - origin.at('core-start');
  const both = config.props.section === 'both';
  const core = both ? frame < coreFrames : config.props.section !== 'growth';
  const local = frame - (both && !core ? coreFrames : 0);
  const at = origin.atFrame(origin.at(core ? 'core-start' : 'growth-start') + local);
  return <MintFilmView config={config} clock={at} ready={clock.ready}/>;
}
