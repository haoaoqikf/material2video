import {useLayoutEffect, useMemo} from 'react';
import {THREE, useThree} from 'm2v/code-scene';
import {
  cameraAt, finaleAt, pathUAt, smooth01, smoothstep, unlockAt, window01,
} from './lifeMath';

type V3 = [number, number, number];
type Props = {t: number};

const WHITE = '#f2f8fc';
const BLUE = '#8fd2f7';
const BLUE_DIM = '#3f7fa8';
const DARK_LINE = '#1b3547';
const VOID = '#02060a';

/* ------------------------------------------------------------------ */
/* 主路径与基础几何                                                     */
/* ------------------------------------------------------------------ */

const PATH_POINTS: V3[] = [
  [0, 0, 0], [8, 0, 0], [18, 0, 0], [32, 0, 2], [48, 0, 4],
  [58, 5, 4], [68, 13, 4], [78, 18, 4], [90, 24, 4], [108, 24, 4],
  [118, 27, 3], [128, 31, 2], [138, 34, 2], [150, 34, 2], [162, 34, 2],
  [175, 34, 2], [190, 34, 2],
];

const PATH = new THREE.CatmullRomCurve3(
  PATH_POINTS.map((point) => new THREE.Vector3(...point)), false, 'catmullrom', 0.18,
);

const TRAIL_GEO = new THREE.TubeGeometry(PATH, 900, 0.07, 5, false);
const TRAIL_GLOW_GEO = new THREE.TubeGeometry(PATH, 900, 0.24, 5, false);
const TRAIL_INDEX_COUNT = TRAIL_GEO.index ? TRAIL_GEO.index.count : 0;
const ROAD_GEO = new THREE.TubeGeometry(PATH, 900, 0.028, 4, false);
const ROAD_MAT = new THREE.MeshBasicMaterial({color: '#dff2ff', transparent: true, opacity: 0.38});

const GHOST = new THREE.CatmullRomCurve3([
  new THREE.Vector3(4, 0, 0), new THREE.Vector3(16, 0, -3),
  new THREE.Vector3(34, 0, -11), new THREE.Vector3(58, 0, -22),
  new THREE.Vector3(82, 0, -30),
], false, 'catmullrom', 0.2);
const GHOST_GEO = new THREE.TubeGeometry(GHOST, 260, 0.035, 4, false);

const TRAIL_MAT = new THREE.MeshBasicMaterial({color: WHITE, transparent: true, opacity: 0.95});
const TRAIL_GLOW_MAT = new THREE.MeshBasicMaterial({
  color: BLUE, transparent: true, opacity: 0.07, blending: THREE.AdditiveBlending, depthWrite: false,
});
const GHOST_MAT = new THREE.MeshBasicMaterial({color: BLUE_DIM, transparent: true, opacity: 0.2});

function sampleCurve(curve: THREE.Curve<THREE.Vector3>, count: number): THREE.Vector3[] {
  return Array.from({length: count}, (_, i) => curve.getPointAt(i / (count - 1)));
}

function tube(points: V3[] | THREE.Vector3[], radius: number, segments = 300): THREE.TubeGeometry {
  const curve = new THREE.CatmullRomCurve3(
    points.map((point) => point instanceof THREE.Vector3 ? point : new THREE.Vector3(...point)),
    false, 'catmullrom', 0.15,
  );
  return new THREE.TubeGeometry(curve, segments, radius, 4, false);
}

