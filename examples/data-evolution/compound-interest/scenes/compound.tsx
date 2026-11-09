import {useSceneContext} from '../src/code-scene/context';
import type {CodeSceneProps} from '../src/code-scene/context';
import {filmClock} from './capital-motion';
import MintFilmView from './components/mint-film-view';

export default function Compound(config: CodeSceneProps) {
  const clock = useSceneContext();
  const at = filmClock(clock.elapsedSeconds * config.fps, config.fps, config.eventFrames);
  return <MintFilmView config={config} clock={at} ready={clock.ready}/>;
}
