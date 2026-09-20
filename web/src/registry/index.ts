/**
 * 视觉组件注册表：`kind` → 组件、它认识的标注键、适用条目区间与默认场景映射。
 *
 * 注册表是**组件选择面**的单一真源：AI 只决定「第几幕用哪个 kind」，
 * 不去写画面代码。因此这里的三件事必须能被两侧读到——
 * 渲染层按 `kind` 取组件，校验器按 `labels` 提醒写了却不画的标注键，
 * 文档与 `scripts/a2v/catalog.py` 的组件表由它生成（任务 9.1/9.2）。
 *
 * 与旧实现的关系：旧注册表在 `assets/figures.js` 的 `define(...)` 里，
 * 服务端镜像在 `scripts/a2v/catalog.py`。两边漂移过一次（图节点只允许 `{id}`），
 * 症状是**整份分镜在一条路径上画不出来**而另一条说它合法。
 * 因此这里保留 `labels` 与 `items`，作为生成与对照的输入：
 * `labels` 与 `items` 逐项等于 `catalog.py` 的 `FIGURE_CATALOG`
 * （`tests/test_web_registry.py` 会对照，不靠人记）。
 */
import type { FC } from 'react';

import { BalanceFigure } from '@/components/Balance';
import { ChartFigure } from '@/components/Chart';
import { ExchangeFigure } from '@/components/Exchange';
import { FlowFigure } from '@/components/Flow';
import { GapFigure } from '@/components/Gap';
import { IcebergFigure } from '@/components/Iceberg';
import { LoopFigure } from '@/components/Loop';
import { NumberFigure } from '@/components/Number';
import { StairsFigure } from '@/components/Stairs';
import { VersusFigure } from '@/components/Versus';

export interface FigureDefinition {
  kind: string;
  /**
   * 该组件认识的标注键（`figure.labels` / `annotations` 的键）。
   * 声明了却不画的键会让标签空着，校验器据此提醒。
   */
  labels: readonly string[];
  /** 建议的条目数区间（items / nodes）；null 表示不限制。 */
  items: readonly [number, number] | null;
  /** 适合表达什么，用于错误信息与文档。 */
  summary: string;
  /** 组件本体。 */
  Component: FC;
}

export const FIGURES: Record<string, FigureDefinition> = {
  balance: {
    kind: 'balance',
    labels: ['leftPan', 'rightPan'],
    items: null,
    summary: '一边重一边轻，随后证明重的那个是空壳',
    Component: BalanceFigure,
  },
  gap: {
    kind: 'gap',
    labels: ['assumption', 'fact', 'dropLabel', 'noDropLabel'],
    items: null,
    summary: '量出真正失去了多少：一侧从满到空，另一侧从头就没有',
    Component: GapFigure,
  },
  iceberg: {
    kind: 'iceberg',
    labels: ['surface'],
    items: [1, 3],
    summary: '看得见的一角与看不见的主体不是一回事',
    Component: IcebergFigure,
  },
  loop: {
    kind: 'loop',
    labels: ['gauge'],
    items: [3, 6],
    summary: '循环往复，每转一圈积累一点',
    Component: LoopFigure,
  },
  stairs: {
    kind: 'stairs',
    labels: ['axis', 'before', 'after'],
    items: [2, 5],
    summary: '次数累积带来的位置变化，并在末段翻转视角',
    Component: StairsFigure,
  },
  exchange: {
    kind: 'exchange',
    labels: ['leftNode', 'rightNode'],
    items: null,
    summary: '双向关系，两个端点互相选择',
    Component: ExchangeFigure,
  },
  versus: {
    kind: 'versus',
    labels: ['left', 'right', 'note'],
    items: null,
    summary: '两种反应并排，箭头指出该从哪边转向哪边',
    Component: VersusFigure,
  },
  number: {
    kind: 'number',
    labels: [],
    items: null,
    summary: '按帧递增显示数值，并展示标签与说明',
    Component: NumberFigure,
  },
  chart: {
    kind: 'chart',
    labels: ['unit', 'note'],
    items: [2, 6],
    summary: '柱状/折线/饼图：数据序列随帧显影，关键数值同步输出为 DOM 文本',
    Component: ChartFigure,
  },
  flow: {
    kind: 'flow',
    labels: [],
    items: [2, 6],
    summary: '因果链/流程步骤：dagre 分层布局，自上而下逐步连线，节点文字按实测宽度定形',
    Component: FlowFigure,
  },
};

/** 分镜没有声明 `figure.kind` 时，按场景类型取用的默认组件。 */
export const DEFAULT_KIND_BY_SCENE: Record<string, string> = {
  title: 'balance',
  quote: 'gap',
  comparison: 'versus',
  list: 'iceberg',
  diagram: 'loop',
  timeline: 'stairs',
  conclusion: 'exchange',
  number: 'number',
  chart: 'chart',
};

export function figureDefinition(kind: string): FigureDefinition | undefined {
  return FIGURES[kind];
}

export function knownKinds(): string[] {
  return Object.keys(FIGURES).sort();
}

/**
 * 算出这一幕实际会用到哪个组件：分镜声明优先，否则按场景类型取默认。
 *
 * 两处都取不到时返回 null，由调用方报错——「画不出来要报错」是渲染层的职责，
 * 不是「类型不在清单里就画个空白」。
 */
export function resolveKind(
  sceneType: string,
  data: Record<string, unknown>,
): string | null {
  const figure = data['figure'];
  if (figure && typeof figure === 'object' && !Array.isArray(figure)) {
    const declared = (figure as Record<string, unknown>)['kind'];
    if (typeof declared === 'string' && declared.trim()) {
      return declared.trim();
    }
  }
  return DEFAULT_KIND_BY_SCENE[sceneType] ?? null;
}
