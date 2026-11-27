import { DEFAULT_FPS } from './video-config';
import type { FC } from 'react';
import { Composition } from 'remotion';
import { SceneFilm, type SceneFilmProps } from './scene-film/SceneFilm';
import { DEFAULT_FRAME } from './frames';
import './styles/index.css';

/**
 * 三类作品共用一个 composition。
 *
 * 时长、帧率与尺寸都从作品材料推导，**不在注册时写死**：材料是内容层的
 * 单一真源，画面参数必须由它推导，而不是两处维护。注册时的时长只是占位。
 */
export const RemotionRoot: FC = () => {
  return (
      <Composition
        id="SceneFilm"
        component={SceneFilm}
        durationInFrames={1}
        fps={DEFAULT_FPS}
        width={DEFAULT_FRAME.width}
        height={DEFAULT_FRAME.height}
        defaultProps={{ version: 9, schemaVersion: 9, fps: DEFAULT_FPS, width: DEFAULT_FRAME.width,
          height: DEFAULT_FRAME.height, title: '', subtitle: DEFAULT_FRAME.subtitle,
          durationInFrames: 1, compiledScenes: [], subtitleCues: [] } as SceneFilmProps}
        calculateMetadata={({ props }) => ({ durationInFrames: props.durationInFrames, fps: props.fps, width: props.width, height: props.height })}
      />
  );
};