function lineGeometry(points: THREE.Vector3[]): THREE.BufferGeometry {
  const values = new Float32Array(points.length * 3);
  points.forEach((point, i) => {
    values[i * 3] = point.x;
    values[i * 3 + 1] = point.y;
    values[i * 3 + 2] = point.z;
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(values, 3));
  return geometry;
}

function pathPoint(u: number): THREE.Vector3 {
  return PATH.getPointAt(Math.max(0, Math.min(1, u)));
}

/* ------------------------------------------------------------------ */
/* 人物                                                                */
/* ------------------------------------------------------------------ */

function Figure({position, direction, phase = 0, scale = 1, opacity = 1}: {
  position: THREE.Vector3; direction?: THREE.Vector3; phase?: number; scale?: number; opacity?: number;
}) {
  const rotation = direction ? Math.atan2(direction.x, direction.z) : 0;
  const swing = Math.sin(phase * Math.PI * 2) * 0.22;
  const body = <meshBasicMaterial color={WHITE} transparent={opacity < 0.99} opacity={opacity}/>;
  return <group position={position.toArray()} rotation={[0, rotation, 0]} scale={scale}>
    <mesh position={[0, 1.42, 0]}><capsuleGeometry args={[0.19, 0.55, 4, 10]}/>{body}</mesh>
    <mesh position={[0, 1.05, 0]}><capsuleGeometry args={[0.16, 0.34, 4, 10]}/>{body}</mesh>
    <mesh position={[0, 1.9, 0]}><sphereGeometry args={[0.14, 12, 10]}/>{body}</mesh>
    <group rotation={[swing, 0, 0]}>
      <mesh position={[-0.1, 0.75, 0]}><capsuleGeometry args={[0.075, 0.5, 4, 8]}/>{body}</mesh>
      <mesh position={[-0.1, 0.2, 0.02]}><capsuleGeometry args={[0.07, 0.4, 4, 8]}/>{body}</mesh>
    </group>
    <group rotation={[-swing, 0, 0]}>
      <mesh position={[0.1, 0.75, 0]}><capsuleGeometry args={[0.075, 0.5, 4, 8]}/>{body}</mesh>
      <mesh position={[0.1, 0.2, 0.02]}><capsuleGeometry args={[0.07, 0.4, 4, 8]}/>{body}</mesh>
    </group>
    <mesh position={[-0.22, 1.45, 0]} rotation={[0, 0, -swing]}><capsuleGeometry args={[0.05, 0.4, 4, 8]}/>{body}</mesh>
    <mesh position={[0.22, 1.45, 0]} rotation={[0, 0, swing]}><capsuleGeometry args={[0.05, 0.4, 4, 8]}/>{body}</mesh>
    <mesh position={[-0.1, 0.04, 0.1]}><boxGeometry args={[0.14, 0.08, 0.28]}/>{body}</mesh>
    <mesh position={[0.1, 0.04, 0.1]}><boxGeometry args={[0.14, 0.08, 0.28]}/>{body}</mesh>
  </group>;
}

function FigureAtPath({t, offset = 0, lateral = 0, height = 0, scale = 1}: {
  t: number; offset?: number; lateral?: number; height?: number; scale?: number;
}) {
  const u = pathUAt(t);
  const position = pathPoint(u);
  const tangent = PATH.getTangentAt(u);
  const side = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
  position.addScaledVector(side, lateral);
  position.y += height;
  return <Figure position={position} direction={tangent} phase={u * 18} scale={scale}/>;
}

/* ------------------------------------------------------------------ */
/* 开场：分叉与未走的路                                                 */
/* ------------------------------------------------------------------ */

function Opening({t, figures = true}: Props & {figures?: boolean}) {
  const u = pathUAt(t);
  const ghost = window01(t, 0.5, 4.5);
  return <group>
    <mesh geometry={TRAIL_GLOW_GEO} material={TRAIL_GLOW_MAT}/>
    <mesh geometry={GHOST_GEO} material={GHOST_MAT} visible={ghost > 0.01}/>
    <mesh geometry={GHOST_GEO}>
      <meshBasicMaterial color={BLUE} transparent opacity={0.12} blending={THREE.AdditiveBlending} depthWrite={false}/>
    </mesh>
    {/* 岔口处极小的方向差：仅用一段短亮线提示选择发生。 */}
    <mesh position={[4, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[0.22, 0.3, 32]}/>
      <meshBasicMaterial color={BLUE} transparent opacity={0.5 * window01(t, 0.5, 2.5)}/>
    </mesh>
  </group>;
}

function TrailDraw({progress}: {progress: number}) {
  const geometry = TRAIL_GEO;
  useLayoutEffect(() => {
    geometry.setDrawRange(0, Math.max(1, Math.floor(TRAIL_INDEX_COUNT * progress)));
  }, [geometry, progress]);
  return <mesh geometry={geometry} material={TRAIL_MAT}/>;
}

/* ------------------------------------------------------------------ */
/* 城市：机会网络                                                       */
/* ------------------------------------------------------------------ */

type Network = {edges: THREE.BufferGeometry; nodes: THREE.BufferGeometry; order: number[]};

function makeNetwork(seed: number, x0: number, x1: number, z0: number, z1: number,
  cols: number, rows: number, connectChance: number, center: V3): Network {
  let state = seed >>> 0;
  const rand = () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
  const nodes: THREE.Vector3[] = [];
  for (let ix = 0; ix < cols; ix += 1) {
    for (let iz = 0; iz < rows; iz += 1) {
      const x = x0 + (x1 - x0) * (ix / Math.max(1, cols - 1)) + (rand() - 0.5) * 3.2;
      const z = z0 + (z1 - z0) * (iz / Math.max(1, rows - 1)) + (rand() - 0.5) * 3.2;
      nodes.push(new THREE.Vector3(x, 0.015, z));
    }
  }
  const pairs: [number, number][] = [];
  for (let ix = 0; ix < cols; ix += 1) {
    for (let iz = 0; iz < rows; iz += 1) {
      const index = ix * rows + iz;
      if (ix + 1 < cols && rand() < connectChance) pairs.push([index, (ix + 1) * rows + iz]);
      if (iz + 1 < rows && rand() < connectChance) pairs.push([index, ix * rows + (iz + 1)]);
      if (ix + 1 < cols && iz + 1 < rows && rand() < connectChance * 0.45) {
        pairs.push([index, (ix + 1) * rows + iz + 1]);
      }
    }
  }
  const centerPoint = new THREE.Vector3(...center);
  pairs.sort((a, b) => {
    const da = nodes[a[0]].distanceTo(centerPoint);
    const db = nodes[b[0]].distanceTo(centerPoint);
    return da - db;
  });
  const positions = new Float32Array(pairs.length * 6);
  pairs.forEach(([a, b], i) => {
    positions.set([nodes[a].x, nodes[a].y, nodes[a].z, nodes[b].x, nodes[b].y, nodes[b].z], i * 6);
  });
  const edgeGeometry = new THREE.BufferGeometry();
  edgeGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const nodePositions = new Float32Array(nodes.length * 3);
  nodes.forEach((node, i) => nodePositions.set([node.x, node.y + 0.03, node.z], i * 3));
  const nodeGeometry = new THREE.BufferGeometry();
  nodeGeometry.setAttribute('position', new THREE.BufferAttribute(nodePositions, 3));
  return {edges: edgeGeometry, nodes: nodeGeometry, order: pairs.map((_, i) => i)};
}

const DENSE = makeNetwork(7, 4, 54, -28, 28, 13, 10, 0.86, [28, 0, 2]);
const SPARSE = makeNetwork(19, 72, 100, -18, 18, 5, 4, 0.32, [86, 0, 0]);

function NetworkDraw({network, progress, color, nodeColor, opacity, reveal = 1}: {
  network: Network; progress: number; color: string; nodeColor: string; opacity: number; reveal?: number;
}) {
  const lineMat = useMemo(() => new THREE.LineBasicMaterial({
    color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false,
  }), [color, opacity]);
  const nodeMat = useMemo(() => new THREE.PointsMaterial({
    color: nodeColor, size: 0.48, sizeAttenuation: true, transparent: true,
    opacity: opacity * 0.8, depthWrite: false,
  }), [nodeColor, opacity]);
  useLayoutEffect(() => {
    const count = network.edges.getAttribute('position').count;
    network.edges.setDrawRange(0, Math.max(0, Math.floor(count * progress)));
    network.nodes.setDrawRange(0, Math.max(0, Math.floor(network.nodes.getAttribute('position').count * reveal)));
  }, [network, progress, reveal]);
  return <group>
    <lineSegments geometry={network.edges} material={lineMat}/>
    <points geometry={network.nodes} material={nodeMat}/>
  </group>;
}

function City({t, figures = true}: Props & {figures?: boolean}) {
  const p = window01(t, 6.0, 12.5);
  const residual = 1 - 0.55 * window01(t, 15, 18);
  const presence = 1 - 0.72 * window01(t, 24, 28);
  return <group>
    <NetworkDraw network={DENSE} progress={smooth01(p)} color="#d6ecfb" nodeColor={BLUE}
      opacity={0.92 * residual * presence}/>
    <NetworkDraw network={SPARSE} progress={window01(t, 5.5, 9)} color={BLUE_DIM} nodeColor={BLUE_DIM}
      opacity={0.3 * presence}/>
    <mesh position={pathPoint(pathUAt(t)).add(new THREE.Vector3(0, 0.04, 0)).toArray()}
      rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[0.75, 1.0, 40]}/>
      <meshBasicMaterial color={BLUE} transparent opacity={0.55 * presence}/>
    </mesh>
  </group>;
}

/* ------------------------------------------------------------------ */
/* 行业：移动地形                                                       */
/* ------------------------------------------------------------------ */

const RISE = new THREE.CatmullRomCurve3([
  new THREE.Vector3(48, 0, 4), new THREE.Vector3(56, 3, 4),
  new THREE.Vector3(64, 8, 4), new THREE.Vector3(72, 14, 4), new THREE.Vector3(78, 18, 4),
], false, 'catmullrom', 0.15);
const FLAT = new THREE.CatmullRomCurve3([
  new THREE.Vector3(48, 0, 8), new THREE.Vector3(78, 0, 8),
], false, 'catmullrom', 0.15);
const RISE_GEO = new THREE.TubeGeometry(RISE, 200, 0.09, 4, false);
const FLAT_GEO = new THREE.TubeGeometry(FLAT, 120, 0.045, 4, false);

function curtain(curve: THREE.Curve<THREE.Vector3>, baseY: number, segments = 80): THREE.BufferGeometry {
  const points = sampleCurve(curve, segments + 1);
  const values = new Float32Array(points.length * 2 * 3);
  points.forEach((point, i) => {
    values.set([point.x, point.y, point.z, point.x, baseY, point.z], i * 6);
  });
  const indices: number[] = [];
  for (let i = 0; i < segments; i += 1) {
    const a = i * 2;
    indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(values, 3));
  geometry.setIndex(indices);
  return geometry;
}
const RISE_CURTAIN = curtain(RISE, 0, 60);
const RISE_CONTOURS = (() => {
  const points = sampleCurve(RISE, 13);
  const segments: number[] = [];
  points.forEach((point) => segments.push(point.x, point.y, point.z, point.x, 0, point.z));
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(segments), 3));
  return geometry;
})();

