/** 正式片、代表性试制与无字验证共用同一个画面，避免试制相机和正式实现分离。 */
import type {CodeSceneProps} from '../../src/code-scene/context';
import {MINT} from '../capital-motion';
import type {FilmClock} from '../capital-motion';
import {fullFrame} from '../mint-film-motion';
import CapitalStage from './capital-stage';
import FilmTitles from './mint-film-titles';

export default function MintFilmView({config, clock, ready}: {
  config: CodeSceneProps; clock: FilmClock; ready: () => void;
}) {
  return <div style={{position: 'relative', width: config.width, height: config.height,
    background: MINT.background, overflow: 'hidden'}}>
    <CapitalStage state={fullFrame(clock)} width={config.width} height={config.height}
      density={config.captureScale ?? 1} onReady={ready}/>
    {!config.props.hideText && <FilmTitles clock={clock}/>}
  </div>;
}
