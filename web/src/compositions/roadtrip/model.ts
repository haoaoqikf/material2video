/**
 * 多日地图游记的纯函数层：帧 → 天、每日相机、里程与底图地址。
 *
 * 相机口径与 Python `road_trip/layout.py` 一致：开场 8×→12×、12× 跟随、
 * 收束到当天概览；Day 4 在七十二拐窗口平滑提高到 14×。所有状态只依赖当前帧
 * 与 props，不读取上一帧、随机数或挂钟。
 */
import type {SubtitleStyle} from '../../frames';
import type {AdministrativePlace, Camera, RouteModel} from '../driving/route';
import type {MapBasemap} from '../driving/MapLayer';
import {buildRouteModel, clamp, easeOutQuad, projectPoint, smoothstep, toScreen,
  type DrivingStep, type ProjectedPoint} from '../driving/route';
import raw from './layout.json';

export const LAYOUT = raw;

export type RoadTripCardFact = {id: string; label: string; value: string; sourceId: string};
export type RoadTripCard = {id: string; title: string; facts: RoadTripCardFact[]};
export type RoadTripLandmark = {id: string; label: string; distanceMeters: number};
export type RoadTripOverview = {path: string; projected: {left: number; top: number; width: number; height: number};
  width: number; height: number};
export type RoadTripFollowTiles = {zoom: number;
  tiles: Array<{x: number; y: number; z: number; path: string; projected: RoadTripOverview['projected']}>};
export type RoadTripBasemap = {style: 'road' | 'satellite'; overview: RoadTripOverview;
  followTiles: RoadTripFollowTiles};
export type RoadTripSegmentWindow = {startFrame: number; endFrame: number};
export type RoadTripDay = {
  id: string; title: string; subtitle: string;
  originLabel: string; destinationLabel: string;
  startFrame: number; durationInFrames: number;
  chapterFrames: number; openingStart: number; openingFrames: number; followStart: number;
  arrivalLocalFrame: number; pulloutFrames: number;
  steps: DrivingStep[];
  totalDistanceMeters: number;
  administrativePlaces: AdministrativePlace[];
  cities: Array<{name: string; adcode: string; location: [number, number]}>;
  card: RoadTripCard | null;
  landmarks: RoadTripLandmark[];
  narration: Array<{id: string; text: string}>;
  segmentWindows: Record<string, RoadTripSegmentWindow>;
  basemap?: RoadTripBasemap;
};
export type RoadTripProps = {
  schemaVersion: number; durationInFrames: number; fps: number; width: number; height: number;
  title: string; originLabel: string; destinationLabel: string; attribution: string;
  sources: Record<string, {title: string; publisher: string}>;
  subtitle: SubtitleStyle;
  days: RoadTripDay[];
  subtitleCues: Array<{startFrame: number; endFrame: number; text: string}>;
  globalBasemap?: RoadTripOverview;
  assetBase?: string;
};

export type ContentRect = {top: number; bottom: number; left: number; right: number;
  innerTop: number; innerBottom: number; innerLeft: number; innerRight: number;
  cx: number; cy: number};

export function contentRect(width: number = LAYOUT.width, height: number = LAYOUT.height): ContentRect {
  const top = LAYOUT.title.height + LAYOUT.content.topGap;
  const bottom = height - LAYOUT.content.bottomMargin;
  const left = LAYOUT.content.sideMargin;
  const right = width - LAYOUT.content.sideMargin;
  const padding = LAYOUT.content.padding;
  return {
    top, bottom, left, right,
    innerTop: top + padding, innerBottom: bottom - padding,
    innerLeft: left + padding, innerRight: right - padding,
    cx: (left + right) / 2, cy: (top + bottom) / 2,
  };
}

export function dayAtFrame(props: RoadTripProps, frame: number): {index: number; day: RoadTripDay; localFrame: number} {
  for (let index = 0; index < props.days.length; index += 1) {
    const day = props.days[index]!;
    if (frame < day.startFrame + day.durationInFrames) {
      return {index, day, localFrame: frame - day.startFrame};
    }
  }
  const index = props.days.length - 1;
  const day = props.days[index]!;
  return {index, day, localFrame: Math.max(0, day.durationInFrames - 1)};
}

/**
 * 把一天的投影坐标平移到当天起点。
 *
 * Web Mercator 的绝对米值在千万级；SVG 设备坐标在 24 位定点附近会丢精度，
 * 小范围路线配合高倍率相机时尤其明显（底图与路线整块消失）。相机、底图
 * 投影矩形与标签共用同一个偏移，屏幕结果与绝对坐标完全等价。
 */
