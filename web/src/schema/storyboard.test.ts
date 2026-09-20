import { describe, expect, it } from 'vitest';
import { EMPTY_STORYBOARD, parseStoryboard, sceneSchema } from '@/schema/storyboard';

describe('v2 分镜 schema', () => {
  it('接受最小有效场景树', () => expect(parseStoryboard(EMPTY_STORYBOARD).version).toBe(2));
  it('拒绝旧分镜并给出迁移提示', () => expect(() => parseStoryboard({ version: 1 })).toThrow(/migrate_storyboard/));
  it('拒绝重复节点 id', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree.children!.push({ id: 'text', type: 'shape' });
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝不存在的动效目标', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions.push({ target: 'missing', recipe: 'fade', startFrame: 0 });
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝自由样式字段', () => {
    const input = structuredClone(EMPTY_STORYBOARD) as unknown as { scenes: Array<{ sceneTree: Record<string, unknown> }> };
    input.scenes[0]!.sceneTree.style = { color: 'red' };
    expect(() => parseStoryboard(input)).toThrow(/style/);
  });
  it('拒绝指向 data 之外的内容引用', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree.children![0]!.contentRef = 'visual.text';
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝原语未注册的属性', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree.ratio = '1:1';
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝原语不支持的动效配方', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions = [{ target: 'text', recipe: 'count', startFrame: 0 }];
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝超出场景时长的动效', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions = [{ target: 'text', recipe: 'reveal', startFrame: 29, durationFrames: 5 }];
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝超出节点数上限的场景树', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree.children = Array.from({ length: 48 }, (_, i) => ({ id: `n${i}`, type: 'shape' as const }));
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
});
