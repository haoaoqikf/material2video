/**
 * 两层框架住宅的确定性构件图、动作与镜头求值。
 *
 * 本模块不依赖 WebGL 与 React，只由材料与帧号求值；单元测试用同一份规则
 * 断言构件 ID、洞口数量与关键包围盒。Python 校验器在 `components.py` 维护
 * 同一套 ID 规则，prepare 时会把身份清单放进 props 供运行时核对。
 */

export type Vec3 = [number, number, number];
export type Action =
  | 'excavate' | 'pour' | 'grow' | 'slide' | 'lift' | 'rotate' | 'insert' | 'spread';
export type MaterialKey =
  | 'site' | 'soil' | 'foundation' | 'concrete' | 'concrete-dark'
  | 'wall' | 'wood' | 'glass' | 'roof' | 'yard' | 'ink';

export type Opening = {
  id: string;
  floor: number;
  side: WallSide;
  offset: number;
  width: number;
  height: number;
  sill: number;
};

export type WallSide = 'front' | 'back' | 'left' | 'right';

export type House = {
  width: number;
  depth: number;
  floors: number;
  floorHeight: number;
  bayCount: number;
  roof: {type: 'gable' | 'flat'; height: number; overhang: number};
  wallThickness: number;
  foundationDepth: number;
  sitePadding: number;
  stairs: {side: WallSide; offset: number; width: number};
  openings: Opening[];
};

export type Stage = {id: string; label: string; startSeconds: number; endSeconds: number};
export type CameraSpec = {position: Vec3; target: Vec3; fov: number};
export type Shot = {
  id: string;
  startSeconds: number;
  endSeconds: number;
  camera: CameraSpec;
  to?: CameraSpec;
  hide: string[];
};
export type Step = {
  id: string;
  stage: string;
  select: string[];
  action: Action;
  label?: string;
  startSeconds: number;
  endSeconds: number;
  after: string[];
};

export type Component = {id: string; kind: string; floor: number};

export type Hole = {u: number; v: number; width: number; height: number};

export type BoxSpec = {
  center: Vec3;
  size: Vec3;
  rotation: Vec3;
  material: MaterialKey;
  holes?: Hole[];
  triangular?: boolean;
  frame?: {innerWidth: number; innerDepth: number};
  border?: number;
  slabHole?: {x: number; z: number; width: number; depth: number};
};

export type Transform = {
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
  opacity: number;
};