function Industry({t, figures = true}: Props & {figures?: boolean}) {
  const show = window01(t, 16, 20);
  const presence = 1 - 0.72 * window01(t, 30, 34);
  const point = pathPoint(pathUAt(t));
  const flatPosition = new THREE.Vector3(point.x, 0, 8);
  return <group>
    <mesh geometry={RISE_GEO}>
      <meshBasicMaterial color={WHITE} transparent opacity={(0.1 + 0.85 * window01(t, 13, 18)) * presence}/>
    </mesh>
    <mesh geometry={RISE_CURTAIN}>
      <meshBasicMaterial color="#0a2233" transparent opacity={0.28 * show * presence} side={THREE.DoubleSide}
        depthWrite={false} blending={THREE.AdditiveBlending}/>
    </mesh>
    <lineSegments geometry={RISE_CONTOURS}>
      <lineBasicMaterial color={BLUE_DIM} transparent opacity={0.35 * show * presence} blending={THREE.AdditiveBlending}/>
    </lineSegments>
    <mesh geometry={FLAT_GEO}>
      <meshBasicMaterial color={WHITE} transparent opacity={(0.1 + 0.85 * window01(t, 13, 18)) * presence}/>
    </mesh>
    <Figure position={flatPosition} direction={RISE.getTangentAt(0.5)} phase={0.35} opacity={window01(t, 16, 18) * presence}/>
    <lineSegments geometry={lineGeometry([point, flatPosition])}>
      <lineBasicMaterial color={BLUE} transparent opacity={0.28 * window01(t, 19, 21) * presence} blending={THREE.AdditiveBlending}/>
    </lineSegments>
  </group>;
}

