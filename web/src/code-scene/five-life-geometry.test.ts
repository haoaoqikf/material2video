import { describe, expect, it } from 'vitest';
import {
  AGE_SCALE,
  DEAD_END,
  INDUSTRY_LANES,
  LEARNING_BRIDGE,
  MAIN_BEFORE,
  NEW_PATH,
  NEW_START,
  REALIZED,
  TREE_PATHS,
  cameraAt,
  cameraFrame,
  industryDistance,
  lifeMarkPoint,
  makePath,
  projectPoint,
  subjectAt,
  type Vec3,
} from '../../../examples/five-life-choices/scenes/geometry';

const distance = (a: Vec3, b: Vec3) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

describe('五选择路径表', () => {
  it('零长度路径可取样、可裁剪且不会产生 NaN', () => {
    const path = makePath([[1, 2, 3], [1, 2, 3]]);
    expect(path.length).toBe(0);
    expect(path.atDistance(0)).toEqual([1, 2, 3]);
    expect(path.atDistance(999)).toEqual([1, 2, 3]);
    expect(path.atU(0.5)).toEqual([1, 2, 3]);
    expect(path.cut(10)).toHaveLength(2);
    expect(Number.isFinite(path.atDistance(10)[0])).toBe(true);
  });

  it('按累计距离取样时相邻点连续，端点精确', () => {
    const step = MAIN_BEFORE.length / 240;
    let previous = MAIN_BEFORE.atDistance(0);
    for (let i = 1; i <= 240; i += 1) {
      const point = MAIN_BEFORE.atDistance(step * i);
      expect(distance(previous, point)).toBeLessThanOrEqual(step * 1.05 + 1e-6);
      previous = point;
    }
    expect(distance(MAIN_BEFORE.atDistance(0), MAIN_BEFORE.points[0])).toBeLessThan(1e-6);
    expect(distance(MAIN_BEFORE.atDistance(MAIN_BEFORE.length),
      MAIN_BEFORE.points[MAIN_BEFORE.points.length - 1])).toBeLessThan(1e-6);
  });

  it('五条跑道共用同一世界距离，且距离单调、端点钳制', () => {
    const distances = [15.8, 18, 22, 25, 27].map(industryDistance);
    expect(distances).toEqual([...distances].sort((a, b) => a - b));
    expect(industryDistance(-10)).toBe(0);
    expect(industryDistance(999)).toBeCloseTo(Math.min(...INDUSTRY_LANES.map((lane) => lane.path.length)), 6);
    const d = industryDistance(22);
    const before = INDUSTRY_LANES[2].path.atDistance(d - 2);
    const after = INDUSTRY_LANES[2].path.atDistance(d + 2);
    expect(distance(before, after)).toBeGreaterThan(0);
  });

  it('叙事年龄平台期不会冻结主体；连接端点与断头/新起点重合', () => {
    const a = subjectAt(43.4).point;
    const b = subjectAt(45.9).point;
    expect(distance(a, b)).toBeGreaterThan(1);
    expect(distance(subjectAt(46.2).point, DEAD_END)).toBeLessThan(1);
    expect(distance(subjectAt(48.4).point, NEW_START)).toBeLessThan(1);
    expect(LEARNING_BRIDGE.length).toBeGreaterThan(100);
  });

  it('47 岁后的年龄刻度落在新路上，而不是被主路端点钳制', () => {
    const mark = lifeMarkPoint(60);
    expect(mark[0]).toBeCloseTo(60 * AGE_SCALE, 1);
    expect(distance(mark, NEW_PATH.points[NEW_PATH.points.length - 1])).toBeGreaterThan(10);
    expect(distance(mark, DEAD_END)).toBeGreaterThan(50);
  });

  it('结尾树有共享节点与父子关系，且主路是唯一亮路径', () => {
    const byId = new Map(TREE_PATHS.map((path) => [path.id, path]));
    const bright = TREE_PATHS.filter((path) => path.bright);
    expect(bright).toHaveLength(1);
    expect(bright[0].id).toBe('realized');
    for (const path of TREE_PATHS) {
      if (path.level === 2) {
        expect(path.parent).not.toBeNull();
        expect(byId.has(path.parent ?? '')).toBe(true);
      }
      if (path.level === 1) {
        const siblingOrigins = TREE_PATHS
          .filter((item) => item.level === 1 && item.origin === path.origin);
        expect(siblingOrigins.length).toBeGreaterThan(1);
      }
    }
    const endpoints = TREE_PATHS.filter((path) => path.level === 1)
      .map((path) => path.points[path.points.length - 1]);
    expect(new Set(endpoints.map((point) => point.join(','))).size).toBe(endpoints.length);
  });

  it('行业光点按常量世界距离推进，画面采样无阶梯或断点', () => {
    const worldSteps: number[] = [];
    for (let t = 16; t <= 26; t += 0.1) {
      worldSteps.push(industryDistance(t + 0.1) - industryDistance(t));
    }
    const nonZero = worldSteps.filter((step) => step > 1e-6);
    expect(nonZero.length).toBeGreaterThan(80);
    expect(Math.max(...nonZero) - Math.min(...nonZero)).toBeLessThan(1e-6);

    const lane = INDUSTRY_LANES[2];
    const screenMoves: number[] = [];
    let previous: {x: number; y: number} | null = null;
    for (let t = 16; t <= 26; t += 0.1) {
      const point = lane.path.atDistance(industryDistance(t));
      const frame = cameraFrame(cameraAt(t), {x: 0, y: 0, width: 1920, height: 1080});
      const projected = projectPoint(frame, point);
      expect(projected.visible).toBe(true);
      if (previous) screenMoves.push(Math.hypot(projected.x - previous.x, projected.y - previous.y));
      previous = {x: projected.x, y: projected.y};
    }
    const sorted = [...screenMoves].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];
    expect(Math.min(...screenMoves)).toBeGreaterThan(0.05);
    expect(Math.max(...screenMoves)).toBeLessThan(median * 5 + 1e-6);
  });

  it('主体在年龄平台期仍按路径推进，画面位移无突然跳变', () => {
    const moves: number[] = [];
    let previous = subjectAt(45).point;
    for (let t = 45.1; t <= 46.1; t += 0.1) {
      const point = subjectAt(t).point;
      moves.push(distance(previous, point));
      previous = point;
    }
    const sorted = [...moves].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];
    expect(median).toBeGreaterThan(0.5);
    expect(Math.max(...moves)).toBeLessThan(median * 5 + 1e-6);
  });

  it('同一时刻重复求值一致，已走路径包含连接与新路', () => {
    expect(subjectAt(33.333)).toEqual(subjectAt(33.333));
    expect(REALIZED.length).toBeGreaterThan(MAIN_BEFORE.length + LEARNING_BRIDGE.length);
    expect(TREE_PATHS.length).toBeGreaterThan(30);
  });
});
