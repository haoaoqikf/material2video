/**
 * 视觉组件注册表：`kind` → 组件、它认识的标注键、容量、适用场景与默认场景映射。
 *
 * **元数据的唯一真源是 `registry.json`**（本目录下）：组件集合、标注键、容量、
 * 适用场景类型与默认映射都声明在那里，两侧直接消费——
 *
 * - 渲染层（本文件）把 JSON 条目与组件本体接起来；
 * - 校验器读**生成物** `scripts/a2v/catalog.py`（由 `scripts/sync_catalog.py`
 *   从同一份 JSON 生成，手改派生文件会被机检判为落后）；
 * - 分镜 schema 的 `kind` 取值读生成物 `web/src/schema/figureKinds.ts`；
 * - 组件目录文档的组件表同样是生成物。
 *
 * 与旧实现的关系：旧注册表在 `assets/figures.js` 的 `define(...)` 里，
 * 服务端镜像在 `scripts/a2v/catalog.py`。两边漂移过一次（图节点只允许 `{id}`），
 * 症状是**整份分镜在一条路径上画不出来**而另一条说它合法。本变更加上生成机制后，
 * 这类漂移在 `tests/test_web_registry.py` 的「重新生成无差异」断言上失败，
 * 不再依赖人记。
 */
import type { FC } from 'react';

import registryData from './registry.json';
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

/** registry.json 的一条声明（不含组件本体）。 */
export interface FigureEntry {
  kind: string;
  /** 该组件认识的标注键（`figure.labels` / `annotations` 的键）。 */
  labels: readonly string[];
  /** 建议的条目数区间（items / nodes / values）；null 表示不限制。 */
  items: readonly [number, number] | null;
  /** 容量在文档里的量词（「侧」「栏」「节点」…）。 */
  capacityUnit: string;
  /** 适用场景类型（storyboard 的 scene.type）。 */
  sceneTypes: readonly string[];
  /** 适合表达什么，用于错误信息与文档。 */
  summary: string;
  /** false = 规划中的组件：文档照登，渲染层没有它。 */
  implemented: boolean;
  /** 组件实现源码（相对 web/src/）。标注键机检与溯源用它。 */
  source: string;
  /** 画面主体画在 canvas 上：K7/K8 对图形内部不适用。 */
  canvasDrawn: boolean;
  /** 会把 `figure.schematic` 自动画成「示意」标。 */
  schematicMark: boolean;
}

export interface FigureDefinition extends FigureEntry {
  /** 组件本体。规划中的组件没有它（undefined）。 */
  Component?: FC;
}

/** kind → 组件本体。只有已实现的组件在这里；与 registry.json 的对照由测试守住。 */
const COMPONENTS: Record<string, FC> = {
  balance: BalanceFigure,
  gap: GapFigure,
  iceberg: IcebergFigure,
  loop: LoopFigure,
  stairs: StairsFigure,
  exchange: ExchangeFigure,
  versus: VersusFigure,
  number: NumberFigure,
  chart: ChartFigure,
  flow: FlowFigure,
};

function toDefinition(entry: FigureEntry): FigureDefinition {
  const component = COMPONENTS[entry.kind];
  if (entry.implemented && !component) {
    throw new Error(
      `注册表条目 ${entry.kind} 声明 implemented，但渲染层没有接上组件本体` +
        `（web/src/registry/index.ts 的 COMPONENTS 缺少它）`,
    );
  }
  return {
    ...entry,
    items: entry.items === null ? null : [entry.items[0]!, entry.items[1]!],
    Component: component,
  };
}

export const FIGURES: Record<string, FigureDefinition> = Object.fromEntries(
  /*
   * JSON 导入把 `items` 推断成 `number[]`，与 `readonly [number, number]` 对不上；
   * 注册表的形状由 `tests/test_web_registry.py` 与 vitest 的注册表测试共同守住，
   * 这里经由 unknown 收窄是声明而非绕过。
   */
  (registryData.figures as unknown as FigureEntry[]).map((entry) => [
    entry.kind,
    toDefinition(entry),
  ]),
);

/** 分镜没有声明 `figure.kind` 时，按场景类型取用的默认组件。 */
export const DEFAULT_KIND_BY_SCENE: Record<string, string> = registryData.defaultKindByScene;

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
