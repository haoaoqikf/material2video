/**
 * 注册表运行时的自洽性（渲染层这一侧的机检）。
 *
 * 注册表元数据的唯一真源是 `registry.json`；Python 侧的生成物机检在
 * `tests/test_web_registry.py`。这里钉住渲染层消费注册表时必须成立的性质：
 *
 * 1. 分镜 schema 的 `kind` 枚举（生成物）与注册表是同一份集合——
 *    schema 放行的每个 kind 都真的有组件，注册表里的每个 kind schema 都认识；
 * 2. 默认映射只指向已实现的组件，且该组件声明了「适用于」那个场景类型；
 * 3. 已实现的组件都接上了组件本体（规划中的组件允许没有）。
 */

import { describe, expect, it } from 'vitest';

import { FIGURE_KINDS } from '@/schema/figureKinds';
import { DEFAULT_KIND_BY_SCENE, FIGURES, figureDefinition, knownKinds, resolveKind } from '@/registry';

describe('注册表：与分镜 schema 的 kind 枚举一致', () => {
  it('schema 放行的 kind 与注册表是同一份集合', () => {
    expect([...FIGURE_KINDS].sort()).toEqual(knownKinds());
  });

  it('已实现的组件都接上了组件本体', () => {
    for (const [kind, entry] of Object.entries(FIGURES)) {
      if (entry.implemented) {
        expect(entry.Component, `${kind} 声明 implemented 但没有组件本体`).toBeTypeOf('function');
      }
    }
  });
});

describe('注册表：默认映射', () => {
  it('每个默认组件都存在且已实现', () => {
    for (const [sceneType, kind] of Object.entries(DEFAULT_KIND_BY_SCENE)) {
      const entry = figureDefinition(kind);
      expect(entry, `${sceneType} 默认到不存在的组件 ${kind}`).toBeDefined();
      expect(entry!.implemented, `${kind} 还没实现，不能当 ${sceneType} 的默认`).toBe(true);
    }
  });

  it('默认组件声明了「适用于」那个场景类型', () => {
    for (const [sceneType, kind] of Object.entries(DEFAULT_KIND_BY_SCENE)) {
      const entry = figureDefinition(kind)!;
      expect(
        entry.sceneTypes,
        `${kind} 是 ${sceneType} 的默认，但 registry.json 的 sceneTypes 没有声明它`,
      ).toContain(sceneType);
    }
  });
});

describe('注册表：resolveKind', () => {
  it('分镜声明优先于默认映射', () => {
    const resolved = resolveKind('title', { figure: { kind: 'chart' } });
    expect(resolved).toBe('chart');
  });

  it('缺省时按场景类型取默认，两处都没有则返回 null', () => {
    expect(resolveKind('title', {})).toBe(DEFAULT_KIND_BY_SCENE['title']);
    expect(resolveKind('不存在的类型', {})).toBeNull();
  });
});
