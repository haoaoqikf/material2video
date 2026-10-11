import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  createSceneRandom,
  freezeFrameOption,
  frameStroke,
  layoutGraph,
  probe,
  type M2VGraphEdge,
  type M2VGraphNode,
} from './index';
import { FrameIcon } from './adapters/icons';
import { ChartBarIncreasing } from 'lucide-react';

describe('稳定种子随机（任务 5.5）', () => {
  it('同一节点标识永远返回同一序列', () => {
    const sceneA = createSceneRandom('scene-1');
    const first = Array.from({ length: 8 }, () => sceneA('kpi'));
    const second = Array.from({ length: 8 }, () => sceneA('kpi'));
    expect(first).toEqual(second);
  });

  it('序列与求值顺序无关：多次寻帧重放得到同一组值', () => {
    const scene = createSceneRandom('scene-1');
    // 每次调用都从种子重新出发：同一节点在任何帧、任何求值顺序下
    // 返回同一个值（渲染是纯函数，重放即重算）。
    const draws = (): { a: number; b: number } => ({ a: scene('a'), b: scene('b') });
    expect(draws()).toEqual(draws());
    expect(draws()).toEqual({ a: scene('a'), b: scene('b') });

    // 需要一列随机值时用索引化的节点标识：每个槽位独立、稳定、可重放
    const slots = (count: number): number[] => {
      const values: number[] = [];
      for (let i = 0; i < count; i += 1) values.push(scene(`slot-${i}`));
      return values;
    };
    expect(slots(6)).toEqual(slots(6));
    expect(new Set(slots(6)).size).toBeGreaterThan(1);
  });

  it('不同场景/节点的序列相互独立', () => {
    expect(createSceneRandom('s1')()).not.toBe(createSceneRandom('s2')());
    expect(createSceneRandom('s1')('x')).not.toBe(createSceneRandom('s1')('y'));
  });
});

describe('ECharts 帧驱动选项（任务 5.2）', () => {
  it('动画在用户 option 之后被强制关闭', () => {
    const frozen = freezeFrameOption({
      animation: true,
      animationDuration: 800,
      series: [{ type: 'bar', data: [1, 2, 3] }],
    });
    expect(frozen.animation).toBe(false);
    expect(frozen.animationDuration).toBe(0);
    expect(frozen.animationDurationUpdate).toBe(0);
    // 作品数据原样保留
    expect(frozen.series).toEqual([{ type: 'bar', data: [1, 2, 3] }]);
  });
});

describe('Dagre 稳定布局（任务 5.3）', () => {
  const nodes: M2VGraphNode[] = [
    { id: 'ingest', width: 120, height: 48 },
    { id: 'clean', width: 120, height: 48 },
    { id: 'chart', width: 160, height: 64 },
  ];
  const edges: M2VGraphEdge[] = [
    { from: 'ingest', to: 'clean' },
    { from: 'clean', to: 'chart' },
  ];

  it('不同枚举顺序产生完全相同的坐标与路径', () => {
    const ordered = layoutGraph(nodes, edges);
    const reversed = layoutGraph([...nodes].reverse(), [...edges].reverse());
    const shuffled = layoutGraph([nodes[1]!, nodes[2]!, nodes[0]!], [edges[1]!, edges[0]!]);
    expect(reversed).toEqual(ordered);
    expect(shuffled).toEqual(ordered);
  });

  it('输出被深冻结，渲染期间不可改写', () => {
    const layout = layoutGraph(nodes, edges);
    expect(Object.isFrozen(layout)).toBe(true);
    expect(Object.isFrozen(layout.nodes[0])).toBe(true);
    expect(() => {
      (layout as { width: number }).width = 999;
    }).toThrow();
  });

  it('边引用未声明节点时硬失败', () => {
    expect(() => layoutGraph(nodes, [{ from: 'ingest', to: 'ghost' }])).toThrow(/未声明/);
    expect(() => layoutGraph([...nodes, nodes[0]!], edges)).toThrow(/重复/);
  });
});

describe('SVG 探针与图标约束（任务 5.4）', () => {
  it('FrameIcon 渲染本地 SVG，不产生外部 use 或链接', () => {
    const html = renderToStaticMarkup(<FrameIcon icon={ChartBarIncreasing} size={48} progress={0.5} aria-label="趋势" />);
    expect(html).toContain('<svg');
    expect(html).not.toContain('<use');
    expect(html).not.toContain('href="http');
    expect(html).not.toContain('xlink');
    expect(html).toContain('aria-label="趋势"');
    // 透明度由帧号驱动，走 style 而非 CSS 动画
    expect(html).toContain('opacity:0.5');
  });

  it('frameStroke 把进度映射成 dasharray/offset，端点闭合', () => {
    expect(frameStroke(0)).toEqual({ dasharray: expect.any(String), offset: 1.0001 });
    expect(frameStroke(1).offset).toBeCloseTo(0, 6);
    const half = frameStroke(0.5);
    expect(Number(half.offset)).toBeCloseTo(0.50005, 6);
  });

  it('probe 标记包含节点、角色与 schematic 声明', () => {
    expect(probe({ node: 'value', role: 'headline' })).toEqual({
      'data-m2v-node': 'value',
      'data-m2v-role': 'headline',
    });
    expect(probe({ node: 'shape', schematic: true })['data-m2v-schematic']).toBe('');
  });
});
