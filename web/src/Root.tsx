import type { FC } from 'react';
import type { CalculateMetadataFunction } from 'remotion';
import { Composition } from 'remotion';
import type { A2VProps } from './compositions/A2VComposition';
import { ActiveComposition } from '../.gen/active-composition';
import { EMPTY_STORYBOARD } from './schema/storyboard';
import { totalFrames } from './runtime/timeline';
import './styles/index.css';

/**
 * 时长、帧率与尺寸都从分镜推导，**不在注册时写死**。
 *
 * 这样真实作品只需要把分镜作为 props 传进来（`--props <storyboard.json>`），
 * 不需要每次改 composition 的注册参数。分镜是内容层的单一真源，
 * 画面参数必须由它推导，而不是两处维护。
 */
const calculateA2V: CalculateMetadataFunction<A2VProps> = ({ props }) => {
  return {
    durationInFrames: totalFrames(props),
    fps: props.fps,
    width: props.width,
    height: props.height,
  };
};

export const RemotionRoot: FC = () => {
  return (
    <Composition
      id="A2V"
      component={ActiveComposition}
      durationInFrames={totalFrames(EMPTY_STORYBOARD)}
      fps={EMPTY_STORYBOARD.fps}
      width={EMPTY_STORYBOARD.width}
      height={EMPTY_STORYBOARD.height}
      defaultProps={EMPTY_STORYBOARD}
      calculateMetadata={calculateA2V}
    />
  );
};
