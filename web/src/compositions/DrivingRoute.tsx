/**
 * 自驾路线 composition：竖屏浅色普通道路地图、贴路小车、居中标题与车辆旁里程。
 *
 * 位置、朝向、已走路线与镜头全部来自 `./driving/route` 的纯函数；本文件只做
 * 当前帧取数与绘制，不保存跨帧状态。道路底图与路线使用同一 GCJ-02 投影。
 */
import { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import {
  basemapBlend, buildRouteModel, cameraForFrame, clamp, displayDistanceMeters, distanceForFrame,
  fitCameraInContent, formatDistance, headingAtDistance, highwayLabels, pointAtDistance,
  projectPoint, roadLabelKey, toScreen, walkedPoints,
  type DrivingRouteProps, type ProjectedPoint, type RouteCity,
} from './driving/route';
import { LAYOUT, contentRect } from './driving/layout';
import { estimateTextWidth, fitFontSize, placeDistancePill, truncateText } from './driving/labels';

export type { DrivingRouteProps } from './driving/route';
export {
  basemapBlend, buildRouteModel, cameraForFrame, displayDistanceMeters, distanceForFrame,
  fitCamera, fitCameraInContent, formatDistance, headingAtDistance, highwayLabels, pointAtDistance,
  projectPoint, roadLabelKey, smoothstep, toScreen, walkedPoints,
} from './driving/route';

const INK = '#142433';
const MUTED = '#5b6b7c';
const WALKED = '#1f6feb';
const UNWALKED = '#8b98a7';
const MAP_BG = '#f3f0e9';
const PANEL = 'rgba(255,255,255,0.95)';
const TITLE_HEIGHT = LAYOUT.title.height;

function markerLabelY(y: number, height: number): number {
  return y < TITLE_HEIGHT + 84 ? y + 48 : Math.min(y - 30, height - 40);
}

function polylinePoints(points: ProjectedPoint[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(' ');
}

type Box = {left: number; right: number; top: number; bottom: number};

function overlaps(first: Box, second: Box): boolean {
  return !(first.right < second.left || first.left > second.right
    || first.bottom < second.top || first.top > second.bottom);
}

export function DrivingRoute(props: DrivingRouteProps) {
  const frame = useCurrentFrame();
  const model = useMemo(() => buildRouteModel(props.steps), [props.steps]);
  const content = contentRect(props.width, props.height);
  const fullCamera = fitCameraInContent(model.bounds, props.width, props.height);
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
  const blend = basemapBlend(camera.scale, fullCamera.scale);
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

  const endpointNames = [props.originLabel, props.destinationLabel]
    .map((label) => label.replace(/[市区县]$/u, ''))
    .filter((label) => label.length > 0);
  const cityBoxes: Box[] = [];
  const cityLabels = (props.cities ?? []).flatMap((city: RouteCity, index: number) => {
    if (!city || !Array.isArray(city.location) || city.location.length !== 2) return [];
    if (endpointNames.some((endpoint) => city.name.includes(endpoint))) return [];
    const point = toScreen(camera, projectPoint(city.location));
    if (point.x < 40 || point.x > props.width - 40) return [];
    if (Math.hypot(point.x - vehicle.x, point.y - vehicle.y) < 80) return [];
    if (Math.hypot(point.x - origin.x, point.y - origin.y) < 80
      || Math.hypot(point.x - destination.x, point.y - destination.y) < 80) return [];
    const halfWidth = (estimateTextWidth(city.name, LAYOUT.labels.citySize) + 16) / 2;
    for (const offset of index % 2 === 0 ? [-24, 34] : [34, -24]) {
      const y = point.y + offset;
      if (!inMapArea(y)) continue;
      const box = {left: point.x - halfWidth, right: point.x + halfWidth, top: y - 20, bottom: y + 8};
      if (box.left < 10 || box.right > props.width - 10) continue;
      if (labelBoxes.some((other) => overlaps(box, other))) continue;
      if (cityBoxes.some((other) => overlaps(box, other))) continue;
      cityBoxes.push(box);
      return [{name: city.name, x: point.x, y}];
    }
    return [];
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
          <image data-m2v-basemap="follow" href={props.basemap.follow.dataUri}
            x={props.basemap.follow.projected.left} y={props.basemap.follow.projected.top}
            width={props.basemap.follow.projected.width}
            height={props.basemap.follow.projected.height}
            preserveAspectRatio="none" opacity={blend} />
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

      {cityLabels.map((label) => <text key={`city-${label.name}`}
        data-m2v-city-label={label.name} x={label.x} y={label.y} textAnchor="middle"
        fill="#2a3b4d" fontSize={LAYOUT.labels.citySize} fontWeight={500} stroke="#ffffff"
        strokeWidth={6} paintOrder="stroke" strokeLinejoin="round">{label.name}</text>)}

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
