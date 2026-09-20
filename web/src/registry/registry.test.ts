import { describe, expect, it } from 'vitest';
import { knownPrimitiveTypes, primitiveDefinition, PRIMITIVES } from '@/registry';

describe('视觉原语注册表', () => {
  it('覆盖首批三类原语且类型唯一', () => {
    expect(knownPrimitiveTypes()).toContain('stack');
    expect(knownPrimitiveTypes()).toContain('text');
    expect(knownPrimitiveTypes()).toContain('shape');
    expect(new Set(knownPrimitiveTypes()).size).toBe(Object.keys(PRIMITIVES).length);
  });
  it('声明容量、属性、动效和来源', () => {
    for (const type of knownPrimitiveTypes()) {
      const entry = primitiveDefinition(type)!;
      expect(entry.children).toHaveLength(2);
      expect(entry.props).toBeInstanceOf(Array);
      expect(entry.motions.length).toBeGreaterThan(0);
      expect(entry.source).toMatch(/\.tsx$/);
    }
  });
});
