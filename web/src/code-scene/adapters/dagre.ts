/**
 * Dagre 稳定布局 helper：把自动布局变成「输入集合决定结果」的纯函数。
 *
 * dagre 本身对输入**枚举顺序**敏感：同样的节点集合按不同顺序喂进去，
 * 内部迭代顺序不同，坐标可能差出一截。这里在入口做规范化：
 * - 节点按 id 排序、边按 `(from, to)` 排序后再喂给 dagre；
 * - 配置冻结为默认值（作品可以覆盖，但取的是显式字段，不继承顺序）；
 * - 输出深冻结：布局结果在渲染期间不可被改写。
 *
 * 同一个图（无论枚举顺序）永远得到同一份坐标与路径——
 * 这是随机寻帧与跨机器渲染确定性的前提。
 */
import dagre from '@dagrejs/dagre';

/** 图节点：id 必须稳定（与数据绑定，与出现顺序无关）。 */
export interface M2VGraphNode {
  id: string;
  width: number;
  height: number;
  /** 可选的显示标签；布局只关心 id 与尺寸。 */
  label?: string;
}

/** 有向边：from/to 必须引用已声明的节点 id。 */
export interface M2VGraphEdge {
  from: string;
  to: string;
  label?: string;
}

/** 布局配置：默认值冻结在此，覆盖需显式传字段。 */
export interface M2VGraphConfig {
  rankdir?: 'TB' | 'BT' | 'LR' | 'RL';
  nodesep?: number;
  ranksep?: number;
}

export interface M2VGraphPoint {
  x: number;
  y: number;
}

export interface M2VGraphLayoutNode extends M2VGraphPoint {
  id: string;
  width: number;
  height: number;
  label?: string;
}

export interface M2VGraphLayoutEdge {
  from: string;
  to: string;
  label?: string;
  /** dagre 计算的折线控制点（已按路径方向排序）。 */
  points: M2VGraphPoint[];
}

export interface M2VGraphLayout {
  /** 按 id 排序的节点坐标（中心点）。 */
  nodes: M2VGraphLayoutNode[];
  /** 按 (from, to) 排序的边路径。 */
  edges: M2VGraphLayoutEdge[];
  /** 整张图的包围盒尺寸，画布/取景用。 */
  width: number;
  height: number;
}

const DEFAULT_CONFIG: Required<M2VGraphConfig> = {
  rankdir: 'LR',
  nodesep: 48,
  ranksep: 96,
};

function deepFreeze<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const key of Object.keys(value as object)) {
      deepFreeze((value as Record<string, unknown>)[key]);
    }
  }
  return value;
}

/** 规范化排序：节点按 id，边按 (from, to)。 */
function normalize(nodes: readonly M2VGraphNode[], edges: readonly M2VGraphEdge[]): { nodes: M2VGraphNode[]; edges: M2VGraphEdge[] } {
  const sortedNodes = [...nodes].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const sortedEdges = [...edges].sort((a, b) =>
    a.from === b.from ? (a.to < b.to ? -1 : a.to > b.to ? 1 : 0) : a.from < b.from ? -1 : 1,
  );
  return { nodes: sortedNodes, edges: sortedEdges };
}

/**
 * 计算稳定布局。同一个 (nodes, edges) 集合无论以什么顺序传入、
 * 求值多少次，都返回深比较相等的布局结果。
 *
 * 抛错情形：边引用了未声明的节点、节点 id 重复——布局器宁可硬失败，
 * 也不输出一份悄悄歪掉的图。
 */
export function layoutGraph(
  nodes: readonly M2VGraphNode[],
  edges: readonly M2VGraphEdge[],
  config: M2VGraphConfig = {},
): M2VGraphLayout {
  const ids = new Set(nodes.map((node) => node.id));
  if (ids.size !== nodes.length) {
    throw new Error('layoutGraph：节点 id 重复，无法产生稳定布局');
  }
  for (const edge of edges) {
    if (!ids.has(edge.from) || !ids.has(edge.to)) {
      throw new Error(`layoutGraph：边 ${edge.from} → ${edge.to} 引用了未声明的节点`);
    }
  }

  const sorted = normalize(nodes, edges);
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({
    rankdir: config.rankdir ?? DEFAULT_CONFIG.rankdir,
    nodesep: config.nodesep ?? DEFAULT_CONFIG.nodesep,
    ranksep: config.ranksep ?? DEFAULT_CONFIG.ranksep,
    marginx: 0,
    marginy: 0,
  });
  graph.setDefaultEdgeLabel(() => ({}));
  for (const node of sorted.nodes) {
    graph.setNode(node.id, { width: node.width, height: node.height });
  }
  for (const edge of sorted.edges) {
    graph.setEdge(edge.from, edge.to);
  }
  dagre.layout(graph);

  const layoutNodes: M2VGraphLayoutNode[] = sorted.nodes.map((node) => {
    const placed = graph.node(node.id) as { x: number; y: number };
    return { id: node.id, x: placed.x, y: placed.y, width: node.width, height: node.height, ...(node.label !== undefined ? { label: node.label } : {}) };
  });
  const layoutEdges: M2VGraphLayoutEdge[] = sorted.edges.map((edge) => {
    const placed = graph.edge(edge.from, edge.to) as { points: M2VGraphPoint[] };
    return {
      from: edge.from,
      to: edge.to,
      ...(edge.label !== undefined ? { label: edge.label } : {}),
      points: placed.points.map((point) => ({ x: point.x, y: point.y })),
    };
  });
  const graphBounds = graph.graph() as { width: number; height: number };

  return deepFreeze({
    nodes: layoutNodes,
    edges: layoutEdges,
    width: graphBounds.width ?? 0,
    height: graphBounds.height ?? 0,
  });
}