/* ------------------------------------------------------------------ */
/* 伴侣：双轨耦合                                                       */
/* ------------------------------------------------------------------ */

function helixCurve(start: V3, end: V3, radius: number, phase: number, turns = 1.1) {
  const a = new THREE.Vector3(...start);
  const b = new THREE.Vector3(...end);
  const points: THREE.Vector3[] = [];
  const steps = 48;
  for (let i = 0; i <= steps; i += 1) {
    const p = i / steps;
    const point = a.clone().lerp(b, p);
    const angle = phase + p * Math.PI * 2 * turns;
    point.x += Math.sin(angle) * radius;
    point.y += Math.cos(angle) * radius * 0.55;
    points.push(point);
  }
  return new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.1);
}

const PLUS_MAIN = new THREE.CatmullRomCurve3([
  new THREE.Vector3(78, 18, 0), new THREE.Vector3(88, 23, -1.2),
  new THREE.Vector3(98, 30, -0.4), new THREE.Vector3(108, 34, 0.6),
], false, 'catmullrom', 0.18);
const PLUS_PARTNER = new THREE.CatmullRomCurve3([
  new THREE.Vector3(78, 18, 2.2), new THREE.Vector3(88, 23, 1.0),
  new THREE.Vector3(98, 30, 1.8), new THREE.Vector3(108, 34, 2.8),
], false, 'catmullrom', 0.18);
const MINUS_A = new THREE.CatmullRomCurve3([
  new THREE.Vector3(104, 18, -14), new THREE.Vector3(112, 15, -12),
  new THREE.Vector3(120, 11, -8), new THREE.Vector3(126, 8, -6),
], false, 'catmullrom', 0.22);
const MINUS_B = new THREE.CatmullRomCurve3([
  new THREE.Vector3(104, 18, -16.5), new THREE.Vector3(112, 14, -20),
  new THREE.Vector3(120, 10, -24), new THREE.Vector3(126, 7, -26),
], false, 'catmullrom', 0.22);
const PLUS_GEO = new THREE.TubeGeometry(PLUS_MAIN, 200, 0.06, 4, false);
const PARTNER_GEO = new THREE.TubeGeometry(PLUS_PARTNER, 200, 0.06, 4, false);
const MINUS_A_GEO = new THREE.TubeGeometry(MINUS_A, 180, 0.04, 4, false);
const MINUS_B_GEO = new THREE.TubeGeometry(MINUS_B, 180, 0.04, 4, false);

