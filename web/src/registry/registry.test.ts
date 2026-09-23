import { describe, expect, it } from 'vitest';
import { knownPrimitiveTypes, primitiveDefinition, PRIMITIVES, STYLE_PACKS, supportsContinuityTransform } from '@/registry';

describe('视觉原语注册表', () => {
  it('为每种风格包登记确定性的动效配方', () => {
    expect(Object.keys(STYLE_PACKS).sort()).toEqual(['cinematic', 'editorial', 'poetic', 'technical']);
    for (const recipe of Object.values(STYLE_PACKS)) {
      expect(recipe.riseDistance).toBeGreaterThan(0);
      expect(recipe.transitionSpan).toBeGreaterThan(0);
    }
  });
  it('只允许同类或登记过的跨幕原语变形', () => {
    expect(supportsContinuityTransform('shape', 'shape')).toBe(true);
    expect(supportsContinuityTransform('flow', 'cycle')).toBe(true);
    expect(supportsContinuityTransform('text', 'image')).toBe(false);
  });
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
