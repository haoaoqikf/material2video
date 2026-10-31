/**
 * 自驾路线 composition：竖屏浅色普通道路地图、贴路小车、居中标题与车辆旁里程。
 *
 * 位置、朝向、已走路线与镜头全部来自 `./driving/route` 的纯函数；本文件只做
 * 当前帧取数与绘制，不保存跨帧状态。道路底图与路线使用同一 GCJ-02 投影。
 */
import { useEffect, useMemo } from 'react';
import { AbsoluteFill, cancelRender, continueRender, delayRender, useCurrentFrame } from 'remotion';
import {
  basemapOpacity, buildRouteModel, buildTileIndex, cameraForFrame, clamp, displayDistanceMeters,
  distanceForFrame, formatDistance, headingAtDistance, highwayLabels, pointAtDistance,
  projectPoint, roadLabelKey, selectVisibleTiles, toScreen, walkedPoints,
  type DrivingRouteProps, type ProjectedPoint, type RouteModel,
} from './driving/route';
import { LAYOUT, contentRect } from './driving/layout';
import { estimateTextWidth, fitFontSize, placeDistancePill, truncateText } from './driving/labels';

export type { DrivingRouteProps } from './driving/route';
export {
  basemapOpacity, buildRouteModel, buildTileIndex, cameraForFrame, displayDistanceMeters,
  distanceForFrame, easeOutQuad, fitCamera, fitCameraInContent, formatDistance, headingAtDistance,
  highwayLabels, pointAtDistance, projectPoint, roadLabelKey, selectVisibleTiles, smoothstep,
  smoothedPointAtDistance, timeline, toScreen, tileKey, walkedPoints,
} from './driving/route';

const INK = '#142433';
const MUTED = '#5b6b7c';
const WALKED = '#1f6feb';
const UNWALKED = '#8b98a7';
const MAP_BG = '#f3f0e9';
const PANEL = 'rgba(255,255,255,0.95)';
const TITLE_HEIGHT = LAYOUT.title.height;

function markerLabelY(y: number, height: number): number {
  return clamp(y - 30, TITLE_HEIGHT + 42, height - 40);
}

