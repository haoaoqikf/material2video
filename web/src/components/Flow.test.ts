/**
 * flow 布局与连线几何的确定性断言（任务 8.1 / 8.3 的「机检」部分）。
 *
 * 两条被钉死的性质：
 *
 * 1. **同一份节点与连线，布局两次逐值相同**——布局是纯函数，
 *    不含测量、拟合或随机；这正是规格里「关系图布局可复现」场景的实现侧证据。
 * 2. **连线几何只由布局点串决定**：折线长度是解析值（各段之和），
 *    箭镞与截短是纯几何——渲染路径上没有任何 `getTotalLength()` 式的实时测量。
 */

import { describe, expect, it } from 'vitest';

import { arrowHead, edgeGeometry, polylineLength, trimPolylineEnd } from '@/flow/edges';
import { FLOW_VIEW, flowNodeSize, flowTextLines, flowViewTransform } from '@/components/Flow';
import { layoutFlow } from '@/flow/layout';
import { parseFlowEdges, parseFlowNodes } from '@/flow/parse';

const NODES = [
  { id: '报名', width: 160, height: 90 },
  { id: '准备', width: 160, height: 90 },
  { id: '上场', width: 180, height: 90 },
  { id: '落选', width: 150, height: 90 },
];

const EDGES = [
  { from: '报名', to: '准备' },
  { from: '准备', to: '上场' },
  { from: '上场', to: '落选' },
];

/** 离一个点最近的节点 id（用于断言连线的起终点落在正确的节点边框上）。 */
function nearestNode(centers: Map<string, { x: number; y: number }>, point: { x: number; y: number }): string {
  let bestId = '';
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const [id, center] of centers) {
    const distance = Math.hypot(point.x - center.x, point.y - center.y);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestId = id;
    }
  }
  return bestId;
}

describe('layoutFlow：纯函数分层布局（任务 8.1）', () => {
  it('同一份节点与连线布局两次结果逐值相同', () => {
    const first = layoutFlow(NODES, EDGES);
    const second = layoutFlow(NODES, EDGES);
    expect(first).toEqual(second);
  });

  it('布局里没有 NaN：所有坐标与尺寸都是有限数', () => {
    const layout = layoutFlow(NODES, EDGES);
    for (const node of layout.nodes) {
      expect(Number.isFinite(node.x)).toBe(true);
      expect(Number.isFinite(node.y)).toBe(true);
      expect(node.width).toBeGreaterThan(0);
      expect(node.height).toBeGreaterThan(0);
    }
    for (const edge of layout.edges) {
      expect(edge.points.length).toBeGreaterThanOrEqual(2);
      for (const point of edge.points) {
        expect(Number.isFinite(point.x)).toBe(true);
        expect(Number.isFinite(point.y)).toBe(true);
      }
    }
    expect(layout.width).toBeGreaterThan(0);
    expect(layout.height).toBeGreaterThan(0);
  });

  it('连线方向与输入一致：起终点分别贴着源节点与目标节点的边框', () => {
    const layout = layoutFlow(NODES, EDGES);
    const centers = new Map(layout.nodes.map((node) => [node.id, node]));
    for (const edge of layout.edges) {
      const source = centers.get(edge.from)!;
      const target = centers.get(edge.to)!;
      const start = edge.points[0]!;
      const end = edge.points[edge.points.length - 1]!;
      const toSource = Math.hypot(start.x - source.x, start.y - source.y);
      const toTarget = Math.hypot(end.x - target.x, end.y - target.y);
      // 等尺寸节点上下直连时，两个距离都等于半高——所以是 ≤ 而不是 <
      expect(toSource).toBeLessThanOrEqual(toTarget);
      // 起点离源节点最近、终点离目标节点最近（而不是接到了别人身上）
      const nearestToStart = nearestNode(centers, start);
      const nearestToEnd = nearestNode(centers, end);
      expect(nearestToStart).toBe(edge.from);
      expect(nearestToEnd).toBe(edge.to);
    }
  });

  it('换输入必有不同：布局随节点尺寸与连线变化', () => {
    const baseline = layoutFlow(NODES, EDGES);
    const wider = layoutFlow(
      NODES.map((node) => ({ ...node, width: node.width + 40 })),
      EDGES,
    );
    expect(wider).not.toEqual(baseline);

    const rerouted = layoutFlow(NODES, [EDGES[0]!, { from: '报名', to: '上场' }, EDGES[2]!]);
    expect(rerouted).not.toEqual(baseline);
  });

  it('反馈回路（环）也能布局：dagre 自己断环，结果仍然确定', () => {
    const loop = [...EDGES, { from: '落选', to: '准备' }];
    const first = layoutFlow(NODES, loop);
    const second = layoutFlow(NODES, loop);
    expect(first).toEqual(second);
  });

  it('重复的节点 id 抛错：两个同名节点会被画成同一个', () => {
    expect(() =>
      layoutFlow([...NODES, { id: '报名', width: 120, height: 80 }], EDGES),
    ).toThrow(/重复/);
  });

  it('悬空的连线抛错：两端必须都是已声明的节点', () => {
    expect(() => layoutFlow(NODES, [{ from: '报名', to: '不存在' }])).toThrow(/不存在/);
  });
});