export function localModel(steps: DrivingStep[]): {model: RouteModel; offset: ProjectedPoint} {
  const model = buildRouteModel(steps);
  const offset = model.projected[0]!;
  return {
    offset,
    model: {
      ...model,
      projected: model.projected.map((point) => ({x: point.x - offset.x, y: point.y - offset.y})),
      bounds: {
        minX: model.bounds.minX - offset.x, maxX: model.bounds.maxX - offset.x,
        minY: model.bounds.minY - offset.y, maxY: model.bounds.maxY - offset.y,
      },
    },
  };
}

export function fullScale(model: RouteModel, width: number, height: number): number {
  const content = contentRect(width, height);
  const spanX = Math.max(model.bounds.maxX - model.bounds.minX, 1e-6);
  const spanY = Math.max(model.bounds.maxY - model.bounds.minY, 1e-6);
  return Math.min((content.innerRight - content.innerLeft) / spanX,
    (content.innerBottom - content.innerTop) / spanY);
}

export function dayDistance(model: RouteModel, day: RoadTripDay, localFrame: number): number {
  if (localFrame < day.followStart) return 0;
  if (localFrame >= day.arrivalLocalFrame) return model.lengthMeters;
  const progress = clamp((localFrame - day.followStart + 1) / Math.max(1, day.arrivalLocalFrame - day.followStart), 0, 1);
  return model.lengthMeters * progress;
}

function zoomWindow(dayId: string) {
  return LAYOUT.followZoomWindows.find((item) => item.dayId === dayId) ?? null;
}

export function followMultiplier(day: RoadTripDay, fraction: number, modelLength: number): number {
  const window = zoomWindow(day.id);
  const base = LAYOUT.camera.followZoom;
  if (!window) return base;
  const landmark = day.landmarks.find((item) => item.id === window.landmarkId);
  if (!landmark) return base;
  const center = clamp(landmark.distanceMeters / Math.max(1, modelLength), 0, 1);
  const span = 0.06;
  const near = clamp(1 - Math.abs(fraction - center) / span, 0, 1);
  return base + (window.zoom - base) * smoothstep(near);
}

function openingCamera(model: RouteModel, amount: number, width: number, height: number): Camera {
  const content = contentRect(width, height);
  const full = fullScale(model, width, height);
  const startScale = full * LAYOUT.camera.openingStartZoom;
  const endScale = full * LAYOUT.camera.openingEndZoom;
  const scale = startScale + (endScale - startScale) * easeOutQuad(amount);
  const start = model.projected[0]!;
  return {scale, tx: content.cx - start.x * scale, ty: content.cy - start.y * scale};
}

function overviewCamera(model: RouteModel, width: number, height: number): Camera {
  const content = contentRect(width, height);
  const scale = fullScale(model, width, height);
  return {
    scale,
    tx: content.cx - ((model.bounds.minX + model.bounds.maxX) / 2) * scale,
    ty: content.cy - ((model.bounds.minY + model.bounds.maxY) / 2) * scale,
  };
}

function mixCamera(from: Camera, to: Camera, amount: number): Camera {
  const t = smoothstep(amount);
  return {
    scale: from.scale + (to.scale - from.scale) * t,
    tx: from.tx + (to.tx - from.tx) * t,
    ty: from.ty + (to.ty - from.ty) * t,
  };
}

const SMOOTHING_STEP_METERS = 400;
const SMOOTHING_HALF_FRAMES = Math.round(LAYOUT.camera.cameraSmoothingSeconds * 30 + 0.5);

function followCamera(model: RouteModel, day: RoadTripDay, distance: number,
                      width: number, height: number): Camera {
  const content = contentRect(width, height);
  const full = fullScale(model, width, height);
  const fraction = clamp(distance / Math.max(1, model.lengthMeters), 0, 1);
  const scale = full * followMultiplier(day, fraction, model.lengthMeters);
  const metersPerProjected = model.projectedLength > 0 ? model.lengthMeters / model.projectedLength : 1;
  const visibleMeters = (Math.min(width, height) / scale) * metersPerProjected;
  const lookahead = Math.min(model.lengthMeters * 0.02, visibleMeters * 0.2);
  const targetDistance = Math.min(distance + lookahead * 0.5, model.lengthMeters);
  let x = 0;
  let y = 0;
  let count = 0;
  for (let offset = -SMOOTHING_HALF_FRAMES; offset <= SMOOTHING_HALF_FRAMES; offset += 1) {
    const point = pointAtDistance(model, targetDistance + offset * SMOOTHING_STEP_METERS);
    x += point.x;
    y += point.y;
    count += 1;
  }
  return {scale, tx: Math.round(content.cx - (x / count) * scale),
    ty: Math.round(content.cy - (y / count) * scale)};
}

