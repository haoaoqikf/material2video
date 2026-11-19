import {useEffect, useRef, useState} from 'react';
import {Player, type PlayerRef} from '@remotion/player';
import {SceneFilm, type SceneFilmProps} from '@/scene-film/SceneFilm';
import {ensureFonts} from '@/fonts';
import {settleOnFrame, type M2VContractV6} from '../contract/bridge';

async function readyImages() {
  await Promise.all(Array.from(document.images).map(image => image.decode()));
}
export function ExplainerContractApp() {
  const preview = new URLSearchParams(location.search).get('video-preview') === '1';
  const [props, setProps] = useState<SceneFilmProps | null>(null);
  const [error, setError] = useState('');
  const player = useRef<PlayerRef>(null);
  useEffect(() => {
    const url = new URLSearchParams(location.search).get('m2v-storyboard')!;
    let cancelled = false;
    void fetch(url).then(async response => {
      if (!response.ok) throw new Error(`讲解材料读取失败：HTTP ${response.status}`);
      const data = await response.json() as SceneFilmProps;
      if (data.version !== 9 || !data.compiledScenes || !data.durationInFrames) throw new Error('需要已准备的 v9 分镜材料');
      if (!cancelled) setProps(data);
    }).catch(cause => {if (!cancelled) setError(String(cause));});
    return () => {cancelled = true;};
  }, []);
  useEffect(() => {
    const current = player.current;
    if (!props || !current) return;
    const contract: M2VContractV6 = {version: 6, fps: props.fps, width: props.width, height: props.height,
      durationInFrames: props.durationInFrames,
      currentFrame: () => current.getCurrentFrame(),
      ready: async () => {await ensureFonts(); await settleOnFrame(current, 0); await readyImages();},
      seekToFrame: async frame => {
        if (!Number.isInteger(frame) || frame < 0 || frame >= props.durationInFrames) throw new Error('讲解求帧越界');
        await settleOnFrame(current, frame); await readyImages();
      }};
    window.__M2V__ = contract;
    return () => {if (window.__M2V__ === contract) delete window.__M2V__;};
  }, [props]);
  if (error) return <div data-m2v-contract-error="">{error}</div>;
  if (!props) return null;
  return <Player ref={player} component={SceneFilm} inputProps={props} durationInFrames={props.durationInFrames}
    fps={props.fps} compositionWidth={props.width} compositionHeight={props.height}
    style={preview ? {width: `min(100vw, ${100 * props.width / props.height}vh)`, aspectRatio: `${props.width}/${props.height}`}
      : {width: props.width, height: props.height}}
    controls={preview} clickToPlay={preview} acknowledgeRemotionLicense/>;
}
