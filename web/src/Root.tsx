import type { FC } from 'react';
import { Composition } from 'remotion';
import { ArticleExplainer, type ArticleExplainerProps } from './compositions/ArticleExplainer';
import { FinancialTimeSeries, type FinancialTimeSeriesProps } from './compositions/FinancialTimeSeries';
import { HousingTimeSeries, type HousingTimeSeriesProps } from './compositions/HousingTimeSeries';
import './styles/index.css';

/**
 * 注册全部 composition。
 *
 * 时长、帧率与尺寸都从作品材料推导，**不在注册时写死**：材料是内容层的
 * 单一真源，画面参数必须由它推导，而不是两处维护。因此每个 composition
 * 都带 `calculateMetadata`，注册时的 `durationInFrames` 只是占位。
 */
export const RemotionRoot: FC = () => {
  return (
    <>
      <Composition
        id="ArticleExplainer"
        component={ArticleExplainer}
        durationInFrames={1}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ version: 7, schemaVersion: 7, fps: 30, width: 1080, height: 1920, title: '', visual: { theme: 'dark' },
          durationInFrames: 1, compiledScenes: [], subtitleCues: [] } as ArticleExplainerProps}
        calculateMetadata={({ props }) => ({ durationInFrames: props.durationInFrames, fps: props.fps, width: props.width, height: props.height })}
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
    </>
  );
};