const SIDES: WallSide[] = ['front', 'back', 'left', 'right'];
const SIDE_SIGN: Record<WallSide, [number, number]> = {
  front: [0, 1], back: [0, -1], left: [-1, 0], right: [1, 0],
};

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function smooth(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

export function buildComponents(house: House): Component[] {
  const components: Component[] = [];
  const add = (id: string, kind: string, floor = 0) => {
    if (components.some((item) => item.id === id)) throw new Error(`构件 ID 重复：${id}`);
    components.push({id, kind, floor});
  };
  add('site', 'site');
  add('excavation', 'excavation');
  add('foundation-slab', 'foundation');
  for (const side of SIDES) add(`foundation-ring-${side}`, 'foundation');
  for (let floor = 1; floor <= house.floors; floor += 1) {
    add(`slab-${floor}`, 'slab', floor);
    for (let bay = 0; bay <= house.bayCount; bay += 1) {
      for (const side of ['front', 'back'] as const) {
        add(`column-${floor}-${bay}-${side}`, 'column', floor);
      }
    }
    for (const side of ['front', 'back'] as const) {
      for (let bay = 0; bay < house.bayCount; bay += 1) {
        add(`beam-${floor}-${side}-${bay}`, 'beam', floor);
      }
    }
    for (const side of ['left', 'right'] as const) {
      add(`beam-${floor}-${side}`, 'beam', floor);
    }
    for (const side of SIDES) add(`wall-${floor}-${side}-0`, 'wall', floor);
    if (floor < house.floors) {
      add(`stairwell-${floor}`, 'stair', floor);
      for (let step = 0; step < 10; step += 1) add(`stair-${floor}-${step}`, 'stair', floor);
    }
  }
  add(`stairwell-${house.floors}`, 'stair', house.floors);
  if (house.roof.type === 'gable') {
    for (const panel of ['left', 'right']) add(`roof-${panel}`, 'roof', house.floors);
    add('roof-ridge', 'roof', house.floors);
    add('roof-gable-front', 'roof', house.floors);
    add('roof-gable-back', 'roof', house.floors);
  } else {
    add('roof-slab', 'roof', house.floors);
    for (const side of SIDES) add(`parapet-${side}`, 'roof', house.floors);
  }
  for (const opening of house.openings) {
    add(`opening-${opening.id}`, 'opening', opening.floor);
    add(`finish-${opening.id}`, 'finish', opening.floor);
  }
  add('yard-path', 'yard');
  add('yard-steps', 'yard');
  add('yard-hedge', 'yard');
  return components;
}

export function expandSelector(components: Component[], selector: string): string[] {
  if (selector.slice(0, -1).includes('*') || (selector.match(/\*/g) ?? []).length > 1) {
    throw new Error(`选择器只支持末尾一个 *：${selector}`);
  }
  if (selector.endsWith('*')) {
    const prefix = selector.slice(0, -1);
    return components.filter((item) => item.id.startsWith(prefix)).map((item) => item.id);
  }
  return components.filter((item) => item.id === selector).map((item) => item.id);
}

export function ownerMap(components: Component[], steps: Step[]): Map<string, Step> {
  const owners = new Map<string, Step>();
  for (const step of steps) {
    for (const selector of step.select) {
      const found = expandSelector(components, selector);
      if (found.length === 0) throw new Error(`选择器没有匹配任何构件：${selector}`);
      for (const id of found) {
        if (owners.has(id)) throw new Error(`构件被重复建成：${id}`);
        owners.set(id, step);
      }
    }
  }
  return owners;
}

export function hiddenSet(components: Component[], shot: Shot): Set<string> {
  const hidden = new Set<string>();
  for (const selector of shot.hide) {
    const found = expandSelector(components, selector);
    if (found.length === 0) throw new Error(`隐藏选择器没有匹配任何构件：${selector}`);
    found.forEach((id) => hidden.add(id));
  }
  return hidden;
}

function openingHoles(house: House, floor: number, side: WallSide): Hole[] {
  const floorBase = (floor - 1) * house.floorHeight + 0.22;
  const wallLength = side === 'front' || side === 'back' ? house.width : house.depth;
  return house.openings
    .filter((opening) => opening.floor === floor && opening.side === side)
    .map((opening) => ({
      u: -wallLength / 2 + opening.offset + opening.width / 2,
      v: floorBase + opening.sill + opening.height / 2 - (floorBase + (house.floorHeight - 0.22) / 2),
      width: opening.width,
      height: opening.height,
    }));
}

function wallBox(house: House, floor: number, side: WallSide): BoxSpec {
  const halfW = house.width / 2;
  const halfD = house.depth / 2;
  const t = house.wallThickness;
  const base = (floor - 1) * house.floorHeight + 0.22;
  const height = house.floorHeight - 0.22;
  const centerY = base + height / 2;
  if (side === 'front' || side === 'back') {
    const z = (side === 'front' ? halfD : -halfD) + (side === 'front' ? -t / 2 : t / 2);
    return {
      center: [0, centerY, z], size: [house.width, height, t], rotation: [0, 0, 0],
      material: 'wall', holes: openingHoles(house, floor, side),
    };
  }
  const x = (side === 'right' ? halfW : -halfW) + (side === 'right' ? -t / 2 : t / 2);
  return {
    center: [x, centerY, 0], size: [house.depth, height, t], rotation: [0, -Math.PI / 2, 0],
    material: 'wall', holes: openingHoles(house, floor, side),
  };
}

export function componentBox(house: House, component: Component): BoxSpec {
  const halfW = house.width / 2;
  const halfD = house.depth / 2;
  const t = house.wallThickness;
  const roofBase = house.floors * house.floorHeight;
  const id = component.id;
  if (id === 'site') {
    return {
      center: [0, -0.15, 0],
      size: [house.width + house.sitePadding * 2, 0.3, house.depth + house.sitePadding * 2],
      rotation: [0, 0, 0], material: 'site',
      frame: {innerWidth: house.width + 1.2, innerDepth: house.depth + 1.2},
    };
  }
  if (id === 'excavation') {
    return {
      center: [0, -house.foundationDepth / 2 - 0.02, 0],
      size: [house.width + 1.8, house.foundationDepth, house.depth + 1.8],
      rotation: [0, 0, 0], material: 'soil',
    };
  }
  if (id === 'foundation-slab') {
    return {
      center: [0, -house.foundationDepth * 0.6 / 2 + 0.05, 0],
      size: [house.width + 1.4, house.foundationDepth * 0.6, house.depth + 1.4],
      rotation: [0, 0, 0], material: 'foundation',
    };
  }
  if (id.startsWith('foundation-ring-')) {
    const side = id.replace('foundation-ring-', '') as WallSide;
    const [sx, sz] = SIDE_SIGN[side];
    const length = sx === 0 ? house.width : house.depth;
    return {
      center: [sx * (halfW - t / 2), 0.275, sz * (halfD - t / 2)],
      size: sx === 0 ? [length, 0.45, t] : [t, 0.45, length],
      rotation: [0, 0, 0], material: 'foundation',
    };
  }
  if (id.startsWith('slab-')) {
    const floor = Number(id.split('-')[1]);
    const hole = floor >= 2 ? {
      x: halfW - 1.2, z: 0, width: house.stairs.width + 0.5, depth: house.depth - 2.4,
    } : undefined;
    return {
      center: [0, (floor - 1) * house.floorHeight + 0.11, 0],
      size: [house.width, 0.22, house.depth], rotation: [0, 0, 0], material: 'concrete',
      slabHole: hole,
    };
  }
  if (id.startsWith('column-')) {
    const [, floorText, bayText, side] = id.split('-');
    const floor = Number(floorText);
    const bay = Number(bayText);
    const base = (floor - 1) * house.floorHeight + 0.22;
    const height = house.floorHeight - 0.22;
    const span = house.width - 0.9;
    const x = -halfW + 0.45 + (span * bay) / house.bayCount;
    const z = side === 'front' ? halfD - 0.42 : -halfD + 0.42;
    return {
      center: [x, base + height / 2, z],
      size: [0.32, height, 0.32], rotation: [0, 0, 0], material: 'concrete-dark',
    };
  }
  if (id.startsWith('beam-')) {
    const [, floorText, side, bayText] = id.split('-');
    const floor = Number(floorText);
    const top = floor * house.floorHeight;
    if (side === 'left' || side === 'right') {
      const x = (side === 'right' ? 1 : -1) * (halfW - 0.42);
      return {
        center: [x, top - 0.175, 0],
        size: [0.32, 0.35, house.depth - 0.9], rotation: [0, 0, 0],
        material: 'concrete-dark',
      };
    }
    const bay = Number(bayText);
    const width = (house.width - 0.9) / house.bayCount;
    const x = -halfW + 0.45 + width * (bay + 0.5);
    const z = side === 'front' ? halfD - 0.42 : -halfD + 0.42;
    return {
      center: [x, top - 0.175, z],
      size: [width, 0.35, 0.32], rotation: [0, 0, 0], material: 'concrete-dark',
    };
  }
  if (id.startsWith('wall-')) {
    const [, floorText, side] = id.split('-');
    return wallBox(house, Number(floorText), side as WallSide);
  }
  if (id.startsWith('stairwell-')) {
    const floor = Number(id.split('-')[1]);
    const x = halfW - 1.2;
    const top = floor === house.floors;
    return {
      center: [x, floor * house.floorHeight + (top ? 0.01 : 0.11),
        top ? 0 : halfD - 1.5],
      size: top ? [0.9, 0.04, 0.9] : [house.stairs.width, 0.22, 0.9],
      rotation: [0, 0, 0], material: top ? 'ink' : 'wood',
    };
  }
  if (id.startsWith('stair-')) {
    const [, floorText, stepText] = id.split('-');
    const floor = Number(floorText);
    const step = Number(stepText);
    const base = (floor - 1) * house.floorHeight + 0.22;
    const stepHeight = (house.floorHeight - 0.22) / 10;
    const run = (house.depth - 2.4) / 10;
    const x = halfW - 1.2;
    const zStart = -halfD + 1.2;
    return {
      center: [x, base + stepHeight * (step + 0.5), zStart + run * (step + 0.5)],
      size: [house.stairs.width, stepHeight, run], rotation: [0, 0, 0], material: 'wood',
    };
  }
  if (id === 'roof-ridge') {
    return {
      center: [0, roofBase + house.roof.height, 0],
      size: [0.4, 0.2, house.depth + house.roof.overhang * 2],
      rotation: [0, 0, 0], material: 'roof',
    };
  }
  if (id.startsWith('roof-gable-')) {
    const z = id.endsWith('front') ? halfD + house.roof.overhang : -halfD - house.roof.overhang;
    return {
      center: [0, roofBase + house.roof.height / 2, z],
      size: [house.width, house.roof.height, 0.14],
      rotation: [0, 0, 0], material: 'wall', triangular: true,
    };
  }
  if (id === 'roof-left' || id === 'roof-right') {
    const reach = halfW + house.roof.overhang;
    const angle = Math.atan2(house.roof.height, reach);
    const length = Math.hypot(reach, house.roof.height);
    const sign = id === 'roof-left' ? -1 : 1;
    return {
      center: [sign * reach / 2, roofBase + house.roof.height / 2, 0],
      size: [length, 0.16, house.depth + house.roof.overhang * 2],
      rotation: [0, 0, sign * -angle], material: 'roof',
    };
  }
  if (id === 'roof-slab') {
    return {
      center: [0, roofBase + 0.15, 0],
      size: [house.width + house.roof.overhang * 2, 0.3, house.depth + house.roof.overhang * 2],
      rotation: [0, 0, 0], material: 'roof',
    };
  }
  if (id.startsWith('parapet-')) {
    const side = id.replace('parapet-', '') as WallSide;
    const [sx, sz] = SIDE_SIGN[side];
    const length = sx === 0 ? house.width + house.roof.overhang * 2 : house.depth + house.roof.overhang * 2;
    return {
      center: [sx * (halfW + house.roof.overhang - 0.12), roofBase + house.roof.height / 2,
        sz * (halfD + house.roof.overhang - 0.12)],
      size: sx === 0 ? [length, house.roof.height, 0.24] : [0.24, house.roof.height, length],
      rotation: [0, 0, 0], material: 'roof',
    };
  }
  if (id.startsWith('opening-')) {
    const openingId = id.slice('opening-'.length);
    const opening = house.openings.find((item) => item.id === openingId);
    if (!opening) throw new Error(`未知洞口：${openingId}`);
    const base = (opening.floor - 1) * house.floorHeight + 0.22;
    const along = opening.side === 'front' || opening.side === 'back' ? house.width : house.depth;
    const u = -along / 2 + opening.offset + opening.width / 2;
    const [sx, sz] = SIDE_SIGN[opening.side];
    const x = sx === 0 ? u : sx * (halfW - t / 2);
    const z = sz === 0 ? u : sz * (halfD - t / 2);
    return {
      center: [x, base + opening.sill + opening.height / 2, z],
      size: [opening.width + 0.16, opening.height + 0.16, 0.12],
      rotation: [0, sx === 0 ? 0 : -Math.PI / 2, 0], material: 'wood',
      border: 0.12,
    };
  }
  if (id.startsWith('finish-')) {
    const openingId = id.slice('finish-'.length);
    const opening = house.openings.find((item) => item.id === openingId);
    if (!opening) throw new Error(`未知门窗：${openingId}`);
    const base = (opening.floor - 1) * house.floorHeight + 0.22;
    const along = opening.side === 'front' || opening.side === 'back' ? house.width : house.depth;
    const u = -along / 2 + opening.offset + opening.width / 2;
    const [sx, sz] = SIDE_SIGN[opening.side];
    const inset = sx === 0 ? sz * 0.03 : sx * 0.03;
    return {
      center: [sx === 0 ? u : sx * (halfW - t / 2) + inset,
        base + opening.sill + opening.height / 2,
        sz === 0 ? u : sz * (halfD - t / 2) + inset],
      size: [opening.width * 0.92, opening.height * 0.92, 0.05],
      rotation: [0, sx === 0 ? 0 : -Math.PI / 2, 0],
      material: openingId.startsWith('door') ? 'wood' : 'glass',
    };
  }
  if (id === 'yard-path') {
    const door = house.openings.find((item) => item.id.startsWith('door'));
    const x = door && (door.side === 'front' || door.side === 'back')
      ? -halfW + door.offset + door.width / 2 : 0;
    const length = house.sitePadding;
    return {
      center: [x, 0.03, halfD + length / 2],
      size: [1.6, 0.06, length], rotation: [0, 0, 0], material: 'yard',
    };
  }
  if (id === 'yard-hedge') {
    return {
      center: [-halfW - 0.3, 0.35, halfD + house.sitePadding - 0.4],
      size: [house.width * 0.35, 0.7, 0.5], rotation: [0, 0, 0], material: 'yard',
    };
  }
  if (id === 'yard-steps') {
    const door = house.openings.find((item) => item.id.startsWith('door'));
    const x = door && (door.side === 'front' || door.side === 'back')
      ? -halfW + door.offset + door.width / 2 : 0;
    return {
      center: [x, 0.09, halfD + 0.6],
      size: [2.2, 0.18, 1.2], rotation: [0, 0, 0], material: 'concrete',
    };
  }
  throw new Error(`未知构件：${id}`);
}

export function transformFor(house: House, component: Component, step: Step | undefined,
                             seconds: number): Transform {
  const box = componentBox(house, component);
  const position: Vec3 = [...box.center];
  const rotation: Vec3 = [...box.rotation];
  const scale: Vec3 = [1, 1, 1];
  let opacity = 1;
  if (!step) return {position, rotation, scale, opacity};
  const p = smooth((seconds - step.startSeconds)
    / Math.max(0.001, step.endSeconds - step.startSeconds));
  switch (step.action) {
    case 'excavate':
      scale[1] = Math.max(0.001, p);
      position[1] = -box.size[1] * p / 2;
      break;
    case 'pour':
    case 'grow':
      scale[1] = Math.max(0.001, p);
      position[1] = box.center[1] - box.size[1] / 2 + box.size[1] * p / 2;
      break;
    case 'slide':
      position[2] = box.center[2] + 0.15 * (1 - p);
      break;
    case 'lift':
      position[1] = box.center[1] + 6 * (1 - p);
      break;
    case 'rotate':
      if (box.rotation[2] !== 0) {
        rotation[2] = box.rotation[2] + (box.rotation[2] >= 0 ? 0.1 : -0.1) * (1 - p);
      } else {
        position[1] = box.center[1] + 0.1 * (1 - p);
      }
      break;
    case 'insert':
      scale[0] = 0.85 + 0.15 * p;
      scale[1] = 0.85 + 0.15 * p;
      scale[2] = 0.85 + 0.15 * p;
      opacity = p;
      break;
    case 'spread':
      scale[2] = Math.max(0.001, p);
      position[2] = box.center[2] - box.size[2] / 2 + box.size[2] * p / 2;
      break;
  }
  return {position, rotation, scale, opacity};
}

export function shotAt(shots: Shot[], seconds: number): Shot {
  return shots.find((shot) => seconds >= shot.startSeconds && seconds < shot.endSeconds)
    ?? shots[shots.length - 1];
}

export function cameraAt(shot: Shot, seconds: number): CameraSpec {
  const to = shot.to ?? shot.camera;
  const t = smooth((seconds - shot.startSeconds)
    / Math.max(0.001, shot.endSeconds - shot.startSeconds));
  const lerp = (a: Vec3, b: Vec3): Vec3 => [
    a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t,
  ];
  return {
    position: lerp(shot.camera.position, to.position),
    target: lerp(shot.camera.target, to.target),
    fov: shot.camera.fov + (to.fov - shot.camera.fov) * t,
  };
}

export function currentStep(steps: Step[], seconds: number): Step {
  const active = steps.filter((step) => seconds >= step.startSeconds && seconds < step.endSeconds);
  if (active.length > 0) return active[active.length - 1];
  const past = steps.filter((step) => step.startSeconds <= seconds);
  return past.length > 0 ? past[past.length - 1] : steps[0];
}

export function stepIds(step: Step, components: Component[]): string[] {
  return step.select.flatMap((selector) => expandSelector(components, selector));
}

export function wallHoleCount(house: House, floor: number, side: WallSide): number {
  return openingHoles(house, floor, side).length;
}

/** 供测试断言的最终包围盒（中心与尺寸，世界坐标）。 */
export function boxBounds(house: House, component: Component): {center: Vec3; size: Vec3} {
  const box = componentBox(house, component);
  return {center: box.center, size: box.size};
}
