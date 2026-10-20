/** 俯视道路与车辆的基础画件；所有位置都由轨迹采样传入。 */
import {COLOR, SIZE} from './stage';
import {TRAFFIC, loopPoint} from './traffic';

export function LoopRoad({cx, cy, width = 84, opacity = 1}: {
  cx: number; cy: number; width?: number; opacity?: number;
}) {
  const {rx, ry} = TRAFFIC.loop;
  return (
    <g opacity={opacity}>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={COLOR.edge} strokeWidth={width + 10}/>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={COLOR.road} strokeWidth={width}/>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={COLOR.roadLine} strokeWidth={2.5}
        strokeDasharray="20 26" opacity={0.9}/>
    </g>
  );
}

export function StraightRoad({width, y, height, cameraS, center = 540}: {
  width: number; y: number; height: number; cameraS: number; center?: number;
}) {
  const middle = y + height / 2;
  const first = Math.floor((cameraS - 700) / 64) * 64;
  const dashes = Array.from({length: 24}, (_, index) => first + index * 64);
  return (
    <g>
      <rect x={0} y={y} width={width} height={height} fill={COLOR.road}/>
      <line x1={0} x2={width} y1={y + 3} y2={y + 3} stroke={COLOR.edge} strokeWidth={3}/>
      <line x1={0} x2={width} y1={y + height - 3} y2={y + height - 3} stroke={COLOR.edge} strokeWidth={3}/>
      {dashes.map(s => {
        const x = center + (s - cameraS);
        return x > -40 && x < width + 40
          ? <line key={s} x1={x} x2={x + 28} y1={middle} y2={middle} stroke={COLOR.roadLine}
              strokeWidth={3} opacity={0.95}/>
          : null;
      })}
    </g>
  );
}

export function CarMark({x, y, heading, braking, focus = false, label, scale = 1, opacity = 1}: {
  x: number; y: number; heading: number; braking: boolean;
  focus?: boolean; label?: string | number; scale?: number; opacity?: number;
}) {
  const length = TRAFFIC.car.length * scale;
  const width = TRAFFIC.car.width * scale;
  const degrees = (heading * 180) / Math.PI;
  return (
    <g opacity={opacity}>
      <g transform={`translate(${x} ${y}) rotate(${degrees})`}>
        {focus && <rect x={-length / 2 - 8} y={-width / 2 - 8} width={length + 16} height={width + 16}
          rx={12} fill="none" stroke={COLOR.accent} strokeWidth={3.5} opacity={0.95}/>}
        <rect x={-length / 2} y={-width / 2} width={length} height={width} rx={width * 0.32}
          fill={COLOR.car}/>
        <rect x={-length * 0.16} y={-width * 0.34} width={length * 0.4} height={width * 0.68}
          rx={width * 0.16} fill={COLOR.carLight}/>
        <rect x={length * 0.2} y={-width * 0.34} width={length * 0.12} height={width * 0.68}
          rx={width * 0.08} fill={COLOR.glass} opacity={0.85}/>
        {braking && <>
          <rect x={-length / 2 - 1 * scale} y={-width * 0.4} width={4 * scale} height={width * 0.8}
            rx={2 * scale} fill={COLOR.brake}/>
          <circle cx={-length / 2 + 1 * scale} cy={-width * 0.3} r={10 * scale} fill={COLOR.brake} opacity={0.26}/>
          <circle cx={-length / 2 + 1 * scale} cy={width * 0.3} r={10 * scale} fill={COLOR.brake} opacity={0.26}/>
        </>}
        <circle cx={-length / 2 + 2 * scale} cy={-width * 0.3} r={3.4 * scale}
          fill={braking ? COLOR.brake : '#8a5447'}/>
        <circle cx={-length / 2 + 2 * scale} cy={width * 0.3} r={3.4 * scale}
          fill={braking ? COLOR.brake : '#8a5447'}/>
        <circle cx={length / 2 - 2 * scale} cy={-width * 0.3} r={2.2 * scale} fill="#f1e2b8" opacity={0.85}/>
        <circle cx={length / 2 - 2 * scale} cy={width * 0.3} r={2.2 * scale} fill="#f1e2b8" opacity={0.85}/>
      </g>
      {label !== undefined && (
        <text x={x} y={y + 5 * scale} textAnchor="middle" fontSize={SIZE.number * scale}
          fontWeight={700} fill={COLOR.paper} stroke={COLOR.ink} strokeWidth={0.4}
          style={{pointerEvents: 'none'}}>{label}</text>
      )}
    </g>
  );
}

/** 沿环路画一段带颜色的弧线，用来标出低速区域或传播轨迹。 */
export function ArcPath({cx, cy, fromS, lengthS, stroke, width, opacity = 1, dash, expand = 1}: {
  cx: number; cy: number; fromS: number; lengthS: number;
  stroke: string; width: number; opacity?: number; dash?: string; expand?: number;
}) {
  const steps = Math.max(2, Math.ceil(Math.abs(lengthS) / 12));
  const points = Array.from({length: steps + 1}, (_, index) => {
    const point = loopPoint(fromS + (lengthS * index) / steps);
    return `${cx + point.x * expand},${cy + point.y * expand}`;
  });
  return <polyline points={points.join(' ')} fill="none" stroke={stroke} strokeWidth={width}
    strokeLinecap="round" strokeLinejoin="round" opacity={opacity} strokeDasharray={dash}/>;
}