describe('连线几何：解析长度与箭镞（任务 8.3）', () => {
  it('折线长度是各段之和（解析值）', () => {
    const points = [
      { x: 0, y: 0 },
      { x: 3, y: 4 },
      { x: 3, y: 10 },
    ];
    expect(polylineLength(points)).toBeCloseTo(5 + 6, 10);
  });

  it('末端截短只影响最后一段：截掉多少，终点就往回退多少', () => {
    const points = [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
    ];
    const trimmed = trimPolylineEnd(points, 34);
    expect(trimmed).toHaveLength(2);
    expect(trimmed[0]!.x).toBe(0);
    expect(trimmed[1]!.x).toBeCloseTo(66, 10);
  });

  it('截短量超过整条折线时退化成起点，不产生 NaN', () => {
    const points = [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
    ];
    const trimmed = trimPolylineEnd(points, 100);
    expect(trimmed).toEqual([{ x: 0, y: 0 }]);
  });

  it('箭镞顶点在终点上，底边垂直于最后一段', () => {
    const points = [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
    ];
    const [tip, left, right] = arrowHead(points);
    expect(tip!.x).toBe(100);
    expect(tip!.y).toBe(0);
    // 底边的两个角关于连线对称
    expect(left!.x).toBeCloseTo(right!.x, 10);
    expect(left!.y).toBeCloseTo(-right!.y, 10);
  });

  it('edgeGeometry 把长度与路径一起给出；进度交给 drawPathStyle 原语', () => {
    const points = [
      { x: 0, y: 0 },
      { x: 0, y: 200 },
    ];
    const geometry = edgeGeometry(points);
    expect(geometry.path).toContain('M0.00 0.00');
    expect(geometry.length).toBeGreaterThan(0);
    expect(geometry.length).toBeLessThan(200);
    expect(geometry.arrow).toHaveLength(3);
  });
});

