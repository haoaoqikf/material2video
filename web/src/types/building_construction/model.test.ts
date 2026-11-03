import {describe, expect, it} from 'vitest';
import {
  boxBounds, buildComponents, currentStep, expandSelector, ownerMap, transformFor, wallHoleCount,
  type House, type Step,
} from './model';

const house: House = {
  width: 12, depth: 9, floors: 2, floorHeight: 3, bayCount: 3,
  roof: {type: 'gable', height: 2.2, overhang: 0.6},
  wallThickness: 0.25, foundationDepth: 1.2, sitePadding: 3,
  stairs: {side: 'right', offset: 1.0, width: 1.4},
  openings: [
    {id: 'door-entry', floor: 1, side: 'front', offset: 5.1, width: 1.4, height: 2.3, sill: 0},
    {id: 'window-front-1', floor: 1, side: 'front', offset: 2.2, width: 1.6, height: 1.4, sill: 0.9},
    {id: 'window-front-2', floor: 2, side: 'front', offset: 5.1, width: 1.8, height: 1.4, sill: 0.9},
    {id: 'window-left-1', floor: 1, side: 'left', offset: 3.0, width: 1.4, height: 1.2, sill: 0.9},
  ],
};

const steps: Step[] = [
  {id: 'excavate', stage: 'site', select: ['excavation'], action: 'excavate',
    startSeconds: 1, endSeconds: 6, after: []},
  {id: 'columns-1', stage: 'frame-1', select: ['column-1-*'], action: 'grow',
    startSeconds: 20, endSeconds: 24, after: []},
  {id: 'insert-door', stage: 'finishes', select: ['opening-door-entry'], action: 'insert',
    startSeconds: 50, endSeconds: 53, after: []},
];

function component(id: string) {
  const found = buildComponents(house).find((item) => item.id === id);
  if (!found) throw new Error(`missing ${id}`);
  return found;
}

describe('确定性构件图', () => {
  it('生成固定、唯一的 72 个构件', () => {
    const components = buildComponents(house);
    const ids = components.map((item) => item.id);
    expect(ids.length).toBe(77);
    expect(new Set(ids).size).toBe(77);
    expect(ids.slice(0, 6)).toEqual([
      'site', 'excavation', 'foundation-slab',
      'foundation-ring-front', 'foundation-ring-back', 'foundation-ring-left',
    ]);
    expect(ids).toContain('column-2-3-back');
    expect(ids).toContain('wall-2-front-0');
    expect(ids).toContain('roof-gable-back');
    expect(ids).toContain('finish-window-left-1');
    expect(buildComponents(house)).toEqual(components);
  });

  it('展开末尾 glob 并拒绝中间星号', () => {
    const components = buildComponents(house);
    expect(expandSelector(components, 'column-1-*')).toHaveLength(8);
    expect(expandSelector(components, 'roof-*')).toHaveLength(5);
    expect(() => expandSelector(components, 'column-*-front')).toThrow('末尾');
  });

  it('每个非初始构件只被建成一次', () => {
    const full: Step[] = [
      {id: 'all', stage: 'site', select: ['excavation', 'foundation-*', 'slab-*', 'column-*',
        'beam-*', 'wall-*', 'stair*', 'roof-*', 'opening-*', 'finish-*', 'yard-*'],
        action: 'pour', startSeconds: 0, endSeconds: 1, after: []},
    ];
    const owners = ownerMap(buildComponents(house), full);
    expect(owners.size).toBe(76);
  });
});

describe('关键几何包围盒', () => {
  it('柱、板、屋面与墙体', () => {
    const column = boxBounds(house, component('column-1-0-front'));
    expect(column.center[0]).toBeCloseTo(-5.55);
    expect(column.center[1]).toBeCloseTo(1.61);
    expect(column.center[2]).toBeCloseTo(4.08);
    expect(column.size).toEqual([0.32, 2.78, 0.32]);
    expect(boxBounds(house, component('slab-2'))).toEqual({
      center: [0, 3.11, 0], size: [12, 0.22, 9],
    });
    const roof = boxBounds(house, component('roof-left'));
    expect(roof.center[0]).toBeCloseTo(-3.3);
    expect(roof.center[1]).toBeCloseTo(7.1);
    expect(roof.size[0]).toBeCloseTo(6.957, 2);
    expect(roof.size[2]).toBeCloseTo(10.2);
    const wall = boxBounds(house, component('wall-1-front-0'));
    expect(wall.center[0]).toBeCloseTo(0);
    expect(wall.center[1]).toBeCloseTo(1.61);
    expect(wall.center[2]).toBeCloseTo(4.375);
    expect(wall.size).toEqual([12, 2.78, 0.25]);
  });

  it('墙体洞口数量等于该面开口数', () => {
    const front = boxBounds(house, component('wall-1-front-0'));
    expect(front.size).toEqual([12, 2.78, 0.25]);
    expect(wallHoleCount(house, 1, 'front')).toBe(2);
    expect(wallHoleCount(house, 1, 'left')).toBe(1);
    expect(wallHoleCount(house, 2, 'back')).toBe(0);
    const specs = buildComponents(house);
    expect(specs.filter((item) => item.kind === 'opening')).toHaveLength(4);
  });
});

describe('闭式动作求值', () => {
  it('生长端点与中点只依赖帧时间', () => {
    const column = component('column-1-0-front');
    const start = transformFor(house, column, steps[1], 20);
    const middle = transformFor(house, column, steps[1], 22);
    const end = transformFor(house, column, steps[1], 24);
    expect(start.scale[1]).toBeCloseTo(0.001);
    expect(middle.scale[1]).toBeCloseTo(0.5);
    expect(end.position[0]).toBeCloseTo(-5.55);
    expect(end.position[1]).toBeCloseTo(1.61);
    expect(end.position[2]).toBeCloseTo(4.08);
    expect(end.rotation).toEqual([0, 0, 0]);
    expect(end.scale).toEqual([1, 1, 1]);
    expect(end.opacity).toBe(1);
    expect(transformFor(house, column, steps[1], 22)).toEqual(middle);
  });

  it('插入动作从缩小淡入到最终几何', () => {
    const opening = component('opening-door-entry');
    const start = transformFor(house, opening, steps[2], 50);
    const end = transformFor(house, opening, steps[2], 53);
    expect(start.opacity).toBeCloseTo(0);
    expect(start.scale[0]).toBeCloseTo(0.85);
    expect(end.opacity).toBeCloseTo(1);
    expect(end.scale).toEqual([1, 1, 1]);
  });

  it('当前步骤查询不依赖历史', () => {
    expect(currentStep(steps, 22).id).toBe('columns-1');
    expect(currentStep(steps, 7).id).toBe('excavate');
    expect(currentStep(steps, 99).id).toBe('insert-door');
  });
});
