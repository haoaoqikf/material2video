import { describe, expect, it } from 'vitest';
import { fitRoleDown, motionStyle, resolveContent, ROLE_LADDER } from './SceneTree';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';

describe('场景树运行时', () => {
  it('只解析 data 内容引用', () => {
    expect(resolveContent({ title: '甲', nested: { value: 2 } }, 'data.nested.value')).toBe(2);
    expect(resolveContent({ title: '甲' }, 'visual.title')).toBeUndefined();
  });
  it('支持下标引用且与校验器同一语义', () => {
    expect(resolveContent({ steps: ['甲', '乙'] }, 'data.steps[1]')).toBe('乙');
    expect(resolveContent({ steps: ['甲'] }, 'data.steps[3]')).toBeUndefined();
    expect(resolveContent({ steps: ['甲'] }, 'data.steps[0]')).toBe('甲');
  });
  it('同一帧的动效样式可复现且不改变布局声明', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions = [{ target: 'text', recipe: 'rise', startFrame: 0, durationFrames: 20 }];
    expect(motionStyle(scene, 'text', 7)).toEqual(motionStyle(scene, 'text', 7));
    expect(scene.sceneTree.children).toHaveLength(1);
  });
});

describe('预设字号取档', () => {
  const fitsFor = (tooWide: string[]) => (role: string) => !tooWide.includes(role);

  it('放得下时保持声明档位', () => {
    expect(fitRoleDown('title', fitsFor([]))).toEqual({ role: 'title', measured: true });
  });
  it('放不下时沿阶梯向下取档', () => {
    expect(fitRoleDown('hero', fitsFor(['hero', 'headline']))).toEqual({ role: 'title', measured: true });
    expect(fitRoleDown('body', fitsFor(ROLE_LADDER as unknown as string[]))).toEqual({ role: 'caption', measured: true });
  });
  it('同一输入重复取档结果一致', () => {
    const fits = fitsFor(['hero']);
    expect(fitRoleDown('hero', fits)).toEqual(fitRoleDown('hero', fits));
  });
  it('阶梯必须从大到小', () => {
    expect(ROLE_LADDER[0]).toBe('hero');
    expect(ROLE_LADDER[ROLE_LADDER.length - 1]).toBe('caption');
  });
});
