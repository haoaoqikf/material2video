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
  distanceForFrame, formatDistance, headingAtDistance, headingNear, highwayLabels, pointAtDistance,
  projectPoint, roadLabelKey, selectVisibleTiles, smoothstep, timeline, toScreen, walkedPoints,
  type DrivingRouteProps, type ProjectedPoint, type RouteModel,
} from './route';
import { LAYOUT, contentRect } from './layout';
import { MapLayer } from './MapLayer';
import { estimateTextWidth, fitFontSize, placeDistancePill, truncateText } from './labels';

export type { DrivingRouteProps } from './route';
export {
  basemapOpacity, buildRouteModel, buildTileIndex, cameraForFrame, displayDistanceMeters,
  distanceForFrame, easeOutQuad, fitCamera, fitCameraInContent, formatDistance, headingAtDistance,
  headingNear,
  highwayLabels, pointAtDistance, projectPoint, roadLabelKey, selectVisibleTiles, smoothstep,
  smoothedPointAtDistance, timeline, toScreen, tileKey, walkedPoints,
} from './route';

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

type Box = {left: number; right: number; top: number; bottom: number};

function overlaps(first: Box, second: Box): boolean {
  return !(first.right < second.left || first.left > second.right
    || first.bottom < second.top || first.top > second.bottom);
}

/** 有符号屏幕距离：分离为正，重叠为负。 */
function boxClearance(first: Box, second: Box): number {
  const dx = Math.max(second.left - first.right, first.left - second.right, 0);
  const dy = Math.max(second.top - first.bottom, first.top - second.bottom, 0);
  if (dx > 0 || dy > 0) return Math.hypot(dx, dy);
  return -Math.min(first.right - second.left, second.right - first.left,
    first.bottom - second.top, second.bottom - first.top);
}

/** 行政区文字在大幅变焦时暂时隐去，避免文字随瓦片缩放高速掠过。 */
export function cameraMotionLabelOpacity(frame: number, props: DrivingRouteProps,
                                          spans: ReturnType<typeof timeline>): number {
  const fadeFrames = Math.max(1, Math.round(props.fps * LAYOUT.camera.cameraSmoothingSeconds));
  if (frame < spans.openingFrames) {
    return smoothstep((frame - spans.openingFrames + fadeFrames) / fadeFrames);
  }
  const overviewStart = spans.endingStart + spans.pulloutFrames;
  if (frame < spans.endingStart) return 1;
  if (frame < overviewStart) {
    return 1 - smoothstep((frame - spans.endingStart) / fadeFrames);
  }
  return smoothstep((frame - overviewStart) / fadeFrames);
}

type AreaLabel = {name: string; level: string; adcode: string; x: number; y: number;
  opacity: number; box: Box};

const labelTimelineCache = new WeakMap<object, WeakMap<object, {
  signature: string; frames: AreaLabel[][]
}>>();

const ENDPOINT_VISIBLE_MARGIN = 24;
const LABEL_COLLISION_GAP = 4;

function buildAreaLabelsAtFrame(props: DrivingRouteProps, model: RouteModel, frame: number): AreaLabel[] {
  const camera = cameraForFrame(model, frame, props.durationInFrames, props.fps, props.width, props.height);
  const origin = toScreen(camera, model.projected[0]);
  const destination = toScreen(camera, model.projected[model.projected.length - 1]);
  // 与组件实际绘制端点标签的可见条件保持一致，避免屏幕外端点无形中挡住行政区标签。
  const visible = (point: ProjectedPoint) => point.x >= ENDPOINT_VISIBLE_MARGIN
    && point.x <= props.width - ENDPOINT_VISIBLE_MARGIN
    && point.y >= LAYOUT.title.height
    && point.y <= props.height - ENDPOINT_VISIBLE_MARGIN;
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
    endpointBoxes.push({left: x - halfWidth, right: x + halfWidth, top: y - 36, bottom: y + 12});
  };
  addEndpoint(origin, originText, originSize);
  addEndpoint(destination, destinationText, destinationSize);

  const endpointNames = [props.originLabel, props.destinationLabel]
    .map((label) => label.replace(/[市区县]$/u, '')).filter((label) => label.length > 0);
  const areaSize = LAYOUT.labels.citySize;
  const areaOffset = Math.round(areaSize * 1.2);
  const areaBoxTop = Math.round(areaSize * 0.9);
  const areaBoxBottom = Math.round(areaSize * 0.3);
  const areaBoxes: Box[] = [];
  const spans = timeline(props.durationInFrames, props.fps);
  const pulloutProgress = clamp((frame - spans.endingStart) / spans.pulloutFrames, 0, 1);
  const overviewStart = spans.endingStart + spans.pulloutFrames;
  return [...(props.administrativePlaces ?? [])]
    .filter((place) => frame < overviewStart || place.level === 'city')
    .sort((first, second) => (first.level === 'city' ? 0 : 1)
      - (second.level === 'city' ? 0 : 1)
      || first.adcode.localeCompare(second.adcode, 'en')
      || first.name.localeCompare(second.name, 'zh-CN'))
    .flatMap((place) => {
      if (!place || !Array.isArray(place.center) || place.center.length !== 2) return [];
      if (endpointNames.some((endpoint) => place.name.includes(endpoint))) return [];
      if (place.level === 'county' && place.name.endsWith('区')) return [];
      const point = toScreen(camera, projectPoint(place.center));
      // 地理锚点直接映射到屏幕，不做边缘收拢：标签随地图连续滑入滑出画面，
      // 由视口自然裁切，避免在边缘停住若干帧再突然起步。
      const x = point.x;
      const y = point.y - areaOffset;
      const halfWidth = (estimateTextWidth(place.name, areaSize) + 16) / 2;
      const box = {left: x - halfWidth, right: x + halfWidth,
        top: y - areaBoxTop, bottom: y + areaBoxBottom};
      const blockerClearance = endpointBoxes.reduce((nearest, other) =>
        Math.min(nearest, boxClearance(box, other)), Number.POSITIVE_INFINITY);
      const priorLabelClearance = areaBoxes.reduce((nearest, other) =>
        Math.min(nearest, boxClearance(box, other)), Number.POSITIVE_INFINITY);
      // 可见性只有“完全不透明/完全隐藏”两态：标签之间或与端点文字的相对位置在
      // 跟随段固定，状态不会逐帧翻转；真实重叠时由时间平滑完成一次连续淡出。
      // 车辆、里程牌、署名与标题带是绘制在标签之上的不透明覆盖物，允许短暂遮挡，
      // 不再为它们整体调暗标签——那会让标签在半透明状态停留近半秒，像在闪烁。
      const blocked = Math.min(blockerClearance, priorLabelClearance) < LABEL_COLLISION_GAP;
      const baseOpacity = blocked ? 0 : 1;
      const opacity = place.level === 'city' ? baseOpacity
        : baseOpacity * (1 - pulloutProgress);
      areaBoxes.push(box);
      return [{name: place.name, level: place.level, adcode: place.adcode, x, y, opacity, box}];
    });
}

