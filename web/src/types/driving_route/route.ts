/**
 * 自驾路线几何：投影、累计距离、贴路位置、车头朝向与镜头。
 *
 * 全部函数都是当前帧的纯函数：同一帧无论执行顺序、机器速度或挂钟如何，
 * 位置、朝向、已走路线与相机状态都一致。经纬度统一为 GCJ-02，投影使用
 * 局部 Web Mercator；距离用球面 haversine，只用于沿路进度，画面里程始终取
 * 材料中的 API 距离。
 */

import { LAYOUT, contentRect } from './layout';

export type LonLat = [number, number];

export type DrivingStep = {road: string; points: LonLat[]};

export type RouteCost = {
  durationSeconds: number;
  tollsYuan: number;
  tollDistanceMeters: number;
  trafficLights: number;
};

export type RouteCity = {name: string; adcode: string; location: LonLat};

export type AdministrativePlace = {
  name: string;
  level: 'city' | 'county';
  adcode: string;
  parentAdcode?: string;
  center: LonLat;
};

export type BasemapLayer = {
  zoom: number;
  bbox: [number, number, number, number];
  image: {path: string; sha256: string; width: number; height: number};
  projected: {left: number; top: number; width: number; height: number};
  tileCount: number;
  dataUri: string;
};

export type FollowTile = {
  x: number;
  y: number;
  z: number;
  projected: {left: number; top: number; width: number; height: number};
  dataUri: string;
};

export type FollowTiles = {
  zoom: number;
  tileSize: number;
  tiles: FollowTile[];
};

export type BasemapConfig = {
  provider: string;
  service: string;
  attribution: string;
  fetchedAt: string;
  overview: BasemapLayer;
  followTiles: FollowTiles;
};

export type DrivingRouteProps = {
  schemaVersion: number;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  originLabel: string;
  destinationLabel: string;
  origin: LonLat;
  destination: LonLat;
  routeStart: LonLat;
  routeEnd: LonLat;
  totalDistanceMeters: number;
  attribution: string;
  cost?: RouteCost;
  cities?: RouteCity[];
  administrativePlaces?: AdministrativePlace[];
  basemap?: BasemapConfig;
  steps: DrivingStep[];
};

export type ProjectedPoint = {x: number; y: number};
export type RoadSpan = {road: string; startIndex: number; endIndex: number};

export type RouteModel = {
  coordinates: LonLat[];
  projected: ProjectedPoint[];
  cumulative: number[];
  lengthMeters: number;
  /** 投影平面上的折线总长度；用于把米制前瞻换算到投影单位。 */
  projectedLength: number;
  spans: RoadSpan[];
  bounds: {minX: number; minY: number; maxX: number; maxY: number};
};

export type Camera = {scale: number; tx: number; ty: number};

const EARTH_RADIUS_METERS = 6371008.8;
const MERCATOR_RADIUS = 6378137;
const WORLD = 2 * Math.PI * MERCATOR_RADIUS;

