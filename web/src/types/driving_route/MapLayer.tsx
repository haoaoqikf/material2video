/**
 * 共享地图绘制层：底图概览、跟随瓦片、未走/已走路线。
 *
 * `DrivingRoute` 与 `RoadTrip` 使用同一份相机投影与瓦片反算，抽出后两类视频的
 * 底图坐标、图层顺序与重采样相位不会各写一遍。这里只负责绘制，不计算距离、
 * 相机或标签；所有输入都是当前帧的纯数据。
 */
import type {Camera, FollowTile, ProjectedPoint, RouteModel} from './route';

/** 地图层实际读取的最少底图字段；`DrivingRoute` 的完整底图配置天然满足。 */
export type MapBasemap = {
  overview: {projected: {left: number; top: number; width: number; height: number}; dataUri: string};
  followTiles: {tiles: FollowTile[]};
};

export type MapLayerProps = {
  camera: Camera;
  model: RouteModel;
  distance: number;
  walked: ProjectedPoint[];
  basemap?: MapBasemap;
  visibleTiles?: FollowTile[];
  followOpacity?: number;
  walkedColor?: string;
  unwalkedColor?: string;
};

function polylinePoints(points: ProjectedPoint[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(' ');
}

export function MapLayer({
  camera, model, distance, walked, basemap, visibleTiles = [], followOpacity = 1,
  walkedColor = '#1f6feb', unwalkedColor = '#8b98a7',
}: MapLayerProps) {
  return (
    <g data-m2v-camera="true" data-m2v-scale={camera.scale.toFixed(8)}
      transform={`translate(${camera.tx} ${camera.ty}) scale(${camera.scale})`}>
      {basemap && <>
        <image data-m2v-basemap="overview" href={basemap.overview.dataUri}
          x={basemap.overview.projected.left} y={basemap.overview.projected.top}
          width={basemap.overview.projected.width}
          height={basemap.overview.projected.height}
          preserveAspectRatio="none" opacity={1} />
        <g data-m2v-basemap="follow" data-m2v-basemap-layer="follow"
          data-m2v-basemap-visible-count={visibleTiles.length}
          data-m2v-basemap-opacity={followOpacity.toFixed(4)} opacity={followOpacity}>
          {visibleTiles.map((tile) => <image key={`${tile.x}:${tile.y}`}
            data-m2v-basemap-tile={`${tile.x}:${tile.y}`} href={tile.dataUri}
            x={tile.projected.left} y={tile.projected.top}
            width={tile.projected.width} height={tile.projected.height}
            preserveAspectRatio="none" />)}
        </g>
      </>}
      <polyline data-m2v-route="true" points={polylinePoints(model.projected)} fill="none"
        stroke="#ffffff" strokeWidth={11} strokeLinejoin="round" strokeLinecap="round"
        vectorEffect="non-scaling-stroke" opacity={0.82} />
      <polyline data-m2v-route-color="true" points={polylinePoints(model.projected)} fill="none"
        stroke={unwalkedColor} strokeWidth={6} strokeLinejoin="round" strokeLinecap="round"
        vectorEffect="non-scaling-stroke" />
      {distance > 0 && walked.length > 1 && <>
        <polyline data-m2v-walked-underlay="true" points={polylinePoints(walked)} fill="none"
          stroke="#ffffff" strokeWidth={13} strokeLinejoin="round" strokeLinecap="round"
          vectorEffect="non-scaling-stroke" opacity={0.9} />
        <polyline data-m2v-walked="true" points={polylinePoints(walked)} fill="none"
          stroke={walkedColor} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round"
          vectorEffect="non-scaling-stroke" />
      </>}
    </g>
  );
}