/** 用与相机平滑时长一致的居中窗口平滑碰撞透明度，降低逐帧显隐变化。 */
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
  const radius = Math.round(props.fps * LAYOUT.camera.cameraSmoothingSeconds / 2);
  const spans = timeline(props.durationInFrames, props.fps);
  const overviewStart = spans.endingStart + spans.pulloutFrames;
  const smoothed = raw.map((labels, frame) => labels.map((label) => {
    let total = 0;
    let count = 0;
    for (let sample = Math.max(0, frame - radius); sample <= Math.min(raw.length - 1, frame + radius); sample += 1) {
      const sameLabel = rawByFrame[sample]!.get(label.adcode);
      total += sameLabel?.opacity ?? 0;
      count += 1;
    }
    const settledOpacity = label.level === 'city' || frame < overviewStart ? total / count : 0;
    return {...label, opacity: settledOpacity * cameraMotionLabelOpacity(frame, props, spans)};
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
  const spans = timeline(props.durationInFrames, props.fps);
  const headingDistance = frame < spans.openingFrames ? 0 : distance;
  const previousHeadingDistance = frame <= spans.openingFrames ? 0
    : distanceForFrame(frame - 1, props.durationInFrames, props.fps, model.lengthMeters);
  const previousHeading = headingAtDistance(model, previousHeadingDistance);
  const heading = (headingNear(previousHeading, headingAtDistance(model, headingDistance)) * 180) / Math.PI;
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

  const areaSize = LAYOUT.labels.citySize;
  const labelFrames = useMemo(() => buildAdministrativeLabelTimeline(props, model), [
    props.steps, props.administrativePlaces, props.durationInFrames, props.fps, props.width,
    props.height, props.originLabel, props.destinationLabel, props.attribution,
    props.totalDistanceMeters, model,
  ]);
  const areaLabels = labelFrames[frame] ?? [];
  const visibleAreaBoxes = areaLabels.filter((label) => label.opacity >= 0.1)
    .map((label) => label.box);

  // 里程牌是次要覆盖物：优先选择不压住可见行政区标签的候选位置，
  // 避免在车辆经过城市时把最重要的地名盖住。
  const pillText = `已行驶 ${formatDistance(traveled)}`;
  const pill = placeDistancePill(vehicle.x, vehicle.y, pillText, props.width, props.height,
    TITLE_HEIGHT + 12, [attributionBox, ...endpointBoxes, ...visibleAreaBoxes]);
  const pillBox = {left: pill.cx - pill.width / 2, right: pill.cx + pill.width / 2,
    top: pill.cy - pill.height / 2, bottom: pill.cy + pill.height / 2};
  labelBoxes.push(pillBox);
  for (const box of visibleAreaBoxes) labelBoxes.push(box);

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
      <MapLayer camera={camera} model={model} distance={distance} walked={walked}
        basemap={props.basemap} visibleTiles={visibleTiles} followOpacity={opacity}
        walkedColor={WALKED} unwalkedColor={UNWALKED} />

      {roadLabels.map((label) => <text key={roadLabelKey(label)}
        data-m2v-road-label={label.road} x={label.x} y={label.y} textAnchor="middle"
        fill="#1f4f82" fontSize={LAYOUT.labels.roadSize} fontWeight={600} stroke="#ffffff"
        strokeWidth={7} paintOrder="stroke" strokeLinejoin="round">{label.road}</text>)}

      {areaLabels.map((label) => <text key={`area-${label.adcode}`}
        data-m2v-administrative-label={label.name}
        data-m2v-administrative-level={label.level}
        x={label.x.toFixed(2)} y={label.y.toFixed(2)} textAnchor="middle"
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