export function haversineMeters(a: LonLat, b: LonLat): number {
  const toRad = Math.PI / 180;
  const lat1 = a[1] * toRad;
  const lat2 = b[1] * toRad;
  const dLat = lat2 - lat1;
  const dLng = (b[0] - a[0]) * toRad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** 局部 Web Mercator；y 取负号，使屏幕方向保持北向上。 */
export function projectPoint([lng, lat]: LonLat): ProjectedPoint {
  const x = MERCATOR_RADIUS * (lng * Math.PI) / 180;
  const y = -MERCATOR_RADIUS * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  return {x, y};
}

export function buildRouteModel(steps: DrivingStep[]): RouteModel {
  const coordinates: LonLat[] = [];
  const spans: RoadSpan[] = [];
  for (const step of steps) {
    const startIndex = coordinates.length === 0 ? 0 : coordinates.length - 1;
    for (const point of step.points) {
      const last = coordinates[coordinates.length - 1];
      if (last && last[0] === point[0] && last[1] === point[1]) continue;
      coordinates.push([point[0], point[1]]);
    }
    if (coordinates.length > startIndex + 1) {
      spans.push({road: step.road, startIndex, endIndex: coordinates.length - 1});
    }
  }
  if (coordinates.length < 2) throw new Error('路线至少需要两个不同坐标点');
  const cumulative = [0];
  for (let index = 1; index < coordinates.length; index += 1) {
    cumulative.push(cumulative[index - 1] + haversineMeters(coordinates[index - 1], coordinates[index]));
  }
  const projected = coordinates.map(projectPoint);
  const xs = projected.map((point) => point.x);
  const ys = projected.map((point) => point.y);
  let projectedLength = 0;
  for (let index = 1; index < projected.length; index += 1) {
    projectedLength += Math.hypot(projected[index].x - projected[index - 1].x,
      projected[index].y - projected[index - 1].y);
  }
  return {
    coordinates,
    projected,
    cumulative,
    lengthMeters: cumulative[cumulative.length - 1],
    projectedLength,
    spans,
    bounds: {minX: Math.min(...xs), minY: Math.min(...ys), maxX: Math.max(...xs), maxY: Math.max(...ys)},
  };
}

export function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

export function smoothstep(value: number): number {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

/** 开场推近使用 ease-out：前段快、末段收稳，避免 2 秒内推近显得迟滞。 */
export function easeOutQuad(value: number): number {
  const t = clamp(value, 0, 1);
  return 1 - (1 - t) * (1 - t);
}

function segmentAt(model: RouteModel, distance: number): number {
  const d = clamp(distance, 0, model.lengthMeters);
  let low = 0;
  let high = model.cumulative.length - 1;
  while (low + 1 < high) {
    const mid = (low + high) >> 1;
    if (model.cumulative[mid] <= d) low = mid;
    else high = mid;
  }
  return low;
}

function unitTangent(model: RouteModel, index: number): ProjectedPoint | null {
  const a = model.projected[index];
  const b = model.projected[index + 1];
  if (!a || !b) return null;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = Math.hypot(dx, dy);
  return length > 0 ? {x: dx / length, y: dy / length} : null;
}

/** 当前位置；位置永远落在折线上，已走路线与小车共用这一结果。 */
export function pointAtDistance(model: RouteModel, distance: number): ProjectedPoint & {index: number} {
  const d = clamp(distance, 0, model.lengthMeters);
  const index = segmentAt(model, d);
  const start = model.projected[index];
  const end = model.projected[index + 1];
  const span = model.cumulative[index + 1] - model.cumulative[index];
  const t = span > 0 ? clamp((d - model.cumulative[index]) / span, 0, 1) : 0;
  return {x: start.x + (end.x - start.x) * t, y: start.y + (end.y - start.y) * t, index};
}

/** 跟随相机中心：对目标点前后等距折线点做对称平均，压住折线拐点造成的高频抖动。 */
export function smoothedPointAtDistance(model: RouteModel, distance: number,
                                        frameStepMeters: number, halfFrames: number): ProjectedPoint {
  let x = 0;
  let y = 0;
  let count = 0;
  for (let offset = -halfFrames; offset <= halfFrames; offset += 1) {
    const point = pointAtDistance(model, distance + offset * frameStepMeters);
    x += point.x;
    y += point.y;
    count += 1;
  }
  return {x: x / count, y: y / count};
}

/** 车头方向：用短距离弦线跟随当前道路，端点处只向路线内部取样。
 *
 * 长路线按总长比例取样会把起点附近的多个街区弯道平均成一个虚假的方向，
 * 让车一开始朝错方向、随后再转回来。窗口固定为 15 米，起点直接取首段切线；
 * 这样初始朝向就是道路方向，且不会预看数百米后的弯道。取样相消时退回最近的
 * 非零线段切向，不依赖上一帧。
 */
export function headingAtDistance(model: RouteModel, distance: number): number {
  const lookAhead = Math.min(15, model.lengthMeters / 2);
  const d = clamp(distance, 0, model.lengthMeters);
  const forward = d + lookAhead <= model.lengthMeters;
  const from = pointAtDistance(model, forward ? d : d - lookAhead);
  const to = pointAtDistance(model, forward ? d + lookAhead : d);
  let dx = to.x - from.x;
  let dy = to.y - from.y;
  if (Math.hypot(dx, dy) < 1e-9) {
    const index = segmentAt(model, d);
    for (let step = 0; step < model.projected.length - 1; step += 1) {
      const tangent = unitTangent(model, index + step) ?? unitTangent(model, index - step);
      if (tangent) {
        dx = tangent.x;
        dy = tangent.y;
        break;
      }
    }
  }
  if (d === 0) {
    const tangent = unitTangent(model, 0);
    if (tangent) {
      dx = tangent.x;
      dy = tangent.y;
    }
  }
  return Math.atan2(dy, dx);
}

/** 在参考角附近表达当前角度，避免 -π/π 边界让 SVG 车辆反向旋转一整圈。 */
export function headingNear(reference: number, heading: number): number {
  const delta = Math.atan2(Math.sin(heading - reference), Math.cos(heading - reference));
  return reference + delta;
}

export type Timeline = {
  totalFrames: number;
  openingFrames: number;
  transitionFrames: number;
  driveFrames: number;
  endingFrames: number;
  endingHoldFrames: number;
  pulloutFrames: number;
  endingStart: number;
};

/** 首尾与行驶段的共享帧账本；相机、里程与底图淡出都从这里取边界。 */
export function timeline(durationInFrames: number, fps: number): Timeline {
  const camera = LAYOUT.camera;
  const openingFrames = Math.round(camera.openingSeconds * fps);
  const endingFrames = Math.round(camera.endingSeconds * fps);
  const driveFrames = Math.max(1, durationInFrames - openingFrames - endingFrames);
  const transitionFrames = Math.min(Math.round(camera.openingTransitionSeconds * fps), driveFrames);
  const endingHoldFrames = Math.min(Math.round(camera.endingHoldSeconds * fps),
    Math.max(0, endingFrames - 1));
  const pulloutFrames = Math.max(1, endingFrames - endingHoldFrames);
  return {
    totalFrames: durationInFrames,
    openingFrames,
    transitionFrames,
    driveFrames,
    endingFrames,
    endingHoldFrames,
    pulloutFrames,
    endingStart: durationInFrames - endingFrames,
  };
}

/** 沿路已走距离：开场停在起点，行驶段按匀速推进到终点，不做全段加减速。 */
export function distanceForFrame(frame: number, durationInFrames: number, fps: number, lengthMeters: number): number {
  const spans = timeline(durationInFrames, fps);
  if (frame < spans.openingFrames) return 0;
  if (frame >= spans.endingStart) return lengthMeters;
  const progress = clamp((frame - spans.openingFrames + 1) / spans.driveFrames, 0, 1);
  return lengthMeters * progress;
}

/** 画面里程：按沿路进度换算 API 总距离，绝不把测地长度当作公路公里数。 */
export function displayDistanceMeters(traveledMeters: number, routeLengthMeters: number,
                                       apiDistanceMeters: number): number {
  if (routeLengthMeters <= 0) return 0;
  return apiDistanceMeters * clamp(traveledMeters / routeLengthMeters, 0, 1);
}

export function fitCamera(bounds: RouteModel['bounds'], width: number, height: number, padding: number): Camera {
  const spanX = Math.max(bounds.maxX - bounds.minX, 1e-6);
  const spanY = Math.max(bounds.maxY - bounds.minY, 1e-6);
  const scale = Math.min((width - padding * 2) / spanX, (height - padding * 2) / spanY);
  return {
    scale,
    tx: width / 2 - ((bounds.minX + bounds.maxX) / 2) * scale,
    ty: height / 2 - ((bounds.minY + bounds.maxY) / 2) * scale,
  };
}

/** 全程取景：只使用标题带以下的内容区，避免端点被标题遮挡。 */
export function fitCameraInContent(bounds: RouteModel['bounds'], width: number, height: number): Camera {
  const content = contentRect(width, height);
  const spanX = Math.max(bounds.maxX - bounds.minX, 1e-6);
  const spanY = Math.max(bounds.maxY - bounds.minY, 1e-6);
  const scale = Math.min((content.innerRight - content.innerLeft) / spanX,
    (content.innerBottom - content.innerTop) / spanY);
  return {
    scale,
    tx: content.cx - ((bounds.minX + bounds.maxX) / 2) * scale,
    ty: content.cy - ((bounds.minY + bounds.maxY) / 2) * scale,
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

export function cameraForFrame(model: RouteModel, frame: number, durationInFrames: number,
                                fps: number, width: number, height: number): Camera {
  const content = contentRect(width, height);
  const camera = LAYOUT.camera;
  const full = fitCameraInContent(model.bounds, width, height);
  const spans = timeline(durationInFrames, fps);
  const followScale = full.scale * camera.followZoom;
  const metersPerProjected = model.projectedLength > 0 ? model.lengthMeters / model.projectedLength : 1;
  const frameStepMeters = model.lengthMeters / spans.driveFrames;
  const smoothingHalfFrames = Math.floor(camera.cameraSmoothingSeconds * fps + 0.5);

  const followAt = (distance: number): Camera => {
    const visibleMeters = (Math.min(width, height) / followScale) * metersPerProjected;
    const lookahead = clamp(
      Math.min(model.lengthMeters * camera.lookaheadRouteFraction,
        visibleMeters * camera.lookaheadViewFraction),
      0, model.lengthMeters);
    // 开场结束时相机正对起点；行驶立刻开始，但视野前瞻与折线平滑必须从零渐入，
    // 否则第 60 帧会从起点瞬间跳到数公里外，形成一次明显的位置突跳。
    const leadMeters = lookahead * camera.lookaheadTargetFraction;
    const leadRamp = smoothstep(distance / Math.max(1, leadMeters));
    const targetDistance = Math.min(distance + leadMeters * leadRamp, model.lengthMeters);
    const smoothed = smoothedPointAtDistance(model, targetDistance, frameStepMeters,
      smoothingHalfFrames);
    const anchor = pointAtDistance(model, distance);
    const smoothingRamp = smoothstep(distance / Math.max(1, lookahead * 0.25));
    const target = {
      x: anchor.x + (smoothed.x - anchor.x) * smoothingRamp,
      y: anchor.y + (smoothed.y - anchor.y) * smoothingRamp,
    };
    // 跟随段比例固定，把平移量对齐到整像素：地图瓦片、路线与屏幕标签每帧共享同一
    // 整像素位移，重采样相位不再逐帧变化，避免文字和地名随镜头移动“沸腾”。
    return {
      scale: followScale,
      tx: Math.round(content.cx - target.x * followScale),
      ty: Math.round(content.cy - target.y * followScale),
    };
  };

  const openingScale = full.scale * camera.openingStartZoom;
  const openingEndScale = full.scale * camera.openingEndZoom;
  const openingAt = (amount: number): Camera => {
    const scale = openingScale + (openingEndScale - openingScale) * easeOutQuad(amount);
    const start = model.projected[0];
    return {scale, tx: content.cx - start.x * scale, ty: content.cy - start.y * scale};
  };

  const distance = distanceForFrame(frame, durationInFrames, fps, model.lengthMeters);
  if (frame < spans.openingFrames) {
    return openingAt(spans.openingFrames <= 1 ? 1 : frame / (spans.openingFrames - 1));
  }
  if (frame < spans.openingFrames + spans.transitionFrames) {
    const amount = spans.transitionFrames <= 0 ? 1
      : (frame - spans.openingFrames + 1) / spans.transitionFrames;
    return mixCamera(openingAt(1), followAt(distance), amount);
  }
  if (frame < spans.endingStart) return followAt(distance);
  if (frame < spans.endingStart + spans.pulloutFrames) {
    return mixCamera(followAt(model.lengthMeters), full,
      (frame - spans.endingStart + 1) / spans.pulloutFrames);
  }
  return full;
}

export function toScreen(camera: Camera, point: ProjectedPoint): ProjectedPoint {
  return {x: point.x * camera.scale + camera.tx, y: point.y * camera.scale + camera.ty};
}

export function walkedPoints(model: RouteModel, distance: number): ProjectedPoint[] {
  const current = pointAtDistance(model, distance);
  const points = model.projected.slice(0, current.index + 1).map((point) => ({...point}));
  points.push({x: current.x, y: current.y});
  return points;
}

export type RoadLabel = {road: string; distance: number; lengthMeters: number};

/** 标签的稳定 key：同一帧内按道路名与沿路距离唯一。 */
export function roadLabelKey(label: {road: string; distance: number}): string {
  return `road-${label.road}-${label.distance.toFixed(1)}`;
}

/** 合并连续同名道路，只挑真实高速名称；普通道路不冒充高速。
 *
 * 长距离高速沿路重复放置标签，避免跟随时唯一标签长期落在视域外；短路线
 * 只保留中点一个，避免画面被地名占满。
 */
export function highwayLabels(model: RouteModel): RoadLabel[] {
  const groups: {road: string; startIndex: number; endIndex: number}[] = [];
  for (const span of model.spans) {
    const last = groups[groups.length - 1];
    if (last && last.road === span.road) last.endIndex = span.endIndex;
    else groups.push({...span});
  }
  const labels: RoadLabel[] = [];
  for (const group of groups) {
    const startDistance = model.cumulative[group.startIndex];
    const endDistance = model.cumulative[group.endIndex];
    const lengthMeters = endDistance - startDistance;
    if (!group.road.includes('高速') || lengthMeters <= 0) continue;
    const fractions = lengthMeters >= 20_000 ? [0.2, 0.4, 0.6, 0.8]
      : lengthMeters >= 2_000 ? [0.3, 0.7] : [0.5];
    for (const fraction of fractions) {
      labels.push({road: group.road, distance: startDistance + lengthMeters * fraction, lengthMeters});
    }
  }
  return labels.sort((a, b) => b.lengthMeters - a.lengthMeters).slice(0, 6);
}

/** 跟随瓦片图层的透明度：跟随段完全覆盖概览，结尾拉远时在 1 秒内淡出。 */
export function basemapOpacity(frame: number, durationInFrames: number, fps: number): number {
  const spans = timeline(durationInFrames, fps);
  if (frame < spans.endingStart) return 1;
  if (frame < spans.endingStart + spans.pulloutFrames) {
    return 1 - smoothstep((frame - spans.endingStart + 1) / spans.pulloutFrames);
  }
  return 0;
}

export function tileKey(x: number, y: number): string {
  return `${x}:${y}`;
}

/** 稳定的瓦片索引：每帧只查视口覆盖的瓦片，不扫描整条走廊。 */
export function buildTileIndex(tiles: FollowTile[]): Map<string, FollowTile> {
  return new Map(tiles.map((tile) => [tileKey(tile.x, tile.y), tile]));
}

/** 按屏幕视口反算瓦片范围；只返回与视口相交（含少量像素余量）的块。 */
export function selectVisibleTiles(index: ReadonlyMap<string, FollowTile>, zoom: number,
                                   camera: Camera, width: number, height: number,
                                   margin: number = 2): FollowTile[] {
  if (index.size === 0 || camera.scale <= 0) return [];
  const n = 1 << zoom;
  const left = (0 - margin - camera.tx) / camera.scale;
  const top = (0 - margin - camera.ty) / camera.scale;
  const right = (width + margin - camera.tx) / camera.scale;
  const bottom = (height + margin - camera.ty) / camera.scale;
  const toTileX = (x: number) => ((x + Math.PI * MERCATOR_RADIUS) / WORLD) * n;
  const pxLeft = toTileX(left);
  const pxRight = toTileX(right);
  const pyTop = toTileX(top);
  const pyBottom = toTileX(bottom);
  const x0 = Math.max(0, Math.floor(pxLeft));
  const x1 = Math.min(n - 1, Math.floor(pxRight - 1e-9));
  const y0 = Math.max(0, Math.floor(pyTop));
  const y1 = Math.min(n - 1, Math.floor(pyBottom - 1e-9));
  const visible: FollowTile[] = [];
  for (let y = y0; y <= y1; y += 1) {
    for (let x = x0; x <= x1; x += 1) {
      const tile = index.get(tileKey(x, y));
      if (tile) visible.push(tile);
    }
  }
  return visible;
}

export function formatDistance(meters: number): string {
  if (meters >= 100_000) return `${Math.round(meters / 1000)} 公里`;
  return `${(meters / 1000).toFixed(1)} 公里`;
}

