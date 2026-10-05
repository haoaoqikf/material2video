import type { FC } from 'react';
import type { CalculateMetadataFunction } from 'remotion';
import { Composition } from 'remotion';
import type { A2VProps } from './compositions/A2VComposition';
import { A2VComposition } from './compositions/A2VComposition';
import { A2VCompositionV4, type A2VCompositionV4Props } from './compositions/A2VCompositionV4';
import { EMPTY_STORYBOARD } from './schema/storyboard';
import { totalFrames } from './runtime/timeline';
import { resolveStoryboardV4 } from './runtime/timelineV4';
import { FinancialTimeSeries, type FinancialTimeSeriesProps } from './compositions/FinancialTimeSeries';
import type { StoryboardV4 } from './schema/storyboardV4';
import './styles/index.css';

/**
 * 时长、帧率与尺寸都从分镜推导，**不在注册时写死**。
 *
 * 这样真实作品只需要把分镜作为 props 传进来（`--props <storyboard.json>`），
 * 不需要每次改 composition 的注册参数。分镜是内容层的单一真源，
 * 画面参数必须由它推导，而不是两处维护。
 */
type ActiveProps = A2VProps | A2VCompositionV4Props;

const ActiveComposition: FC<ActiveProps> = (props) => {
  const raw = props as unknown as { version: number };
  return raw.version === 4
    ? <A2VCompositionV4 {...(props as A2VCompositionV4Props)} />
    : <A2VComposition {...(props as unknown as A2VProps)} />;
};

const calculateA2V: CalculateMetadataFunction<ActiveProps> = ({ props }) => {
  const durationInFrames = props.version === 4
    ? resolveStoryboardV4(props as StoryboardV4, props.mediaTimeline).totalFrames
    : totalFrames(props as A2VProps);
  return {
    durationInFrames,
    fps: props.fps,
    width: props.width,
    height: props.height,
  };
};

export const RemotionRoot: FC = () => {
  return (
    <>
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
      <Composition
        id="FinancialTimeSeries"
        component={FinancialTimeSeries}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{} as FinancialTimeSeriesProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames,
          fps: props.fps,
          width: props.width,
          height: props.height,
        })}
      />
    </>
  );
};