describe('分镜数据解析（画不出来要报错）', () => {
  it('字符串节点：字符串本身就是 id 与文字', () => {
    expect(parseFlowNodes(['报名', '上场'])).toEqual([
      { id: '报名', label: '报名' },
      { id: '上场', label: '上场' },
    ]);
  });

  it('对象节点：label 缺省时退到 id', () => {
    expect(parseFlowNodes([{ id: 'n1' }, { id: 'n2', label: '上场' }])).toEqual([
      { id: 'n1', label: 'n1' },
      { id: 'n2', label: '上场' },
    ]);
  });

  it('nodes 缺失或空数组抛错', () => {
    expect(() => parseFlowNodes(undefined)).toThrow(/nodes/);
    expect(() => parseFlowNodes([])).toThrow(/nodes/);
  });

  it('没有声明 edges 时按顺序连成链', () => {
    const nodes = parseFlowNodes(['一', '二', '三']);
    expect(parseFlowEdges(undefined, nodes)).toEqual([
      { from: '一', to: '二' },
      { from: '二', to: '三' },
    ]);
  });

  it('显式声明的 edges 以声明为准（空数组就是不要连线）', () => {
    const nodes = parseFlowNodes(['一', '二', '三']);
    expect(parseFlowEdges([], nodes)).toEqual([]);
    expect(parseFlowEdges([['一', '三']], nodes)).toEqual([{ from: '一', to: '三' }]);
    expect(parseFlowEdges([{ from: '三', to: '一' }], nodes)).toEqual([{ from: '三', to: '一' }]);
  });

  it('引用不存在节点的边抛错', () => {
    const nodes = parseFlowNodes(['一', '二']);
    expect(() => parseFlowEdges([['一', '三']], nodes)).toThrow(/不是任何节点的 id/);
  });
});

describe('节点盒子：尺寸由实测文字宽度决定（K8 的前提）', () => {
  const widthOf = (line: string) => line.length * 40; // 每字符 40px 的量尺替身

  it('短标签单行：宽度 = 文字宽 + 左右内边距', () => {
    const size = flowNodeSize('上场', widthOf);
    expect(size.lines).toEqual(['上场']);
    expect(size.width).toBe(80 + 28 * 2);
    expect(size.height).toBe(46 + 22 * 2);
    expect(size.measured).toBe(true);
  });

  it('超长标签折行：行数取上限的 ceil，宽度按最宽的一行算', () => {
    const label = '一二三四五六七八九十'; // 10 字 × 40px = 400px > 320px 上限 → 2 行
    const size = flowNodeSize(label, widthOf);
    expect(size.lines).toHaveLength(2);
    expect(size.lines.join('')).toBe(label);
    // 均衡切开是 5 + 5：最宽一行 5 × 40px = 200px
    expect(size.width).toBe(200 + 28 * 2);
    expect(size.height).toBe(2 * 46 + 22 * 2);
  });

  it('量不到宽度走降级：单行原文 + 按字数估宽，不抛错', () => {
    const size = flowNodeSize('上场', () => 0);
    expect(size.measured).toBe(false);
    expect(size.lines).toEqual(['上场']);
    expect(size.width).toBe(2 * 40 + 28 * 2);
  });

  it('多行文字按行盒中心对称铺开', () => {
    const size = flowNodeSize('一二三四五六七八九十', widthOf);
    const lines = flowTextLines(size, 100, 200);
    expect(lines).toHaveLength(2);
    expect(lines[0]!.y).toBeCloseTo(200 - 23, 10);
    expect(lines[1]!.y).toBeCloseTo(200 + 23, 10);
    expect(lines[0]!.x).toBe(100);
  });
});

describe('画布缩放：布局等比缩放居中', () => {
  it('小图放大但有上限，大图缩小到画布内', () => {
    const tiny = layoutFlow(
      [
        { id: '一', width: 100, height: 90 },
        { id: '二', width: 100, height: 90 },
      ],
      [],
    );
    const transform = flowViewTransform(tiny);
    const scale = Number(/scale\(([\d.]+)\)/.exec(transform)![1]);
    expect(scale).toBeLessThanOrEqual(1.5);

    const huge = layoutFlow(
      Array.from({ length: 6 }, (_unused, index) => ({
        id: `节点${index}`,
        width: 400,
        height: 90,
      })),
      [],
    );
    const hugeTransform = flowViewTransform(huge);
    const hugeScale = Number(/scale\(([\d.]+)\)/.exec(hugeTransform)![1]);
    expect(hugeScale).toBeLessThan(1);
    expect(huge.width * hugeScale).toBeLessThanOrEqual(FLOW_VIEW.W);
  });
});
