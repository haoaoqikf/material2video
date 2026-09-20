/**
 * flow 组件的分镜数据解析：`nodes` / `edges` → 布局输入。
 *
 * 「画不出来要报错」是渲染层的纪律（Python 校验器管不到挂载那一刻）：
 * 节点缺失、节点为空、连线引用了不存在的节点，都在这里抛出带字段路径的错误，
 * 不静默画一张空图。结构与 `references/storyboard-schema.md` 的 `diagram`
 * 字段一致，也镜像了 Python 校验器 `_validate_diagram` 的两条规则：
 * 节点是字符串或 `{id, label}`；边是 `[from, to]` 或 `{from, to}`。
 */

/** 布局与渲染共用的节点：`id` 供连线引用，`label` 是画出来的文字。 */
export interface FlowNode {
  id: string;
  label: string;
}

/** 一条连线：两端都是节点的 `id`。 */
export interface FlowEdge {
  from: string;
  to: string;
}

/** 一个节点的文字：字符串直接用；对象取 `label`，退到 `id`。 */
export function flowNodeLabel(node: unknown, index: number): FlowNode {
  if (typeof node === 'string') {
    if (!node.trim()) {
      throw new Error(`flow 组件画不出来：nodes[${index}] 是空白字符串`);
    }
    return { id: node, label: node };
  }
  if (node && typeof node === 'object') {
    const record = node as Record<string, unknown>;
    const id = record['id'];
    if (typeof id === 'string' && id.trim()) {
      const label = record['label'];
      return { id, label: typeof label === 'string' && label.trim() ? label : id };
    }
  }
  throw new Error(
    `flow 组件画不出来：nodes[${index}] 必须是字符串或含 id 的对象（形如 {"id": "暴露", "label": "被看见"}）`,
  );
}

/** 解析 `data.nodes`：缺失或空数组都抛错——一张没有节点的流程图画不出来。 */
export function parseFlowNodes(value: unknown): FlowNode[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(
      'flow 组件画不出来：data.nodes 必须是非空数组，每项是一个节点的文字或 {id, label}',
    );
  }
  return value.map((node, index) => flowNodeLabel(node, index));
}

/** 一条分镜边 → 两端 id；形状不对返回 null（由调用方报错）。 */
function edgePair(edge: unknown): [string, string] | null {
  if (Array.isArray(edge) && edge.length === 2) {
    const [from, to] = edge;
    if (typeof from === 'string' && from && typeof to === 'string' && to) {
      return [from, to];
    }
    return null;
  }
  if (edge && typeof edge === 'object') {
    const record = edge as Record<string, unknown>;
    const from = record['from'];
    const to = record['to'];
    if (typeof from === 'string' && from && typeof to === 'string' && to) {
      return [from, to];
    }
  }
  return null;
}

/**
 * 解析 `data.edges`。
 *
 * **没有声明 `edges` 时按顺序连成链**：`flow` 表达的因果链 / 流程步骤，
 * 默认读法就是「从上到下一步一步」；分镜要画分支或反馈回路时才显式声明边。
 * 显式声明了 `edges`（哪怕是空数组）就以声明为准——空数组是「就是不要连线」，
 * 不是「忘写了」。
 */
export function parseFlowEdges(value: unknown, nodes: readonly FlowNode[]): FlowEdge[] {
  if (value === undefined || value === null) {
    const chain: FlowEdge[] = [];
    for (let index = 1; index < nodes.length; index += 1) {
      chain.push({ from: nodes[index - 1]!.id, to: nodes[index]!.id });
    }
    return chain;
  }
  if (!Array.isArray(value)) {
    throw new Error('flow 组件画不出来：data.edges 必须是数组，每项形如 ["暴露", "落选"]');
  }
  const ids = new Set(nodes.map((node) => node.id));
  return value.map((edge, index) => {
    const pair = edgePair(edge);
    if (!pair) {
      throw new Error(
        `flow 组件画不出来：edges[${index}] 必须是 [from, to] 数组或含 from/to 的对象`,
      );
    }
    const [from, to] = pair;
    for (const end of [from, to]) {
      if (!ids.has(end)) {
        throw new Error(
          `flow 组件画不出来：edges[${index}] 的 ${end} 不是任何节点的 id` +
            `（已声明：${[...ids].join('、')}）`,
        );
      }
    }
    return { from, to };
  });
}