/** 主线人物：伴侣段走上双轨，随后回到主路，避免章节切换时人物瞬移。 */
function mainFigureAt(t: number): {pos: THREE.Vector3; dir: THREE.Vector3} {
  if (t >= 27 && t <= 38) {
    const p = smooth01(window01(t, 27, 38));
  const presence = 1 - 0.72 * window01(t, 38, 42);
    return {pos: PLUS_MAIN.getPointAt(p), dir: PLUS_MAIN.getTangentAt(p)};
  }
  if (t > 38 && t < 41) {
    const a = PLUS_MAIN.getPointAt(1);
    const b = pathPoint(pathUAt(41));
    const s = smooth01((t - 38) / 3);
    return {pos: a.clone().lerp(b, s), dir: b.clone().sub(a).normalize()};
  }
  return {pos: pathPoint(pathUAt(t)), dir: PATH.getTangentAt(pathUAt(t))};
}

function Partner({t, figures = true}: Props & {figures?: boolean}) {
  const p = smooth01(window01(t, 27, 38));
  const presence = 1 - 0.72 * window01(t, 38, 42);
  const mainPoint = PLUS_MAIN.getPointAt(p);
  const partnerPoint = PLUS_PARTNER.getPointAt(Math.min(1, p + 0.035));
  const minusA = MINUS_A.getPointAt(p);
  const minusB = MINUS_B.getPointAt(p);
  const rungs: THREE.Vector3[] = [];
  for (let i = 1; i < 14; i += 1) {
    const u = i / 14;
    rungs.push(PLUS_MAIN.getPointAt(u), PLUS_PARTNER.getPointAt(u));
    rungs.push(MINUS_A.getPointAt(u), MINUS_B.getPointAt(u));
  }
  return <group>
    <mesh geometry={PLUS_GEO}>
      <meshBasicMaterial color={WHITE} transparent opacity={(0.1 + 0.85 * window01(t, 24, 28)) * presence}/>
    </mesh>
    <mesh geometry={PARTNER_GEO}>
      <meshBasicMaterial color={BLUE} transparent opacity={0.75 * window01(t, 27, 30) * presence}/>
    </mesh>
    <mesh geometry={MINUS_A_GEO}>
      <meshBasicMaterial color={BLUE_DIM} transparent opacity={0.4 * window01(t, 27, 30)}/>
    </mesh>
    <mesh geometry={MINUS_B_GEO}>
      <meshBasicMaterial color={BLUE_DIM} transparent opacity={0.4 * window01(t, 27, 30)}/>
    </mesh>
    <lineSegments geometry={lineGeometry(rungs)}>
      <lineBasicMaterial color={BLUE} transparent opacity={0.32 * p * presence} blending={THREE.AdditiveBlending}/>
    </lineSegments>
    <group>
      <Figure position={partnerPoint} direction={PLUS_PARTNER.getTangentAt(p)} phase={p * 7 + 0.5} scale={1.5} opacity={window01(t, 25, 28) * presence}/>
      <Figure position={minusA} direction={MINUS_A.getTangentAt(p)} phase={p * 7} opacity={0.75 * window01(t, 25, 28) * presence} scale={1.5}/>
      <Figure position={minusB} direction={MINUS_B.getTangentAt(p)} phase={p * 7 + 0.5} opacity={0.75 * window01(t, 25, 28) * presence} scale={1.5}/>
    </group>
  </group>;
}

/* ------------------------------------------------------------------ */
/* 投资：时间撑开的道路                                                 */
/* ------------------------------------------------------------------ */

function ribbonGeometry(curve: THREE.Curve<THREE.Vector3>, u0: number, u1: number,
  width0: number, width1: number, segments = 160): THREE.BufferGeometry {
  const values: number[] = [];
  const indices: number[] = [];
  for (let i = 0; i <= segments; i += 1) {
    const local = i / segments;
    const u = u0 + (u1 - u0) * local;
    const point = curve.getPointAt(u);
    const tangent = curve.getTangentAt(u);
    const side = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
    const width = width0 + (width1 - width0) * smooth01(local);
    const left = point.clone().addScaledVector(side, width / 2);
    const right = point.clone().addScaledVector(side, -width / 2);
    values.push(left.x, left.y, left.z, right.x, right.y, right.z);
    if (i < segments) {
      const a = i * 2;
      indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(values), 3));
  geometry.setIndex(indices);
  return geometry;
}