function pointAtDistance(model: RouteModel, distance: number): ProjectedPoint {
  const d = clamp(distance, 0, model.lengthMeters);
  let low = 0;
  let high = model.cumulative.length - 1;
  while (low + 1 < high) {
    const mid = (low + high) >> 1;
    if (model.cumulative[mid]! <= d) low = mid;
    else high = mid;
  }
  const start = model.projected[low]!;
  const end = model.projected[low + 1]!;
  const span = model.cumulative[low + 1]! - model.cumulative[low]!;
  const t = span > 0 ? clamp((d - model.cumulative[low]!) / span, 0, 1) : 0;
  return {x: start.x + (end.x - start.x) * t, y: start.y + (end.y - start.y) * t};
}

export function cameraForDay(model: RouteModel, day: RoadTripDay, localFrame: number,
                             width: number, height: number): Camera {
  if (localFrame < day.openingStart) return overviewCamera(model, width, height);
  if (localFrame < day.followStart) {
    const amount = day.openingFrames <= 1 ? 1 : (localFrame - day.openingStart) / day.openingFrames;
    return openingCamera(model, amount, width, height);
  }
  const distance = dayDistance(model, day, localFrame);
  if (localFrame < day.arrivalLocalFrame) {
    return followCamera(model, day, distance, width, height);
  }
  const pullout = Math.max(1, day.pulloutFrames);
  return mixCamera(followCamera(model, day, model.lengthMeters, width, height),
    overviewCamera(model, width, height), (localFrame - day.arrivalLocalFrame + 1) / pullout);
}

export function followOpacity(day: RoadTripDay, localFrame: number): number {
  if (localFrame < day.followStart) return 0;
  if (localFrame < day.arrivalLocalFrame) return 1;
  const pullout = Math.max(1, day.pulloutFrames);
  return 1 - smoothstep((localFrame - day.arrivalLocalFrame + 1) / pullout);
}

export function chapterOpacity(day: RoadTripDay, localFrame: number): number {
  const fade = Math.max(1, LAYOUT.timeline.chapterFadeFrames);
  if (localFrame >= day.chapterFrames) return 0;
  return 1 - smoothstep((localFrame - (day.chapterFrames - fade)) / fade);
}

export function walkedPointsAt(model: RouteModel, distance: number): ProjectedPoint[] {
  const current = pointAtDistance(model, distance);
  let index = 0;
  while (index + 1 < model.cumulative.length && model.cumulative[index + 1]! <= distance) index += 1;
  const points = model.projected.slice(0, index + 1).map((point) => ({...point}));
  points.push({x: current.x, y: current.y});
  return points;
}

export function formatDistance(meters: number): string {
  if (meters >= 100_000) return `${Math.round(meters / 1000)} 公里`;
  return `${(meters / 1000).toFixed(1)} 公里`;
}

/** 把准备记录里的本地路径转换成 Remotion 可读的 data 地址（由本地静态服务提供）。 */
function shiftProjected(rect: {left: number; top: number; width: number; height: number},
                        offset: ProjectedPoint) {
  return {...rect, left: rect.left - offset.x, top: rect.top - offset.y};
}

export function resolveBasemap(day: RoadTripDay, assetBase: string,
                               offset: ProjectedPoint): MapBasemap | undefined {
  if (!day.basemap) return undefined;
  const prefix = assetBase.endsWith('/') ? assetBase : `${assetBase}/`;
  return {
    overview: {...day.basemap.overview, projected: shiftProjected(day.basemap.overview.projected, offset),
      dataUri: prefix + day.basemap.overview.path},
    followTiles: {
      tiles: day.basemap.followTiles.tiles.map((tile) => ({
        ...tile, projected: shiftProjected(tile.projected, offset), dataUri: prefix + tile.path,
      })),
    },
  };
}

export function screenOf(camera: Camera, coordinate: [number, number],
                         offset: ProjectedPoint): ProjectedPoint {
  const point = projectPoint(coordinate);
  return toScreen(camera, {x: point.x - offset.x, y: point.y - offset.y});
}
