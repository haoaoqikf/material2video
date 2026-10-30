/**
 * 自驾路线 composition：北向二维路线、贴路小车、跟随镜头与必要标注。
 *
 * 位置、朝向、已走路线与镜头全部来自 `./driving/route` 的纯函数；本文件只做
 * 当前帧取数与绘制，不保存跨帧状态。文字只承担地点、道路名称、距离结果和
 * 来源署名，不添加制作说明。
 */
import { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import {
  buildRouteModel, cameraForFrame, clamp, displayDistanceMeters, distanceForFrame, formatDistance,
  headingAtDistance, highwayLabels, pointAtDistance, roadLabelKey, toScreen, walkedPoints,
  type DrivingRouteProps, type ProjectedPoint,
} from './driving/route';

export type { DrivingRouteProps } from './driving/route';
export {
  buildRouteModel, cameraForFrame, displayDistanceMeters, distanceForFrame, fitCamera, formatDistance,
  headingAtDistance, highwayLabels, pointAtDistance, projectPoint, roadLabelKey, smoothstep, toScreen,
  walkedPoints,
} from './driving/route';

const INK = '#eaf6ff';
const MUTED = '#9fc4d8';
const WALKED = '#39d9e8';
const UNWALKED = '#2b4a68';
const BACKGROUND = '#06111c';

function markerLabelY(y: number, height: number): number {
  return y < 84 ? y + 48 : Math.min(y - 30, height - 40);
}

function polylinePoints(points: ProjectedPoint[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(' ');
}

export function DrivingRoute(props: DrivingRouteProps) {
  const frame = useCurrentFrame();
  const model = useMemo(() => buildRouteModel(props.steps), [props.steps]);
  const camera = cameraForFrame(model, frame, props.durationInFrames, props.fps, props.width, props.height);
  const distance = distanceForFrame(frame, props.durationInFrames, props.fps, model.lengthMeters);
  const traveling = pointAtDistance(model, distance);
  const heading = (headingAtDistance(model, distance) * 180) / Math.PI;
  const vehicle = toScreen(camera, traveling);
  const origin = toScreen(camera, model.projected[0]);
  const destination = toScreen(camera, model.projected[model.projected.length - 1]);
  const walked = walkedPoints(model, distance);
  const traveled = displayDistanceMeters(distance, model.lengthMeters, props.totalDistanceMeters);
  const visible = (point: ProjectedPoint) => point.x >= 24 && point.x <= props.width - 24
    && point.y >= 24 && point.y <= props.height - 24;

  const labelBoxes: {left: number; right: number; top: number; bottom: number}[] = [];
  const roadLabels = highwayLabels(model).flatMap((label) => {
    const point = toScreen(camera, pointAtDistance(model, label.distance));
    if (point.x < 120 || point.x > props.width - 120 || point.y < 60 || point.y > props.height - 90) return [];
    if (Math.hypot(point.x - vehicle.x, point.y - vehicle.y) < 64) return [];
    if (Math.hypot(point.x - origin.x, point.y - origin.y) < 64
      || Math.hypot(point.x - destination.x, point.y - destination.y) < 64) return [];
    const angle = headingAtDistance(model, label.distance);
    const x = clamp(point.x - Math.sin(angle) * 20, 120, props.width - 120);
    const y = clamp(point.y + Math.cos(angle) * 20, 60, props.height - 70);
    const halfWidth = (label.road.length * 12) / 2 + 10;
    const box = {left: x - halfWidth, right: x + halfWidth, top: y - 22, bottom: y + 10};
    if (labelBoxes.some((other) => !(box.right < other.left || box.left > other.right
      || box.bottom < other.top || box.top > other.bottom))) return [];
    labelBoxes.push(box);
    return [{road: label.road, distance: label.distance, x, y}];
  });

  return <AbsoluteFill data-m2v-driving="route"
    style={{background: `radial-gradient(ellipse at 50% 42%, #0c2236 0%, ${BACKGROUND} 68%)`,
      fontFamily: 'var(--m2v-font, "M2V Inter", "M2V Sans", sans-serif)'}}>
    <svg width={props.width} height={props.height} viewBox={`0 0 ${props.width} ${props.height}`}
      role="img" aria-label={`${props.originLabel}到${props.destinationLabel}的驾车路线动画`}
      data-m2v-driving-frame={frame}>
      <g data-m2v-camera="true" data-m2v-scale={camera.scale.toFixed(8)}
        transform={`translate(${camera.tx} ${camera.ty}) scale(${camera.scale})`}>
        <polyline data-m2v-route="true" points={polylinePoints(model.projected)} fill="none"
          stroke={UNWALKED} strokeWidth={7} strokeLinejoin="round" strokeLinecap="round"
          vectorEffect="non-scaling-stroke" />
        {distance > 0 && walked.length > 1 && <polyline data-m2v-walked="true" points={polylinePoints(walked)}
          fill="none" stroke={WALKED} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round"
          vectorEffect="non-scaling-stroke" />}
      </g>

      {roadLabels.map((label) => <text key={roadLabelKey(label)}
        data-m2v-road-label={label.road} x={label.x} y={label.y} textAnchor="middle"
        fill={MUTED} fontSize={24} fontWeight={500} stroke={BACKGROUND} strokeWidth={7}
        paintOrder="stroke" strokeLinejoin="round">{label.road}</text>)}

      {visible(origin) && <g data-m2v-origin="true">
        <circle cx={origin.x} cy={origin.y} r={12} fill={WALKED} stroke={BACKGROUND} strokeWidth={4} />
        <text data-m2v-origin-label="true" x={clamp(origin.x, 90, props.width - 90)}
          y={markerLabelY(origin.y, props.height)} textAnchor="middle" fill={INK} fontSize={34}
          fontWeight={700} stroke={BACKGROUND} strokeWidth={7} paintOrder="stroke"
          strokeLinejoin="round">{props.originLabel}</text>
      </g>}

      {visible(destination) && <g data-m2v-destination="true">
        <circle cx={destination.x} cy={destination.y} r={15} fill="none" stroke={INK} strokeWidth={5} />
        <circle cx={destination.x} cy={destination.y} r={4} fill={INK} />
        <text data-m2v-destination-label="true" x={clamp(destination.x, 90, props.width - 90)}
          y={markerLabelY(destination.y, props.height)} textAnchor="middle" fill={INK} fontSize={34}
          fontWeight={700} stroke={BACKGROUND} strokeWidth={7} paintOrder="stroke"
          strokeLinejoin="round">{props.destinationLabel}</text>
      </g>}

      <g data-m2v-vehicle="true" data-m2v-distance={distance.toFixed(1)}
        data-m2v-traveled={traveled.toFixed(1)}
        data-m2v-x={vehicle.x.toFixed(2)} data-m2v-y={vehicle.y.toFixed(2)}
        data-m2v-heading={heading.toFixed(3)} transform={`translate(${vehicle.x} ${vehicle.y}) rotate(${heading})`}>
        <circle r={24} fill={WALKED} opacity={0.18} />
        <path d="M 20 0 L -12 11 L -6 0 L -12 -11 Z" fill="#f2fdff" stroke={BACKGROUND}
          strokeWidth={2.5} strokeLinejoin="round" />
      </g>

      <text data-m2v-distance-label="true" x={72} y={props.height - 58} fill="#cfe6f5" fontSize={24}
        fontWeight={500}>已行驶 {formatDistance(traveled)} · 全程 {formatDistance(props.totalDistanceMeters)}</text>
      <text data-m2v-attribution="true" x={props.width - 72} y={props.height - 52} textAnchor="end"
        fill="#7f9bb0" fontSize={24}>{props.attribution}</text>
    </svg>
  </AbsoluteFill>;
}