const INVEST_START = 0.6;
const INVEST_END = 0.78;
const GROWTH_GEO = ribbonGeometry(PATH, INVEST_START, INVEST_END, 0.16, 7.5, 180);
const THIN_GEO = tube([[108, 20, 9], [123, 20, 9], [138, 20, 9]], 0.05, 80);
const GROWTH_EDGES = (() => {
  const left: THREE.Vector3[] = [];
  const right: THREE.Vector3[] = [];
  for (let i = 0; i <= 180; i += 1) {
    const local = i / 180;
    const u = INVEST_START + (INVEST_END - INVEST_START) * local;
    const point = PATH.getPointAt(u);
    const tangent = PATH.getTangentAt(u);
    const side = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
    const width = 0.16 + 7.5 * smooth01(local);
    left.push(point.clone().addScaledVector(side, width / 2));
    right.push(point.clone().addScaledVector(side, -width / 2));
  }
  return [lineGeometry(left), lineGeometry(right)];
})();

const GROWTH_CONTOURS = (() => {
  const segments: number[] = [];
  for (let i = 0; i <= 12; i += 1) {
    const local = i / 12;
    const u = INVEST_START + (INVEST_END - INVEST_START) * local;
    const point = PATH.getPointAt(u);
    const tangent = PATH.getTangentAt(u);
    const side = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
    const width = 0.16 + 7.5 * smooth01(local);
    const edge = point.clone().addScaledVector(side, -width / 2);
    segments.push(edge.x, edge.y, edge.z, edge.x, 20, edge.z);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(segments), 3));
  return geometry;
})();

function Investment({t, figures = true}: Props & {figures?: boolean}) {
  const growth = window01(t, 38, 44);
  const presence = 1 - 0.72 * window01(t, 46, 50);
  const point = pathPoint(pathUAt(t));
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < 7; i += 1) {
    const u = INVEST_START + (INVEST_END - INVEST_START) * (0.12 + i * 0.11);
    points.push(PATH.getPointAt(u));
  }
  return <group>
    <mesh geometry={GROWTH_GEO}>
      <meshBasicMaterial color={BLUE} transparent opacity={(0.28 + 0.22 * growth) * window01(t, 34, 40) * presence} side={THREE.DoubleSide}
        depthWrite={false} blending={THREE.AdditiveBlending}/>
    </mesh>
    {GROWTH_EDGES.map((geometry, index) => <lineSegments key={index} geometry={geometry}>
      <lineBasicMaterial color={WHITE} transparent opacity={0.7 * growth * window01(t, 34, 40) * presence} blending={THREE.AdditiveBlending}/>
    </lineSegments>)}
    <lineSegments geometry={GROWTH_CONTOURS}>
      <lineBasicMaterial color={BLUE_DIM} transparent opacity={0.35 * growth * window01(t, 34, 40) * presence} blending={THREE.AdditiveBlending}/>
    </lineSegments>
    <mesh geometry={THIN_GEO}>
      <meshBasicMaterial color={WHITE} transparent opacity={0.72 * window01(t, 34, 40) * presence}/>
    </mesh>
    {figures && <FigureAtPath t={t}/>}
    {figures && <Figure position={new THREE.Vector3(132, 24, 9)} direction={new THREE.Vector3(1, 0, 0)} phase={0.4}/>}
    {points.map((point, i) => <mesh key={i} position={point.clone().add(new THREE.Vector3(0, 0.25, 0)).toArray()}>
      <sphereGeometry args={[0.06 + i * 0.035, 8, 6]}/>
      <meshBasicMaterial color={BLUE} transparent opacity={window01(t, 38.5 + i * 0.5, 40 + i * 0.5) * presence}/>
    </mesh>)}
  </group>;
}

/* ------------------------------------------------------------------ */
/* 学习：黑暗地图解锁                                                   */
/* ------------------------------------------------------------------ */

const MAP_CURVES = Array.from({length: 14}, (_, i) => {
  const angle = -0.9 + (i / 13) * 1.8;
  const length = 10 + (i % 4) * 4;
  const origin = new THREE.Vector3(160, 34, 2);
  const end = new THREE.Vector3(
    160 + Math.cos(angle) * length,
    34 + ((i % 4) - 1) * 4 + (i > 9 ? 6 : 0),
    2 + Math.sin(angle) * length,
  );
  return new THREE.CatmullRomCurve3([
    origin,
    origin.clone().lerp(end, 0.45).add(new THREE.Vector3(0, (i % 3) * 2.5, 0)),
    end,
  ], false, 'catmullrom', 0.2);
});
const MAP_GEOS = MAP_CURVES.map((curve) => new THREE.TubeGeometry(curve, 100, 0.035, 3, false));
const BRIDGE = new THREE.CatmullRomCurve3([
  new THREE.Vector3(150, 34, 2), new THREE.Vector3(155, 34.4, 2), new THREE.Vector3(160, 34, 2),
], false, 'catmullrom', 0.2);
const BRIDGE_GEO = new THREE.TubeGeometry(BRIDGE, 80, 0.055, 4, false);
const VERTICAL = new THREE.CatmullRomCurve3([
  new THREE.Vector3(162, 34, 2), new THREE.Vector3(164, 44, 5), new THREE.Vector3(166, 55, 2),
], false, 'catmullrom', 0.2);
const VERTICAL_GEO = new THREE.TubeGeometry(VERTICAL, 80, 0.045, 4, false);
const ARCH = (() => {
  const points: number[] = [];
  const y0 = 28; const y1 = 44; const z0 = -4; const z1 = 8;
  points.push(170, y0, z0, 170, y1, z0, 170, y1, z0, 170, y1, z1,
    170, y1, z1, 170, y0, z1);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(points), 3));
  return geometry;
})();
const CLIFF_ROAD = new THREE.TubeGeometry(PATH, 900, 0.07, 4, false);

