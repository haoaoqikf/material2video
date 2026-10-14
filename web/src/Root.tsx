import type { FC } from 'react';
import type { CalculateMetadataFunction } from 'remotion';
import { Composition } from 'remotion';
import type { M2VProps } from './compositions/M2VComposition';
import { M2VComposition } from './compositions/M2VComposition';
import { M2VCompositionV4, type M2VCompositionV4Props } from './compositions/M2VCompositionV4';
import { EMPTY_STORYBOARD } from './schema/storyboard';
import { totalFrames } from './runtime/timeline';
import { resolveStoryboardV4 } from './runtime/timelineV4';
import { FinancialTimeSeries, type FinancialTimeSeriesProps } from './compositions/FinancialTimeSeries';
import type { StoryboardV4 } from './schema/storyboardV4';
import './styles/index.css';
import { GeneralVideo, type GeneralVideoProps } from './compositions/GeneralVideo';
import { HousingTimeSeries, type HousingTimeSeriesProps } from './compositions/HousingTimeSeries';
import { ArticleExplainer, type ArticleExplainerProps } from './compositions/ArticleExplainer';

/**
 * 时长、帧率与尺寸都从分镜推导，**不在注册时写死**。
 *
 * 这样真实作品只需要把分镜作为 props 传进来（`--props <storyboard.json>`），
 * 不需要每次改 composition 的注册参数。分镜是内容层的单一真源，
 * 画面参数必须由它推导，而不是两处维护。
 */
type ActiveProps = M2VProps | M2VCompositionV4Props;

const ActiveComposition: FC<ActiveProps> = (props) => {
  const raw = props as unknown as { version: number };
  return raw.version === 4
    ? <M2VCompositionV4 {...(props as M2VCompositionV4Props)} />
    : <M2VComposition {...(props as unknown as M2VProps)} />;
};

const calculateM2V: CalculateMetadataFunction<ActiveProps> = ({ props }) => {
  const durationInFrames = props.version === 4
    ? resolveStoryboardV4(props as StoryboardV4, props.mediaTimeline).totalFrames
    : totalFrames(props as M2VProps);
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
      <Composition id="ArticleExplainer" component={ArticleExplainer} durationInFrames={1} fps={30} width={1080} height={1920}
        defaultProps={{version: 5, schemaVersion: 5, fps: 30, width: 1080, height: 1920, title: '', visual: {theme: 'dark'},
          durationInFrames: 1, compiledScenes: [], subtitleCues: []} as ArticleExplainerProps}
        calculateMetadata={({ props }) => ({ durationInFrames: props.durationInFrames, fps: props.fps, width: props.width, height: props.height })} />
      <Composition
        id="M2V"
        component={ActiveComposition}
        durationInFrames={totalFrames(EMPTY_STORYBOARD)}
        fps={EMPTY_STORYBOARD.fps}
        width={EMPTY_STORYBOARD.width}
        height={EMPTY_STORYBOARD.height}
        defaultProps={EMPTY_STORYBOARD}
        calculateMetadata={calculateM2V}
      />
      <Composition
        id="FinancialTimeSeries"
        component={FinancialTimeSeries}
        durationInFrames={180}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{} as FinancialTimeSeriesProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames,
          fps: props.fps,
          width: props.width,
          height: props.height,
        })}
      />
      <Composition
        id="HousingTimeSeries"
        component={HousingTimeSeries}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{} as HousingTimeSeriesProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames,
          fps: props.fps,
          width: props.width,
          height: props.height,
        })}
      />
      <Composition
        id="GeneralVideo"
        component={GeneralVideo}
        durationInFrames={1}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ schemaVersion: 1, fps: 30, width: 1080, height: 1920, durationInFrames: 1, compiledScenes: [] } as GeneralVideoProps}
        calculateMetadata={({ props }) => ({ durationInFrames: props.durationInFrames, fps: props.fps,
          width: props.width, height: props.height })}
      />
    </>
  );
};