function polylinePoints(points: ProjectedPoint[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(' ');
}

type Box = {left: number; right: number; top: number; bottom: number};

function overlaps(first: Box, second: Box): boolean {
  return !(first.right < second.left || first.left > second.right
    || first.bottom < second.top || first.top > second.bottom);
}

/** 有符号屏幕距离：分离为正，重叠为负，用于在碰撞边界附近连续淡出。 */
function boxClearance(first: Box, second: Box): number {
  const dx = Math.max(second.left - first.right, first.left - second.right, 0);
  const dy = Math.max(second.top - first.bottom, first.top - second.bottom, 0);
  if (dx > 0 || dy > 0) return Math.hypot(dx, dy);
  return -Math.min(first.right - second.left, second.right - first.left,
    first.bottom - second.top, second.bottom - first.top);
}

function fadeForClearance(clearance: number, distance: number): number {
  const t = clamp((clearance + distance) / (2 * distance), 0, 1);
  return t * t * (3 - 2 * t);
}

function clearanceToRect(box: Box, rect: Box): number {
  return Math.min(box.left - rect.left, rect.right - box.right,
    box.top - rect.top, rect.bottom - box.bottom);
}

type AreaLabel = {name: string; level: string; adcode: string; x: number; y: number;
  opacity: number; box: Box};

const labelTimelineCache = new WeakMap<object, WeakMap<object, {
  signature: string; frames: AreaLabel[][]
}>>();

function buildAreaLabelsAtFrame(props: DrivingRouteProps, model: RouteModel, frame: number): AreaLabel[] {
  const camera = cameraForFrame(model, frame, props.durationInFrames, props.fps, props.width, props.height);
  const distance = distanceForFrame(frame, props.durationInFrames, props.fps, model.lengthMeters);
  const vehicle = toScreen(camera, pointAtDistance(model, distance));
  const origin = toScreen(camera, model.projected[0]);
  const destination = toScreen(camera, model.projected[model.projected.length - 1]);
  const visible = (point: ProjectedPoint) => point.x >= -120 && point.x <= props.width + 120
    && point.y >= LAYOUT.title.height - 120 && point.y <= props.height + 120;
  const labelBoxes: Box[] = [];
  const endpointBoxes: Box[] = [];
  const originSize = fitFontSize(props.originLabel, 240, LAYOUT.labels.endpointSize, 22);
  const originText = truncateText(props.originLabel, 240, originSize);
  const destinationSize = fitFontSize(props.destinationLabel, 240, LAYOUT.labels.endpointSize, 22);
  const destinationText = truncateText(props.destinationLabel, 240, destinationSize);
  const addEndpoint = (point: ProjectedPoint, label: string, size: number) => {
    if (!visible(point)) return;
    const halfWidth = (estimateTextWidth(label, size) + 16) / 2;
    const x = clamp(point.x, halfWidth + 10, props.width - halfWidth - 10);
    const y = markerLabelY(point.y, props.height);
    const box = {left: x - halfWidth, right: x + halfWidth, top: y - 36, bottom: y + 12};
    endpointBoxes.push(box);
    labelBoxes.push(box);
  };
  addEndpoint(origin, originText, originSize);
  addEndpoint(destination, destinationText, destinationSize);
  const attributionSize = fitFontSize(props.attribution, props.width - 120,
    LAYOUT.labels.attributionSize, 14);
  const attributionText = truncateText(props.attribution, props.width - 120, attributionSize);
  const attributionWidth = estimateTextWidth(attributionText, attributionSize) + 24;
  const attributionBox = {left: props.width - 40 - attributionWidth, right: props.width - 40,
    top: props.height - 76, bottom: props.height - 30};
  labelBoxes.push(attributionBox);
  const pillText = `已行驶 ${formatDistance(displayDistanceMeters(distance, model.lengthMeters,
    props.totalDistanceMeters))}`;
  const pill = placeDistancePill(vehicle.x, vehicle.y, pillText, props.width, props.height,
    LAYOUT.title.height + 12, [attributionBox, ...endpointBoxes]);
  labelBoxes.push({left: pill.cx - pill.width / 2, right: pill.cx + pill.width / 2,
    top: pill.cy - pill.height / 2, bottom: pill.cy + pill.height / 2});
  labelBoxes.push({left: vehicle.x - 32, right: vehicle.x + 32,
    top: vehicle.y - 32, bottom: vehicle.y + 32});
  if (visible(origin)) labelBoxes.push({left: origin.x - 20, right: origin.x + 20,
    top: origin.y - 20, bottom: origin.y + 20});
  if (visible(destination)) labelBoxes.push({left: destination.x - 22, right: destination.x + 22,
    top: destination.y - 22, bottom: destination.y + 22});

  const endpointNames = [props.originLabel, props.destinationLabel]
    .map((label) => label.replace(/[市区县]$/u, '')).filter((label) => label.length > 0);
  const areaSize = LAYOUT.labels.citySize;
  const areaOffset = Math.round(areaSize * 1.2);
  const areaBoxTop = Math.round(areaSize * 0.9);
  const areaBoxBottom = Math.round(areaSize * 0.3);
  const content = contentRect(props.width, props.height);
  const contentBox = {left: 10, right: props.width - 10,
    top: content.top + 6, bottom: content.bottom - 6};
  const areaBoxes: Box[] = [];
  return [...(props.administrativePlaces ?? [])]
    .sort((first, second) => (first.level === 'city' ? 0 : 1)
      - (second.level === 'city' ? 0 : 1)
      || first.adcode.localeCompare(second.adcode, 'en')
      || first.name.localeCompare(second.name, 'zh-CN'))
    .flatMap((place) => {
      if (!place || !Array.isArray(place.center) || place.center.length !== 2) return [];
      if (endpointNames.some((endpoint) => place.name.includes(endpoint))) return [];
      if (place.level === 'county' && place.name.endsWith('区')) return [];
      const point = toScreen(camera, projectPoint(place.center));
      const halfWidth = (estimateTextWidth(place.name, areaSize) + 16) / 2;
      const x = Math.round(clamp(point.x, halfWidth + 10, props.width - halfWidth - 10));
      const y = Math.round(point.y - areaOffset);
      const box = {left: x - halfWidth, right: x + halfWidth,
        top: y - areaBoxTop, bottom: y + areaBoxBottom};
      const fadeDistance = 120;
      const blockerClearance = labelBoxes.reduce((nearest, other) =>
        Math.min(nearest, boxClearance(box, other)), Number.POSITIVE_INFINITY);
      const priorLabelClearance = areaBoxes.reduce((nearest, other) =>
        Math.min(nearest, boxClearance(box, other)), Number.POSITIVE_INFINITY);
      const boundsClearance = Math.min(clearanceToRect(box, contentBox),
        point.x - halfWidth - 10, props.width - halfWidth - 10 - point.x);
      const opacity = Math.min(fadeForClearance(blockerClearance, fadeDistance),
        fadeForClearance(priorLabelClearance, fadeDistance),
        fadeForClearance(boundsClearance, fadeDistance));
      areaBoxes.push(box);
      return [{name: place.name, level: place.level, adcode: place.adcode, x, y, opacity, box}];
    });
}

/** 用九帧居中窗口平滑原始碰撞透明度，单次硬切最多影响一帧的 1/9。 */
export function buildAdministrativeLabelTimeline(props: DrivingRouteProps,
                                                  model: RouteModel): AreaLabel[][] {
  const places = props.administrativePlaces ?? [];
  const signature = `${props.durationInFrames}:${props.fps}:${props.width}:${props.height}:${props.originLabel}:${props.destinationLabel}:${props.attribution}:${props.totalDistanceMeters}`;
  let byPlaces = labelTimelineCache.get(props.steps);
  if (!byPlaces) {
    byPlaces = new WeakMap();
    labelTimelineCache.set(props.steps, byPlaces);
  }
  const cached = byPlaces.get(places);
  if (cached?.signature === signature) return cached.frames;

  const raw = Array.from({length: props.durationInFrames}, (_, frame) =>
    buildAreaLabelsAtFrame(props, model, frame));
  const rawByFrame = raw.map((labels) => new Map(labels.map((label) => [label.adcode, label])));
  const radius = 4;
  const smoothed = raw.map((labels, frame) => labels.map((label) => {
    let total = 0;
    let count = 0;
    for (let sample = Math.max(0, frame - radius); sample <= Math.min(raw.length - 1, frame + radius); sample += 1) {
      const sameLabel = rawByFrame[sample]!.get(label.adcode);
      total += sameLabel?.opacity ?? 0;
      count += 1;
    }
    return {...label, opacity: total / count};
  }));
  byPlaces.set(places, {signature, frames: smoothed});
  return smoothed;
}

export function DrivingRoute(props: DrivingRouteProps) {
  const frame = useCurrentFrame();
  const model = useMemo(() => buildRouteModel(props.steps), [props.steps]);
  const content = contentRect(props.width, props.height);
  const camera = cameraForFrame(model, frame, props.durationInFrames, props.fps,
    props.width, props.height);
  const distance = distanceForFrame(frame, props.durationInFrames, props.fps, model.lengthMeters);
  const traveling = pointAtDistance(model, distance);
  const heading = (headingAtDistance(model, distance) * 180) / Math.PI;
  const vehicle = toScreen(camera, traveling);
  const origin = toScreen(camera, model.projected[0]);
  const destination = toScreen(camera, model.projected[model.projected.length - 1]);
  const walked = walkedPoints(model, distance);
  const traveled = displayDistanceMeters(distance, model.lengthMeters, props.totalDistanceMeters);
  const opacity = basemapOpacity(frame, props.durationInFrames, props.fps);
  const followTiles = props.basemap?.followTiles.tiles ?? [];
  const tileIndex = useMemo(() => buildTileIndex(followTiles), [followTiles]);
  const visibleTiles = props.basemap && opacity > 0
    ? selectVisibleTiles(tileIndex, props.basemap.followTiles.zoom, camera,
      props.width, props.height, 2)
    : [];

  // 数据 URI 瓦片也必须等解码完成；首帧截图不能出现空白块。
  useEffect(() => {
    if (followTiles.length === 0) return;
    const handle = delayRender('加载跟随道路瓦片', {timeoutInMilliseconds: 120_000});
    let remaining = followTiles.length;
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      continueRender(handle);
    };
    const fail = () => {
      if (settled) return;
      settled = true;
      cancelRender(new Error('跟随道路瓦片加载失败'));
    };
    const images = followTiles.map((tile) => {
      const image = new Image();
      image.onload = () => {
        remaining -= 1;
        if (remaining <= 0) finish();
      };
      image.onerror = fail;
      image.src = tile.dataUri;
      return image;
    });
    return () => {
      finish();
      for (const image of images) {
        image.onload = null;
        image.onerror = null;
      }
    };
  }, [followTiles]);

  const visible = (point: ProjectedPoint) => point.x >= 24 && point.x <= props.width - 24
    && point.y >= TITLE_HEIGHT && point.y <= props.height - 24;
  const inMapArea = (y: number) => y > content.top && y < content.bottom - 12;

  const labelBoxes: Box[] = [];
  const endpointBoxes: Box[] = [];
  const originSize = fitFontSize(props.originLabel, 240, LAYOUT.labels.endpointSize, 22);
  const originText = truncateText(props.originLabel, 240, originSize);
  const destinationSize = fitFontSize(props.destinationLabel, 240, LAYOUT.labels.endpointSize, 22);
  const destinationText = truncateText(props.destinationLabel, 240, destinationSize);

  if (visible(origin)) {
    const halfWidth = (estimateTextWidth(originText, originSize) + 16) / 2;
    const x = clamp(origin.x, halfWidth + 10, props.width - halfWidth - 10);
    const y = markerLabelY(origin.y, props.height);
    const box = {left: x - halfWidth, right: x + halfWidth, top: y - 36, bottom: y + 12};
    endpointBoxes.push(box);
    labelBoxes.push(box);
  }
  if (visible(destination)) {
    const halfWidth = (estimateTextWidth(destinationText, destinationSize) + 16) / 2;
    const x = clamp(destination.x, halfWidth + 10, props.width - halfWidth - 10);
    const y = markerLabelY(destination.y, props.height);
    const box = {left: x - halfWidth, right: x + halfWidth, top: y - 36, bottom: y + 12};
    endpointBoxes.push(box);
    labelBoxes.push(box);
  }

  const attributionSize = fitFontSize(props.attribution, props.width - 120,
    LAYOUT.labels.attributionSize, 14);
  const attributionText = truncateText(props.attribution, props.width - 120, attributionSize);
  const attributionWidth = estimateTextWidth(attributionText, attributionSize) + 24;
  const attributionBox = {
    left: props.width - 40 - attributionWidth, right: props.width - 40,
    top: props.height - 76, bottom: props.height - 30,
  };
  labelBoxes.push(attributionBox);

  const pillText = `已行驶 ${formatDistance(traveled)}`;
  const pill = placeDistancePill(vehicle.x, vehicle.y, pillText, props.width, props.height,
    TITLE_HEIGHT + 12, [attributionBox, ...endpointBoxes]);
  const pillBox = {left: pill.cx - pill.width / 2, right: pill.cx + pill.width / 2,
    top: pill.cy - pill.height / 2, bottom: pill.cy + pill.height / 2};
  labelBoxes.push(pillBox);

  const areaSize = LAYOUT.labels.citySize;
  const labelFrames = useMemo(() => buildAdministrativeLabelTimeline(props, model), [
    props.steps, props.administrativePlaces, props.durationInFrames, props.fps, props.width,
    props.height, props.originLabel, props.destinationLabel, props.attribution,
    props.totalDistanceMeters, model,
  ]);
  const areaLabels = labelFrames[frame] ?? [];
  for (const label of areaLabels) {
    if (label.opacity >= 0.1) labelBoxes.push(label.box);
  }

  const roadLabels = highwayLabels(model).flatMap((label) => {
    const point = toScreen(camera, pointAtDistance(model, label.distance));
    if (point.x < 90 || point.x > props.width - 90 || !inMapArea(point.y)) return [];
    if (Math.hypot(point.x - vehicle.x, point.y - vehicle.y) < 80) return [];
    if (Math.hypot(point.x - origin.x, point.y - origin.y) < 90
      || Math.hypot(point.x - destination.x, point.y - destination.y) < 90) return [];
    const angle = headingAtDistance(model, label.distance);
    const x = clamp(point.x - Math.sin(angle) * 20, 90, props.width - 90);
    const y = clamp(point.y + Math.cos(angle) * 20, content.top + 10, content.bottom - 10);
    const halfWidth = (estimateTextWidth(label.road, LAYOUT.labels.roadSize) + 16) / 2;
    if (x - halfWidth < 10 || x + halfWidth > props.width - 10) return [];
    const box = {left: x - halfWidth, right: x + halfWidth, top: y - 24, bottom: y + 12};
    if (labelBoxes.some((other) => overlaps(box, other))) return [];
    labelBoxes.push(box);
    return [{road: label.road, distance: label.distance, x, y}];
  });

  const mainTitle = `${props.originLabel} → ${props.destinationLabel}`;
  const mainSize = fitFontSize(mainTitle, props.width - 2 * LAYOUT.title.sideMargin,
    LAYOUT.title.mainSize, 44);
  const mainText = truncateText(mainTitle, props.width - 2 * LAYOUT.title.sideMargin, mainSize);

  return <AbsoluteFill data-m2v-driving="route"
    style={{background: MAP_BG, fontFamily: 'var(--m2v-font, "M2V Inter", "M2V Sans", sans-serif)'}}>
    <svg width={props.width} height={props.height} viewBox={`0 0 ${props.width} ${props.height}`}
      role="img" aria-label={`${props.originLabel}到${props.destinationLabel}的模拟行程`}
      data-m2v-driving-frame={frame}>
      <g data-m2v-camera="true" data-m2v-scale={camera.scale.toFixed(8)}
        transform={`translate(${camera.tx} ${camera.ty}) scale(${camera.scale})`}>
        {props.basemap && <>
          <image data-m2v-basemap="overview" href={props.basemap.overview.dataUri}
            x={props.basemap.overview.projected.left} y={props.basemap.overview.projected.top}
            width={props.basemap.overview.projected.width}
            height={props.basemap.overview.projected.height}
            preserveAspectRatio="none" opacity={1} />
          <g data-m2v-basemap="follow" data-m2v-basemap-layer="follow"
            data-m2v-basemap-visible-count={visibleTiles.length}
            data-m2v-basemap-opacity={opacity.toFixed(4)} opacity={opacity}>
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
          stroke={UNWALKED} strokeWidth={6} strokeLinejoin="round" strokeLinecap="round"
          vectorEffect="non-scaling-stroke" />
        {distance > 0 && walked.length > 1 && <>
          <polyline data-m2v-walked-underlay="true" points={polylinePoints(walked)} fill="none"
            stroke="#ffffff" strokeWidth={13} strokeLinejoin="round" strokeLinecap="round"
            vectorEffect="non-scaling-stroke" opacity={0.9} />
          <polyline data-m2v-walked="true" points={polylinePoints(walked)} fill="none"
            stroke={WALKED} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round"
            vectorEffect="non-scaling-stroke" />
        </>}
      </g>

      {roadLabels.map((label) => <text key={roadLabelKey(label)}
        data-m2v-road-label={label.road} x={label.x} y={label.y} textAnchor="middle"
        fill="#1f4f82" fontSize={LAYOUT.labels.roadSize} fontWeight={600} stroke="#ffffff"
        strokeWidth={7} paintOrder="stroke" strokeLinejoin="round">{label.road}</text>)}

      {areaLabels.map((label) => <text key={`area-${label.adcode}`}
        data-m2v-administrative-label={label.name}
        data-m2v-administrative-level={label.level}
        x={label.x} y={label.y} textAnchor="middle"
        opacity={label.opacity.toFixed(4)}
        fill={INK} fontSize={areaSize} fontWeight={LAYOUT.labels.cityWeight}
        stroke="#ffffff" strokeWidth={LAYOUT.labels.cityStrokeWidth} paintOrder="stroke"
        strokeLinejoin="round">{label.name}</text>)}

      {visible(origin) && <g data-m2v-origin="true">
        <circle cx={origin.x} cy={origin.y} r={12} fill={WALKED} stroke="#ffffff" strokeWidth={4} />
        <text data-m2v-origin-label="true" x={clamp(origin.x,
          (estimateTextWidth(originText, originSize) + 16) / 2 + 10,
          props.width - (estimateTextWidth(originText, originSize) + 16) / 2 - 10)}
          y={markerLabelY(origin.y, props.height)} textAnchor="middle" fill={INK}
          fontSize={originSize} fontWeight={700} stroke="#ffffff" strokeWidth={7}
          paintOrder="stroke" strokeLinejoin="round">{originText}</text>
      </g>}

      {visible(destination) && <g data-m2v-destination="true">
        <circle cx={destination.x} cy={destination.y} r={15} fill="none" stroke={INK} strokeWidth={5} />
        <circle cx={destination.x} cy={destination.y} r={4} fill={INK} />
        <text data-m2v-destination-label="true" x={clamp(destination.x,
          (estimateTextWidth(destinationText, destinationSize) + 16) / 2 + 10,
          props.width - (estimateTextWidth(destinationText, destinationSize) + 16) / 2 - 10)}
          y={markerLabelY(destination.y, props.height)} textAnchor="middle" fill={INK}
          fontSize={destinationSize} fontWeight={700} stroke="#ffffff" strokeWidth={7}
          paintOrder="stroke" strokeLinejoin="round">{destinationText}</text>
      </g>}

      <g data-m2v-vehicle="true" data-m2v-distance={distance.toFixed(1)}
        data-m2v-traveled={traveled.toFixed(1)}
        data-m2v-x={vehicle.x.toFixed(2)} data-m2v-y={vehicle.y.toFixed(2)}
        data-m2v-heading={heading.toFixed(3)} transform={`translate(${vehicle.x} ${vehicle.y}) rotate(${heading})`}>
        <circle r={26} fill={WALKED} opacity={0.16} />
        <path d="M 20 0 L -12 11 L -6 0 L -12 -11 Z" fill="#ffffff" stroke={INK}
          strokeWidth={2.5} strokeLinejoin="round" />
      </g>

      <g data-m2v-distance-pill="true" data-m2v-traveled={traveled.toFixed(1)}>
        <rect x={pill.cx - pill.width / 2} y={pill.cy - pill.height / 2}
          width={pill.width} height={pill.height} rx={pill.height / 2}
          fill="rgba(255,255,255,0.95)" stroke="#d5dee8" strokeWidth={2} />
        <text data-m2v-distance-text="true" x={pill.cx} y={pill.cy} textAnchor="middle"
          dominantBaseline="middle" fill={INK} fontSize={LAYOUT.labels.pillSize}
          fontWeight={700}>{pillText}</text>
      </g>

      <g data-m2v-title="true">
        <rect x={0} y={0} width={props.width} height={TITLE_HEIGHT} fill={PANEL} />
        <text data-m2v-title-kicker="true" x={props.width / 2} y={LAYOUT.title.kickerY}
          textAnchor="middle" fill={MUTED} fontSize={LAYOUT.title.kickerSize}
          fontWeight={500}>模拟行程</text>
        <text data-m2v-title-main="true" x={props.width / 2} y={LAYOUT.title.mainY}
          textAnchor="middle" fill={INK} fontSize={mainSize} fontWeight={700}>{mainText}</text>
        <line x1={0} y1={TITLE_HEIGHT} x2={props.width} y2={TITLE_HEIGHT}
          stroke="#dfe3e8" strokeWidth={2} />
      </g>

      <g data-m2v-attribution-box="true">
        <rect x={attributionBox.left} y={attributionBox.top}
          width={attributionBox.right - attributionBox.left}
          height={attributionBox.bottom - attributionBox.top} rx={9}
          fill="rgba(255,255,255,0.9)" />
        <text data-m2v-attribution="true" x={props.width - 52}
          y={props.height - 46} textAnchor="end" fill={MUTED}
          fontSize={attributionSize}>{attributionText}</text>
      </g>
    </svg>
  </AbsoluteFill>;
}