function Learning({t, figures = true}: Props & {figures?: boolean}) {
  const figureU = Math.min(pathUAt(t), 0.79);
  const position = pathPoint(figureU);
  return <group>
    <mesh geometry={BRIDGE_GEO}>
      <meshBasicMaterial color={WHITE} transparent opacity={unlockAt(t, 0) * 0.9 * window01(t, 47, 50)}/>
    </mesh>
    {MAP_GEOS.map((geometry, i) => {
      const lit = unlockAt(t, Math.min(3, Math.floor(i / 4)));
      return <mesh key={i} geometry={geometry}>
        <meshBasicMaterial color={lit > 0.2 ? BLUE : DARK_LINE} transparent
          opacity={(0.1 + lit * 0.55) * window01(t, 46, 50)} blending={THREE.AdditiveBlending} depthWrite={false}/>
      </mesh>;
    })}
    <mesh geometry={VERTICAL_GEO}>
      <meshBasicMaterial color={WHITE} transparent opacity={unlockAt(t, 3) * 0.7 * window01(t, 47, 50)}/>
    </mesh>
    <lineSegments geometry={lineGeometry([
      new THREE.Vector3(148, 34, -1), new THREE.Vector3(148, 27, -1),
      new THREE.Vector3(148, 34, 1), new THREE.Vector3(148, 26, 1),
      new THREE.Vector3(148, 34, 3), new THREE.Vector3(148, 28, 3),
    ])}>
      <lineBasicMaterial color={BLUE_DIM} transparent opacity={0.4}/>
    </lineSegments>
    <lineSegments geometry={ARCH}>
      <lineBasicMaterial color={BLUE} transparent opacity={unlockAt(t, 2) * 0.55} blending={THREE.AdditiveBlending}/>
    </lineSegments>
    <mesh position={[148, 34, 2]} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[1.2, 1.5, 48]}/>
      <meshBasicMaterial color={BLUE} transparent opacity={0.2 + unlockAt(t, 0) * 0.3}/>
    </mesh>
  </group>;
}

/* ------------------------------------------------------------------ */
/* 终幕：所有轨迹构成一张人生地图                                       */
/* ------------------------------------------------------------------ */

const FAN_ORIGIN = new THREE.Vector3(4, 0, 0);
const FAN_ENDS: THREE.Vector3[] = [];
const FAN_CURVES: THREE.CatmullRomCurve3[] = [];
for (let i = 0; i < 32; i += 1) {
  const angle = -1.15 + (i / 31) * 2.3;
  const end = new THREE.Vector3(
    4 + Math.cos(angle) * 120,
    8 + (i % 5) * 4,
    Math.sin(angle) * 100,
  );
  FAN_ENDS.push(end);
  FAN_CURVES.push(new THREE.CatmullRomCurve3([
    FAN_ORIGIN.clone(),
    new THREE.Vector3(4 + Math.cos(angle) * 35, 3 + (i % 3), Math.sin(angle) * 30),
    new THREE.Vector3(4 + Math.cos(angle) * 78, 6 + (i % 4), Math.sin(angle) * 64),
    end,
  ], false, 'catmullrom', 0.2));
}
const FAN_GEOS = FAN_CURVES.map((curve, i) =>
  new THREE.TubeGeometry(curve, 50, i === 16 ? 0.09 : 0.04, 4, false));
const FAN_ARCS = [24, 48, 72, 96, 120].map((radius) => {
  const points: THREE.Vector3[] = [];
  for (let i = 0; i <= 60; i += 1) {
    const angle = -1.15 + (i / 60) * 2.3;
    points.push(new THREE.Vector3(4 + Math.cos(angle) * radius * 1.1, 2.5,
      Math.sin(angle) * radius * 0.92));
  }
  return lineGeometry(points);
});
const FAN_LEVEL_POINTS = [24, 48, 72, 96, 120].map((radius) => {
  const angle = FAN_CURVES[16].getPointAt(1).z >= 0 ? 0 : 0;
  return new THREE.Vector3(4 + Math.cos(angle) * radius * 1.1, 2.6, Math.sin(angle) * radius * 0.92);
});

