import {describe, expect, it} from 'vitest';
import {
  burstField, dissolvePair, expandingRings, pointAlongPolyline, samplePath, sampleTrail, staggerReveal,
} from './dynamics';

const linear = (t: number) => t;
const square = (t: number) => t * t;

describe('共享动态几何原语', () => {
  it('沿弧长采样单条路径', () => {
    const points = samplePath('M0 0 L100 0 L100 100', 5);
    expect(points.map(point => [Math.round(point.x), Math.round(point.y)])).toEqual([
      [0, 0], [50, 0], [100, 0], [100, 50], [100, 100],
    ]);
  });

  it('折线位置按累计弧长插值并返回切向', () => {
    const result = pointAlongPolyline([{x: 0, y: 0}, {x: 100, y: 0}, {x: 100, y: 100}], 0.75);
    expect(result.point.x).toBe(100);
    expect(result.point.y).toBe(50);
    expect(result.angle).toBeCloseTo(Math.PI / 2);
  });

  it('拖尾按年龄衰减，端点透明，重复求值一致', () => {
    const points = [{x: 0, y: 0}, {x: 100, y: 0}];
    const once = sampleTrail({points, progress: 1, length: 0.2, count: 5, easing: linear});
    const twice = sampleTrail({points, progress: 1, length: 0.2, count: 5, easing: linear});
    expect(twice).toEqual(once);
    expect(once[0].x).toBe(100);
    expect(once[0].opacity).toBe(1);
    expect(once[4].x).toBe(80);
    expect(once[4].opacity).toBe(0);
    expect(once.map(sample => sample.age)).toEqual([0, 0.25, 0.5, 0.75, 1]);
  });

  it('爆散粒子端点透明、同种子同形态、换种子换形态', () => {
    const start = burstField({count: 12, progress: 0, seed: 'burst', origin: {x: 10, y: 20},
      speed: 80, lifetime: 0.8, easing: linear});
    const end = burstField({count: 12, progress: 1, seed: 'burst', origin: {x: 10, y: 20},
      speed: 80, lifetime: 0.8, easing: linear});
    expect(start.every(particle => particle.opacity === 0)).toBe(true);
    expect(end.every(particle => particle.opacity === 0)).toBe(true);
    const once = burstField({count: 12, progress: 0.5, seed: 'burst', easing: linear});
    const twice = burstField({count: 12, progress: 0.5, seed: 'burst', easing: linear});
    expect(twice).toEqual(once);
    const other = burstField({count: 12, progress: 0.5, seed: 'other', easing: linear});
    expect(other.map(particle => particle.x)).not.toEqual(once.map(particle => particle.x));
  });

  it('扩散环每环独立年龄，半径单调、端点透明', () => {
    const rings = expandingRings({count: 3, progress: 0.5, baseRadius: 10, travel: 100,
      thickness: 2, life: 0.7, stagger: 0.5, easing: square});
    expect(rings[0].radius).toBeGreaterThan(rings[1].radius);
    expect(rings.every(ring => ring.opacity >= 0 && ring.opacity <= 1)).toBe(true);
    const start = expandingRings({count: 3, progress: 0, baseRadius: 10, travel: 100, easing: linear});
    const end = expandingRings({count: 3, progress: 1, baseRadius: 10, travel: 100, easing: linear});
    expect(start.every(ring => ring.opacity === 0)).toBe(true);
    expect(end.every(ring => ring.opacity === 0)).toBe(true);
  });

  it('互补溶解的和恒为 1', () => {
    for (const progress of [0, 0.2, 0.5, 0.8, 1]) {
      const pair = dissolvePair(progress, square);
      expect(pair.out + pair.in).toBeCloseTo(1);
    }
  });

  it('错峰揭示端点精确，先出现的先完成', () => {
    expect(staggerReveal({count: 5, progress: 0, stagger: 0.4, easing: linear})).toEqual([0, 0, 0, 0, 0]);
    expect(staggerReveal({count: 5, progress: 1, stagger: 0.4, easing: linear})).toEqual([1, 1, 1, 1, 1]);
    const middle = staggerReveal({count: 5, progress: 0.5, stagger: 0.4, easing: linear});
    expect(middle[0]).toBeGreaterThan(middle[4]);
  });
});
