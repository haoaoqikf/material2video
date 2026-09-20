/**
 * `flow` 组件的分层布局：dagre 外面包一层**纯函数**外壳（任务 8.1）。
 *
 * 为什么是 dagre 而不是 React Flow：见本变更 design.md 决定 5——
 * React Flow 的节点测量与 `fitView()` 依赖异步布局与 `requestAnimationFrame`，
 * 在逐帧随机访问的渲染里「偶发失效」就是闪烁。分层布局本身只需要一个纯函数：
 * 节点位置由「节点的尺寸 + 谁连谁」决定，算一次、缓存、逐帧复用。
 *
 * 纯函数外壳的意思是：
 *
 * - **输入完全决定输出**。dagre 的 `layout()` 会把坐标写进图对象（原地修改），
 *   因此图对象在函数内部新建，外部只见到返回的普通对象——同一份输入调用两次，
 *   得到的两张布局逐值相同（`Flow.test.ts` 逐值断言）。
 * - **没有测量、没有拟合**。节点宽高由调用方给出（flow 组件按实测文字宽度算出，
 *   与帧号无关）；布局本身不读 DOM、不读视口。
 * - **确定性来自 dagre 本身**：它没有随机源，排序走稳定的插入序。
 *   唯一要小心的是「同一份输入」必须是同一份——节点按数组的顺序进图，
 *   调用方不许自己打乱。
 *
 * 坐标约定：dagre 给的是**中心点**，这里原样保留中心点（矩形按中心画最省心），
 * `width` / `height` 是节点盒子的完整尺寸。`width` / `height`（顶层）是整张图
 * 的外接尺寸，来自 dagre 的图属性（含它自己的边距，marginx/marginy 设为 0）。
 */
import dagre from '@dagrejs/dagre';

/** 布局的间距参数（px，布局坐标系）。与字号一样是组件设计值，不随分镜变化。 */
export const FLOW_LAYOUT = {
  /** 纵向相邻层的间距（ranksep）：因果链自上而下，层间留出连线与箭镞的位置 */
  RANKSEP: 64,
  /** 同层相邻节点的间距（nodesep） */
  NODESEP: 44,
} as const;

/** 参与布局的一个节点：`id` 是连线引用它的名字，宽高是节点盒子的尺寸。 */
export interface FlowNodeInput {
  id: string;
  width: number;
  height: number;
}

/** 参与布局的一条连线：`from` → `to` 都是节点的 `id`。 */
export interface FlowEdgeInput {
  from: string;
  to: string;
}

/** 布局后的一个节点：`x` / `y` 是盒子的**中心点**。 */
export interface FlowLayoutNode {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

/** 折线上的一个点（布局坐标系）。 */
export interface FlowPoint {
  x: number;
  y: number;
}

/** 布局后的一条连线：折线经过的点（起点贴着源节点边框，终点贴着目标节点边框）。 */
export interface FlowLayoutEdge {
  from: string;
  to: string;
  points: FlowPoint[];
}

/** 一次布局的完整结果：外接尺寸由 dagre 的图属性给出。 */
export interface FlowLayout {
  nodes: FlowLayoutNode[];
  edges: FlowLayoutEdge[];
  width: number;
  height: number;
}

/**
 * 对同一份节点与连线算一次分层布局。
 *
 * 方向固定 `TB`（自上而下）：因果链与流程步骤在竖屏里纵向铺开，读的顺序
 * 与画的顺序一致。环（反馈回路）交给 dagre 自己断——它在内部用 DFS 决定
 * 翻转哪条回边，这个过程也是确定性的。
 *
 * 两条输入约定（都在调用方的解析层保证，这里再挡一次）：
 * - `nodes` 不允许重复 `id`：dagre 会把它们并成同一个节点，两个盒子叠在一起；
 * - `edges` 的两端必须都在 `nodes` 里：悬空的连线没有落点。
 */
export function layoutFlow(nodes: readonly FlowNodeInput[], edges: readonly FlowEdgeInput[]): FlowLayout {
  const seen = new Set<string>();
  for (const node of nodes) {
    if (seen.has(node.id)) {
      throw new Error(`flow 布局失败：节点 id 重复（${node.id}）。两个节点同名会被画成同一个`);
    }
    seen.add(node.id);
  }
  for (const edge of edges) {
    if (!seen.has(edge.from) || !seen.has(edge.to)) {
      throw new Error(
        `flow 布局失败：连线 ${edge.from} -> ${edge.to} 引用了不存在的节点` +
          `（已声明：${[...seen].join('、') || '（无）'}）`,
      );
    }
  }

  /*
   * 图对象在函数内部新建：dagre 的 layout() 会把结果写回图对象（原地修改），
   * 复用外部的图会让第二次调用拿到「带着上次坐标」的输入——那就不再是纯函数。
   */
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({
    rankdir: 'TB',
    nodesep: FLOW_LAYOUT.NODESEP,
    ranksep: FLOW_LAYOUT.RANKSEP,
    marginx: 0,
    marginy: 0,
  });
  // 每条边都要有 label 对象，dagre 才会在坐标里返回折线点
  graph.setDefaultEdgeLabel(() => ({}));

  for (const node of nodes) {
    graph.setNode(node.id, { width: node.width, height: node.height });
  }
  for (const edge of edges) {
    graph.setEdge(edge.from, edge.to);
  }

  dagre.layout(graph);

  const graphLabel = graph.graph();
  const laidNodes: FlowLayoutNode[] = nodes.map((node) => {
    const laid = graph.node(node.id);
    return {
      id: node.id,
      x: laid.x,
      y: laid.y,
      width: laid.width,
      height: laid.height,
    };
  });
  const laidEdges: FlowLayoutEdge[] = edges.map((edge) => {
    const laid = graph.edge(edge.from, edge.to);
    return {
      from: edge.from,
      to: edge.to,
      points: laid.points.map((point) => ({ x: point.x, y: point.y })),
    };
  });

  return {
    nodes: laidNodes,
    edges: laidEdges,
    width: graphLabel.width ?? 0,
    height: graphLabel.height ?? 0,
  };
}