function FullTrail() {
  useLayoutEffect(() => {
    TRAIL_GEO.setDrawRange(0, TRAIL_INDEX_COUNT);
    TRAIL_GEO.computeBoundingSphere();
  }, []);
  return <mesh geometry={TRAIL_GEO} material={TRAIL_MAT}/>;
}

const ORIGIN_RAYS = (() => {
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < 14; i += 1) {
    const angle = -1.1 + (i / 13) * 2.2;
    const length = 30 + (i % 4) * 12;
    points.push(new THREE.Vector3(4, 0.3, 0));
    points.push(new THREE.Vector3(4 + Math.cos(angle) * length, 4 + (i % 3) * 6,
      Math.sin(angle) * length * 0.55));
  }
  return lineGeometry(points);
})();

function Finale({t}: Props) {
  const reveal = window01(t, 57.5, 62.5);
  return <group>
    {FAN_GEOS.map((geometry, i) => <mesh key={i} geometry={geometry}>
      <meshBasicMaterial color={i === 16 ? WHITE : BLUE} transparent
        opacity={i === 16 ? (0.35 + 0.65 * reveal) : (0.3 + 0.55 * reveal)} blending={THREE.AdditiveBlending} depthWrite={false}/>
    </mesh>)}
    {FAN_ARCS.map((geometry, i) => <lineSegments key={`arc-${i}`} geometry={geometry}>
      <lineBasicMaterial color={i === 4 ? WHITE : BLUE_DIM} transparent opacity={(0.2 + 0.35 * reveal)}
        blending={THREE.AdditiveBlending}/>
    </lineSegments>)}
    {FAN_LEVEL_POINTS.map((point, i) => <mesh key={`level-${i}`} position={point.toArray()}>
      <sphereGeometry args={[0.9, 10, 8]}/>
      <meshBasicMaterial color={WHITE} transparent opacity={(0.3 + 0.6 * reveal)}/>
    </mesh>)}
    {FAN_ENDS.map((point, i) => <mesh key={`end-${i}`} position={point.toArray()}>
      <sphereGeometry args={[0.45, 8, 6]}/>
      <meshBasicMaterial color={i === 16 ? WHITE : BLUE} transparent
        opacity={i === 16 ? (0.4 + 0.55 * reveal) : (0.3 + 0.4 * reveal)}/>
    </mesh>)}
    <Figure position={FAN_ORIGIN} direction={new THREE.Vector3(1, 0, 0)} scale={2.6}/>
    <Figure position={FAN_ENDS[16]} direction={new THREE.Vector3(1, 0, 0)} scale={2.6}/>
  </group>;
}

/* ------------------------------------------------------------------ */
/* 相机与总装                                                           */
/* ------------------------------------------------------------------ */

function CameraRig({t}: Props) {
  const {camera} = useThree();
  useLayoutEffect(() => {
    const {pos, look, fov} = cameraAt(t);
    camera.position.set(pos[0], pos[1], pos[2]);
    camera.lookAt(look[0], look[1], look[2]);
    if (camera instanceof THREE.PerspectiveCamera) {
      camera.fov = fov;
      camera.updateProjectionMatrix();
    }
  }, [camera, t]);
  return null;
}

export default function LifeWorld({t}: Props) {
  const chapter = t < 6 ? 'opening'
    : t < 16 ? 'city'
      : t < 27 ? 'industry'
        : t < 38 ? 'partner'
          : t < 48 ? 'investment'
            : t < 57 ? 'learning' : 'finale';
  const reveal = finaleAt(t);
  const main = mainFigureAt(t);
  return <>
    <color attach="background" args={[VOID]}/>
    <fog attach="fog" args={[VOID, 120, 620]}/>
    <ambientLight intensity={0.65}/>
    <hemisphereLight args={['#9fc7df', '#02060a', 0.35]}/>
    <directionalLight position={[40, 80, 60]} intensity={1.1} color="#eaf6ff"/>
    <CameraRig t={t}/>
    {t < 57.5 && <mesh geometry={ROAD_GEO} material={ROAD_MAT}/>}
    {t < 57.5 && <Opening t={t} figures={false}/>}
    {t < 57.5 && <City t={t} figures={false}/>}
    {t < 57.5 && <Industry t={t} figures={false}/>}
    {t < 57.5 && <Partner t={t} figures={false}/>}
    {t < 57.5 && <Investment t={t} figures={false}/>}
    {t < 57.5 && <Learning t={t} figures={false}/>}
    {t < 57.5 && <Figure position={main.pos} direction={main.dir} phase={t * 1.6}/>}
    {t < 57.5 && <TrailDraw progress={pathUAt(t)}/>}
    {t >= 57.5 && <Finale t={t}/>}
  </>;
}
