/**
 * 自驾路线几何：投影、累计距离、贴路位置、车头朝向与镜头。
 *
 * 全部函数都是当前帧的纯函数：同一帧无论执行顺序、机器速度或挂钟如何，
 * 位置、朝向、已走路线与相机状态都一致。经纬度统一为 GCJ-02，投影使用
 * 局部 Web Mercator；距离用球面 haversine，只用于沿路进度，画面里程始终取
 * 材料中的 API 距离。
 */

export type LonLat = [number, number];

export type DrivingStep = {road: string; points: LonLat[]};

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
  steps: DrivingStep[];
};

export type ProjectedPoint = {x: number; y: number};
export type RoadSpan = {road: string; startIndex: number; endIndex: number};

export type RouteModel = {
  coordinates: LonLat[];
  projected: ProjectedPoint[];
  cumulative: number[];
  lengthMeters: number;
  spans: RoadSpan[];
  bounds: {minX: number; minY: number; maxX: number; maxY: number};
};

export type Camera = {scale: number; tx: number; ty: number};

const EARTH_RADIUS_METERS = 6371008.8;
const MERCATOR_RADIUS = 6378137;
const OPENING_SECONDS = 3;
const ENDING_SECONDS = 3;
const FOLLOW_ZOOM = 2.5;

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
  return {
    coordinates,
    projected,
    cumulative,
    lengthMeters: cumulative[cumulative.length - 1],
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

/** 车头方向：沿行驶方向取前后窗口的弦向量，端点处只用朝内的窗口。
 *
 * 起点用前方 100 米（总长 0.1% 窗口的一半，20～200 米内）作为朝向，避免车头
 * 背对随即转弯的路线；终点用后方窗口，保持到达方向。取样相消时退回当前
 * 非零线段切向，不依赖上一帧。
 */
export function headingAtDistance(model: RouteModel, distance: number): number {
  const windowMeters = clamp(model.lengthMeters * 0.001, 20, 200);
  const lookAhead = windowMeters / 2;
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
  return Math.atan2(dy, dx);
}

/** 沿路已走距离：开场停在起点，行驶段平滑起停，结尾停在终点。 */
export function distanceForFrame(frame: number, durationInFrames: number, fps: number, lengthMeters: number): number {
  const opening = Math.round(OPENING_SECONDS * fps);
  const ending = Math.round(ENDING_SECONDS * fps);
  const drive = durationInFrames - opening - ending;
  if (frame < opening || drive <= 0) return 0;
  if (frame >= durationInFrames - ending) return lengthMeters;
  const progress = smoothstep((frame - opening + 1) / drive);
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

function mixCamera(from: Camera, to: Camera, amount: number): Camera {
  const t = smoothstep(amount);
  return {
    scale: from.scale + (to.scale - from.scale) * t,
    tx: from.tx + (to.tx - from.tx) * t,
    ty: from.ty + (to.ty - from.ty) * t,
  };
}

export function cameraForFrame(model: RouteModel, frame: number, durationInFrames: number,
                                fps: number, width: number, height: number, padding = 130): Camera {
  const full = fitCamera(model.bounds, width, height, padding);
  const followScale = full.scale * FOLLOW_ZOOM;
  const distance = distanceForFrame(frame, durationInFrames, fps, model.lengthMeters);
  // 前瞻必须是当前视域的一小部分：短路线若固定 200 米下限，跟随镜头会把车推出画面。
  const visibleSpan = Math.min(width, height) / followScale;
  const lookAhead = clamp(Math.min(model.lengthMeters * 0.02, visibleSpan * 0.2), 0, model.lengthMeters);
  const target = pointAtDistance(model, Math.min(distance + lookAhead * 0.5, model.lengthMeters));
  const follow: Camera = {
    scale: followScale,
    tx: width / 2 - target.x * followScale,
    ty: height / 2 - target.y * followScale,
  };
  const seconds = frame / fps;
  const totalSeconds = durationInFrames / fps;
  if (seconds < OPENING_SECONDS) return full;
  if (seconds < OPENING_SECONDS + 1) return mixCamera(full, follow, seconds - OPENING_SECONDS);
  if (seconds < totalSeconds - ENDING_SECONDS) return follow;
  if (seconds < totalSeconds - 1) {
    return mixCamera(follow, full, (seconds - (totalSeconds - ENDING_SECONDS)) / 2);
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

export function formatDistance(meters: number): string {
  if (meters >= 100_000) return `${Math.round(meters / 1000)} 公里`;
  return `${(meters / 1000).toFixed(1)} 公里`;
}
