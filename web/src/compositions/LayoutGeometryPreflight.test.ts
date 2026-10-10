import { describe, expect, it } from 'vitest';
import { layoutSampleFrames, unionGeometryBoxes } from './LayoutGeometryPreflight';
import type { CompiledStateTrack } from '@/runtime/stateTracksV4';

describe('布局预检几何', () => {
  it('只采样全局首尾帧和状态轨道的变化边界，顺序稳定且去重', () => {
    const tracks = [
      { id: 'copy', target: 'title', property: 'value', startFrame: 12, endFrame: 24 } as CompiledStateTrack,
      { id: 'visibility', target: 'note', property: 'visible', startFrame: 24, endFrame: 30 } as CompiledStateTrack,
    ];
    expect(layoutSampleFrames(40, tracks, [{ startFrame: 0, endFrame: 8 }, { startFrame: 30, endFrame: 35 }])).toEqual([0, 7, 12, 23, 24, 29, 30, 34, 39]);
    expect(layoutSampleFrames(1, tracks)).toEqual([0]);
  });

  it('为同一节点合并动态文案布局边界', () => {
    const boxes = unionGeometryBoxes(
      new Map([['title', { x: .2, y: .3, width: .2, height: .05, radius: .1 }]]),
      new Map([['title', { x: .1, y: .25, width: .4, height: .1, radius: .2 }],
        ['note', { x: .5, y: .6, width: .2, height: .04, radius: .1 }]]),
    );
    expect(boxes.get('title')).toMatchObject({ x: .1, y: .25, width: .4, radius: .2 });
    expect(boxes.get('title')?.height).toBeCloseTo(.1);
    expect(boxes.get('note')).toMatchObject({ x: .5, y: .6, radius: .1 });
    expect(boxes.get('note')?.width).toBeCloseTo(.2);
    expect(boxes.get('note')?.height).toBeCloseTo(.04);
  });
});
