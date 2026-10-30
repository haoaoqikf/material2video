/**
 * 两层框架住宅建造示意：程序化构件 + 等轴测确定性逐帧动画。
 *
 * 所有构件、阶段与镜头都由 materials 推导；同一帧不读取挂钟或上一帧状态。
 */
import { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

export type Opening = {
  id: string;
  floor: number;
  side: 'front' | 'back' | 'left' | 'right';
  offset: number;
  width: number;
  height: number;
};

export type BuildingProps = {
  schemaVersion: number;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  building: {
    schemaVersion: number;
    canvas: {width: number; height: number};
    house: {
      width: number;
      depth: number;
      floors: number;
      floorHeight: number;
      bayCount: number;
      roofHeight: number;
      wallThickness: number;
      foundationDepth: number;
      sitePadding: number;
      openings: Opening[];
    };
  };
  construction: {
    schemaVersion: number;
    durationSeconds: number;
    fps: number;
    stages: {id: string; label: string; startSeconds: number; endSeconds: number}[];
    camera: {startAzimuth: number; endAzimuth: number; elevation: number};
  };
};

type Vec3 = [number, number, number];
type Component = {
  id: string;
  stage: number;
  box: {x: number; y: number; z: number; w: number; h: number; d: number};
  color: string;
  order: number;
};

const INK = '#2b2f33';
const BACKGROUND = '#ece7dd';
const GROUND = '#b9b09f';
const FOUNDATION = '#9a948b';
const CONCRETE = '#c9c3b8';
const CONCRETE_DARK = '#aaa499';
const WALL = '#f3eee5';
const WALL_SIDE = '#e4ddd1';
const WOOD = '#b7865b';
const GLASS = '#8bb7c9';
const ROOF = '#6f756f';
const YARD = '#9caa87';

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function smooth(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

function box(id: string, stage: number, order: number, x: number, y: number, z: number,
             w: number, h: number, d: number, color: string): Component {
  return {id, stage, order, box: {x, y, z, w, h, d}, color};
}

function generate(house: BuildingProps['building']['house']): Component[] {
  const components: Component[] = [];
  const {width, depth, floors, floorHeight, bayCount, roofHeight, wallThickness,
    foundationDepth, sitePadding, openings} = house;
  const halfW = width / 2;
  const halfD = depth / 2;
  const t = wallThickness;

  components.push(box('site', 0, 0, -halfW - sitePadding, -0.25, -halfD - sitePadding,
    width + sitePadding * 2, 0.25, depth + sitePadding * 2, GROUND));
  components.push(box('foundation-slab', 1, 0, -halfW - 0.6, -foundationDepth, -halfD - 0.6,
    width + 1.2, foundationDepth, depth + 1.2, FOUNDATION));
  components.push(box('foundation-ring', 1, 1, -halfW, -0.45, -halfD, width, 0.45, t, FOUNDATION));
  components.push(box('foundation-ring-back', 1, 2, -halfW, -0.45, halfD - t, width, 0.45, t,
    FOUNDATION));

  for (let floor = 1; floor <= floors; floor += 1) {
    const base = (floor - 1) * floorHeight;
    components.push(box(`slab-${floor}`, floor === 1 ? 2 : 3, 0,
      -halfW, base - 0.22, -halfD, width, 0.22, depth, CONCRETE));
    for (let bay = 0; bay <= bayCount; bay += 1) {
      const x = -halfW + (width * bay) / bayCount - 0.16;
      for (const z of [-halfD, halfD - 0.32]) {
        components.push(box(`column-${floor}-${bay}-${z < 0 ? 'front' : 'back'}`, floor === 1 ? 2 : 3,
          bay * 2 + (z < 0 ? 0 : 1), x, base, z, 0.32, floorHeight, 0.32, CONCRETE_DARK));
      }
    }
    for (let bay = 0; bay <= bayCount; bay += 1) {
      const x = -halfW + (width * bay) / bayCount;
      components.push(box(`beam-front-${floor}-${bay}`, floor === 1 ? 2 : 3, 20 + bay,
        x === -halfW ? x : x - 0.18, base + floorHeight - 0.35, -halfD, width / bayCount, 0.35, 0.28,
        CONCRETE_DARK));
    }
    components.push(box(`beam-back-${floor}`, floor === 1 ? 2 : 3, 30, -halfW,
      base + floorHeight - 0.35, halfD - 0.28, width, 0.35, 0.28, CONCRETE_DARK));
    components.push(box(`beam-left-${floor}`, floor === 1 ? 2 : 3, 31, -halfW,
      base + floorHeight - 0.35, -halfD, 0.28, 0.35, depth, CONCRETE_DARK));
    components.push(box(`beam-right-${floor}`, floor === 1 ? 2 : 3, 32, halfW - 0.28,
      base + floorHeight - 0.35, -halfD, 0.28, 0.35, depth, CONCRETE_DARK));

    if (floor < floors) {
      const stairX = halfW - 2.1;
      for (let step = 0; step < 6; step += 1) {
        components.push(box(`stair-${floor}-${step}`, 3, 40 + step, stairX,
          base + (step * floorHeight) / 6, -halfD + 1.2 + step * 0.36, 1.4,
          floorHeight / 6, 0.36, WOOD));
      }
    }

    const floorOpenings = openings.filter((opening) => opening.floor === floor);
    for (const side of ['front', 'back', 'left', 'right'] as const) {
      const wallLength = side === 'front' || side === 'back' ? width : depth;
      const sideOpenings = floorOpenings.filter((opening) => opening.side === side);
      const xBreaks = Array.from(new Set([0, wallLength,
        ...sideOpenings.flatMap((opening) => [opening.offset, opening.offset + opening.width])]))
        .filter((value) => value >= 0 && value <= wallLength).sort((a, b) => a - b);
      const yBreaks = Array.from(new Set([0, floorHeight,
        ...sideOpenings.flatMap((opening) => [opening.height])]))
        .filter((value) => value >= 0 && value <= floorHeight).sort((a, b) => a - b);
      for (let xi = 0; xi < xBreaks.length - 1; xi += 1) {
        for (let yi = 0; yi < yBreaks.length - 1; yi += 1) {
          const start = xBreaks[xi];
          const end = xBreaks[xi + 1];
          const low = yBreaks[yi];
          const high = yBreaks[yi + 1];
          if (end - start < 0.02 || high - low < 0.02) continue;
          const cx = (start + end) / 2;
          const cy = (low + high) / 2;
          if (sideOpenings.some((opening) => cx > opening.offset && cx < opening.offset + opening.width
            && cy < opening.height)) continue;
          const id = `wall-${floor}-${side}-${xi}-${yi}`;
          const order = 100 + xi * 10 + yi;
          if (side === 'front' || side === 'back') {
            const z = side === 'front' ? -halfD : halfD - t;
            components.push(box(id, 4, order, -halfW + start, base + low, z, end - start, high - low,
              t, WALL));
          } else {
            const x = side === 'left' ? -halfW : halfW - t;
            components.push(box(id, 4, order, x, base + low, -halfD + start, t, high - low,
              end - start, WALL_SIDE));
          }
        }
      }
    }
  }

  // 屋面板与压顶
  const top = floors * floorHeight;
  components.push(box('roof-slab', 4, 200, -halfW - 0.7, top, -halfD - 0.7,
    width + 1.4, 0.32, depth + 1.4, ROOF));
  components.push(box('roof-ridge', 4, 201, -halfW - 0.7, top + 0.32, -0.25,
    width + 1.4, roofHeight * 0.35, 0.5, ROOF));
  components.push(box('parapet-front', 4, 202, -halfW - 0.7, top + 0.32, -halfD - 0.7,
    width + 1.4, 0.35, 0.25, ROOF));

  for (const opening of openings) {
    const floorBase = (opening.floor - 1) * floorHeight;
    const finish = opening.id.startsWith('door') ? WOOD : GLASS;
    if (opening.side === 'front' || opening.side === 'back') {
      const z = opening.side === 'front' ? -halfD - 0.14 : halfD - 0.02;
      components.push(box(`finish-${opening.id}`, 5, 300, -halfW + opening.offset,
        floorBase, z, opening.width, opening.height, 0.1, finish));
    } else {
      const x = opening.side === 'left' ? -halfW - 0.14 : halfW - 0.02;
      components.push(box(`finish-${opening.id}`, 5, 300, x, floorBase,
        -halfD + opening.offset, 0.1, opening.height, opening.width, finish));
    }
  }

  components.push(box('yard-path', 6, 400, -1.1, 0.02, halfD + 0.2, 2.2, 0.12, sitePadding + 1.5, YARD));
  components.push(box('yard-wall-left', 6, 401, -halfW - sitePadding + 0.4, 0, halfD + 0.3,
    0.3, 1.1, sitePadding + 1.1, WALL_SIDE));
  components.push(box('yard-wall-right', 6, 402, halfW + sitePadding - 0.7, 0, halfD + 0.3,
    0.3, 1.1, sitePadding + 1.1, WALL_SIDE));
  return components;
}

function project(point: Vec3, azimuth: number, elevation: number, scale: number,
                 cx: number, cy: number): {x: number; y: number; depth: number} {
  const [x, y, z] = point;
  const cosA = Math.cos(azimuth);
  const sinA = Math.sin(azimuth);
  const xr = x * cosA - z * sinA;
  const zr = x * sinA + z * cosA;
  return {
    x: cx + xr * scale,
    y: cy - y * scale * Math.cos(elevation) + zr * scale * Math.sin(elevation),
    depth: zr * Math.cos(elevation) + y * Math.sin(elevation),
  };
}

function polygon(points: {x: number; y: number}[]): string {
  return points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ');
}

function shade(color: string, factor: number): string {
  const value = color.replace('#', '');
  const channels = [0, 2, 4].map((index) => parseInt(value.slice(index, index + 2), 16));
  return `#${channels.map((channel) => Math.max(0, Math.min(255, Math.round(channel * factor)))
    .toString(16).padStart(2, '0')).join('')}`;
}

function stageProgress(frame: number, stage: number, stages: BuildingProps['construction']['stages'],
                       fps: number): number {
  const stageSpec = stages[stage];
  if (!stageSpec) return 1;
  return smooth((frame / fps - stageSpec.startSeconds)
    / Math.max(0.01, stageSpec.endSeconds - stageSpec.startSeconds));
}

export function BuildingConstruction(props: BuildingProps) {
  const frame = useCurrentFrame();
  const components = useMemo(() => generate(props.building.house), [props.building.house]);
  const {width, height} = props;
  const camera = props.construction.camera;
  const t = props.durationInFrames <= 1 ? 0 : frame / (props.durationInFrames - 1);
  const azimuth = (camera.startAzimuth + (camera.endAzimuth - camera.startAzimuth) * t) * Math.PI / 180;
  const elevation = camera.elevation * Math.PI / 180;
  const scale = Math.min(width / 30, height / 18);
  const cx = width / 2;
  const cy = height * 0.57;

  const stage = props.construction.stages.find((item) => {
    const seconds = frame / props.fps;
    return seconds >= item.startSeconds && seconds < item.endSeconds;
  }) ?? props.construction.stages[props.construction.stages.length - 1];

  const faces = components.flatMap((component) => {
    const progress = stageProgress(frame, component.stage, props.construction.stages, props.fps);
    if (progress <= 0) return [];
    const lift = (1 - progress) * -0.5;
    const b = component.box;
    const corners = ([
      [b.x, b.y + lift, b.z], [b.x + b.w, b.y + lift, b.z],
      [b.x + b.w, b.y + lift, b.z + b.d], [b.x, b.y + lift, b.z + b.d],
      [b.x, b.y + lift + b.h, b.z], [b.x + b.w, b.y + lift + b.h, b.z],
      [b.x + b.w, b.y + lift + b.h, b.z + b.d], [b.x, b.y + lift + b.h, b.z + b.d],
    ] as Vec3[]).map((corner) => project(corner, azimuth, elevation, scale, cx, cy));
    const definitions: {indices: number[]; factor: number}[] = [
      {indices: [4, 5, 6, 7], factor: 1.06}, {indices: [0, 3, 2, 1], factor: 0.55},
      {indices: [3, 2, 6, 7], factor: 0.88}, {indices: [0, 1, 5, 4], factor: 0.74},
      {indices: [1, 2, 6, 5], factor: 0.96}, {indices: [0, 3, 7, 4], factor: 0.7},
    ];
    return definitions.map((definition) => {
      const points = definition.indices.map((index) => corners[index]);
      return {
        part: component.id,
        points,
        fill: shade(component.color, definition.factor),
        stroke: shade(component.color, 0.66),
        depth: points.reduce((sum, point) => sum + point.depth, 0) / points.length,
        overlay: component.id.startsWith('finish'),
      };
    });
  }).sort((a, b) => Number(a.overlay) - Number(b.overlay) || a.depth - b.depth);

  return <AbsoluteFill style={{background: BACKGROUND}}>
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}
      role="img" aria-label="两层框架住宅建造过程示意"
      data-m2v-building-frame={frame}>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f5f1e8" />
          <stop offset="1" stopColor="#e7e0d3" />
        </linearGradient>
      </defs>
      <rect width={width} height={height} fill="url(#sky)" />
      <ellipse cx={width / 2} cy={height * 0.9} rx={width * 0.38} ry={height * 0.09}
        fill="#d8d0c1" opacity={0.55} />
      {faces.map((face, index) => <polygon key={`${face.part}-${index}`}
        data-m2v-building-part={face.part} points={polygon(face.points)}
        fill={face.fill} stroke={face.stroke} strokeWidth={0.7}
        strokeLinejoin="round" />)}
      <g data-m2v-building-stage={stage?.id ?? ''}>
        <text x={42} y={height - 62} fill={INK} fontSize={20} fontWeight={600}
          opacity={0.62}>{stage?.label ?? ''}</text>
        <text x={width - 42} y={height - 42} textAnchor="end" fill="#6b6f6a" fontSize={16}>
          建造过程示意
        </text>
      </g>
    </svg>
  </AbsoluteFill>;
}
