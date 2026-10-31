import { BUILDING_FPS, DRIVING_ROUTE_FPS, FPS, GENERAL_DEFAULT_FPS, ROAD_TRIP_FPS, VEHICLE_SHOWCASE_FPS } from './video-config';
import type { FC } from 'react';
import { Composition } from 'remotion';
import { ArticleExplainer, type ArticleExplainerProps } from './compositions/ArticleExplainer';
import { BuildingConstruction, type BuildingProps } from './compositions/BuildingConstruction';
import { DrivingRoute, type DrivingRouteProps } from './compositions/DrivingRoute';
import { FinancialTimeSeries, type FinancialTimeSeriesProps } from './compositions/FinancialTimeSeries';
import { RoadTrip, type RoadTripProps } from './compositions/RoadTrip';
import { VehicleShowcase, type VehicleShowcaseProps } from './compositions/VehicleShowcase';
import { DEFAULT_FRAME } from './frames';
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
        fps={GENERAL_DEFAULT_FPS}
        width={DEFAULT_FRAME.width}
        height={DEFAULT_FRAME.height}
        defaultProps={{ version: 8, schemaVersion: 8, fps: GENERAL_DEFAULT_FPS, width: DEFAULT_FRAME.width,
          height: DEFAULT_FRAME.height, title: '', subtitle: DEFAULT_FRAME.subtitle,
          durationInFrames: 1, compiledScenes: [], subtitleCues: [] } as ArticleExplainerProps}
        calculateMetadata={({ props }) => ({ durationInFrames: props.durationInFrames, fps: props.fps, width: props.width, height: props.height })}
      />
      <Composition
        id="FinancialTimeSeries"
        component={FinancialTimeSeries}
        durationInFrames={180}
        fps={FPS}
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
        id="BuildingConstruction"
        component={BuildingConstruction}
        durationInFrames={1200}
        fps={BUILDING_FPS}
        width={1920}
        height={1080}
        defaultProps={{} as BuildingProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames,
          fps: props.fps,
          width: props.width,
          height: props.height,
        })}
      />
      <Composition
        id="VehicleShowcase"
        component={VehicleShowcase}
        durationInFrames={900}
        fps={VEHICLE_SHOWCASE_FPS}
        width={1920}
        height={1080}
        defaultProps={{} as VehicleShowcaseProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames,
          fps: props.fps,
          width: props.width,
          height: props.height,
        })}
      />
      <Composition
        id="RoadTrip"
        component={RoadTrip}
        durationInFrames={5400}
        fps={ROAD_TRIP_FPS}
        width={1080}
        height={1920}
        defaultProps={{} as RoadTripProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames,
          fps: props.fps,
          width: props.width,
          height: props.height,
        })}
      />
      <Composition
        id="DrivingRoute"
        component={DrivingRoute}
        durationInFrames={900}
        fps={DRIVING_ROUTE_FPS}
        width={1080}
        height={1920}
        defaultProps={{} as DrivingRouteProps}
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
