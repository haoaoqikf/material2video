/**
 * `flow`（因果链、流程步骤）：自上而下的分层流程图，节点与连线全部自绘 SVG
 * （任务 8.2 / 8.3）。这是本变更新增的关系流程类组件——旧组件库里没有它的前身，
 * 结构上的对应物是分镜的 `diagram` 场景类型（`nodes` + `edges`）。
 *
 * ## 布局是纯函数（任务 8.1）
 *
 * 节点位置由 `@/flow/layout`（dagre 的纯函数外壳）算出：输入是「每个节点的盒子
 * 尺寸 + 谁连谁」，输出是坐标。同一份输入调用两次逐值相同，没有测量、没有拟合，
 * 布局结果按输入记忆化、逐帧复用。
 *
 * ## 盒子尺寸由实测文字决定（K8 的硬判定）
 *
 * 与飞轮节点同一条教训：先写死盒子再把字塞进去，文字必然穿出容器，
 * 而 K8 量到之前谁也不会发现。这里反过来——**盒子的宽高由实测文字宽度反推**
 * （canvas 量尺，`useTextMeasure`），量尺与帧号无关，量一次、缓存、逐帧复用。
 * 文字元素声明 `data-a2v-inside=".flow-node-box"`，K8 据此判定文字有没有穿出
 * 节点盒子；盒子与文字同属节点 `<g>` 的直接子节点（探针在父节点里找容器）。
 *
 * ## 连线逐帧描边（任务 8.3）
 *
 * 连线是折线（dagre 的点串直接连），**总长度是解析值**（各段长度之和，
 * `@/flow/edges`），在布局确定时算好并随布局缓存。每帧只把帧号换算成进度，
 * 交给 `drawPathStyle` 原语写 `stroke-dasharray` / `stroke-dashoffset`——
 * 不调用 `getTotalLength()`，每帧不做任何实时测量。
 *
 * ## 焦点跟叙述走
 *
 * 节点按序入场，焦点（`data-a2v-state="focus"`）始终落在最新激活的节点上，
 * 交接拆成连续量（`--a2v-focus-mix`）：新旧节点在 handover 帧的混合比例相加
 * 恒为 1，与飞轮的连续交接同一条纪律——任何一帧仍然只有一个焦点，换手无跳变。
 */
import { useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type FC } from 'react';

import { balanceChars } from '@/components/Loop';
import { edgeGeometry, type FlowEdgeGeometry } from '@/flow/edges';
import { layoutFlow, type FlowLayout } from '@/flow/layout';
import { parseFlowEdges, parseFlowNodes } from '@/flow/parse';
import { SPRINGS, spring } from '@/runtime/motion';
import {
  beat,
  clamp,
  drawPathStyle,
  plainText,
  svgOpacity,
  svgTransform,
  useFigure,
  useFit,
  useFontsReady,
  useTextMeasure,
} from '@/runtime/figures';

/* ---------------- 节点盒子的设计常量 ---------------- */

/** 节点文字字号：令牌 `--a2v-ink-value`（预设下 = `--a2v-size-body` = 40px，
 * 未启用预设时样式表兜底 48px）。与飞轮节点同一来源；字号本身由样式表给，
 * 这里只需要行高参与盒子高度的计算——字宽由量尺实测。 */
export const FLOW_NODE_FONT_PX = 40;

/** 行高倍数与参与几何计算的行高（px）：与飞轮节点同一套取值
 * （`1.15 × 40px`，浏览器解析后交给几何计算的是 46px）。 */
export const FLOW_NODE_LINE_PX = 46;

/** 节点盒子的内边距：水平 / 垂直各留出呼吸空间。
 * 大于令牌 `--fig-surface-pad`（16px）：盒子是矩形，文字离边框的视觉距离
 * 需要盖住字形本身的墨迹边。 */
export const FLOW_NODE_PAD_X = 28;
export const FLOW_NODE_PAD_Y = 22;

/** 单行文字的宽度上限（px，量尺坐标）：超过就折行。折行按字数均衡切开
 * （与飞轮的 `balanceChars` 同一份实现），而不是挤在一行里缩字号。 */
export const FLOW_NODE_MAX_TEXT_WIDTH = 320;

/** 节点盒子的圆角。 */
export const FLOW_NODE_RX = 18;

/** 画布：布局结果等比缩放居中到这里。竖屏安全区内可用的图形高度约 900px，
 * 与飞轮（888×560）、阶梯等共用 888px 的图形宽度。 */
export const FLOW_VIEW = { W: 888, H: 920 } as const;

/** 布局放大倍数的上限：两三个节点的小图不放大到字号失控
 * （节点文字始终比幕标题大半档即可，超过会倒置层级）。 */
export const FLOW_MAX_SCALE = 1.5;

/** 一个节点的盒子尺寸与断行结果：由实测文字宽度算出，与帧号无关。 */
export interface FlowNodeSize {
  lines: string[];
  width: number;
  height: number;
  /** 是否量到了宽度；false 是降级路径（单行原文 + 按字数估宽），画面仍然成立 */
  measured: boolean;
}

/** 降级用的估宽：每个字符按一个全角位（1em）估。CJK 文案几乎精确，
 * 拉丁文案偏宽——偏宽只会让盒子大一圈，不会穿帮；偏窄才会。 */
function estimatedWidth(text: string): number {
  return Array.from(text).length * FLOW_NODE_FONT_PX;
}

/**
 * 由实测文字宽度算出节点盒子。
 *
 * `widthOf` 收一个候选行、返回它在真实字体下的宽度（canvas 量尺做）；
 * 量不到（0 / null / NaN）时走降级：单行原文 + 按字数估宽，与飞轮同一纪律
 * ——降级不是抛错，画面必须仍然成立，等量到之后再切过去。
 */
export function flowNodeSize(
  label: string,
  widthOf: (line: string) => number | null | undefined,
): FlowNodeSize {
  const chars = Array.from(label);
  if (!chars.length) {
    // 空标签：退到一个最小的空盒子（不抛错，让分镜的问题在体检里暴露）
    return {
      lines: [''],
      width: FLOW_NODE_PAD_X * 2,
      height: FLOW_NODE_PAD_Y * 2,
      measured: false,
    };
  }
  const fallback: FlowNodeSize = {
    lines: [label],
    width: estimatedWidth(label) + FLOW_NODE_PAD_X * 2,
    height: FLOW_NODE_LINE_PX + FLOW_NODE_PAD_Y * 2,
    measured: false,
  };
  const full = widthOf(label);
  if (!full || !Number.isFinite(full)) {
    return fallback;
  }
  const lineCount = Math.max(1, Math.ceil(full / FLOW_NODE_MAX_TEXT_WIDTH));
  const lines = lineCount === 1 ? [label] : balanceChars(chars, lineCount);
  let widest = 0;
  for (const line of lines) {
    const width = widthOf(line);
    if (!width || !Number.isFinite(width)) {
      return fallback;
    }
    widest = Math.max(widest, width);
  }
  return {
    lines,
    width: widest + FLOW_NODE_PAD_X * 2,
    height: lines.length * FLOW_NODE_LINE_PX + FLOW_NODE_PAD_Y * 2,
    measured: true,
  };
}

/** 节点文字的 tspan 落点：多行时按行盒中心对称铺开（与飞轮同一算法）。 */
export function flowTextLines(
  size: FlowNodeSize,
  cx: number,
  cy: number,
): Array<{ text: string; x: number; y: number }> {
  const lines = size.lines;
  return lines.map((line, index) => ({
    text: line,
    x: cx,
    y: lines.length > 1 ? cy + (index - (lines.length - 1) / 2) * FLOW_NODE_LINE_PX : cy,
  }));
}

/** 把布局缩放居中到画布：返回 `<g>` 的 transform 串。 */
export function flowViewTransform(layout: FlowLayout): string {
  const scale = Math.min(
    FLOW_VIEW.W / Math.max(layout.width, 1),
    FLOW_VIEW.H / Math.max(layout.height, 1),
    FLOW_MAX_SCALE,
  );
  const tx = (FLOW_VIEW.W - layout.width * scale) / 2;
  const ty = (FLOW_VIEW.H - layout.height * scale) / 2;
  return `translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${scale.toFixed(4)})`;
}

/** 只在结果不同时更新 state：逐帧重建对象会让整棵子树每帧都重渲染。 */
function sameSizes(a: FlowNodeSize[] | null, b: FlowNodeSize[]): boolean {
  if (!a || a.length !== b.length) {
    return false;
  }
  return a.every((size, index) => {
    const other = b[index]!;
    return (
      size.width === other.width &&
      size.height === other.height &&
      size.measured === other.measured &&
      size.lines.join('\u0000') === other.lines.join('\u0000')
    );
  });
}

export const FlowFigure: FC = () => {
  const fig = useFigure();
  const { localFrame } = fig.state;
  const data = fig.data;

  const nodes = useMemo(() => parseFlowNodes(data['nodes']), [data]);
  const edges = useMemo(() => parseFlowEdges(data['edges'], nodes), [data, nodes]);
  // 节点与连线的稳定签名：下游 memo / effect 只认它们（数组本身每帧都是新对象）
  const nodesKey = nodes.map((node) => `${node.id}\u0001${node.label}`).join('\u0000');
  const edgesKey = edges.map((edge) => `${edge.from}\u0001${edge.to}`).join('\u0002');
  const nodeCount = nodes.length;

  const titleText = plainText(data['title']);
  const title = useFit({ level: 'title', text: titleText });

  /* ---- 实测文字宽度：本组件唯一的跨帧状态（与飞轮同一套手法） ---- */
  const measure = useTextMeasure();
  const fontsReady = useFontsReady();
  const textRefs = useRef<Array<SVGTextElement | null>>([]);
  const [attached, setAttached] = useState(0);
  const [sizes, setSizes] = useState<FlowNodeSize[] | null>(null);

  const attachText = useMemo(
    () =>
      Array.from(
        { length: nodeCount },
        (_unused: unknown, index: number) => (element: SVGTextElement | null) => {
          textRefs.current[index] = element;
          setAttached((count) => count + 1);
        },
      ),
    [nodeCount],
  );

  useLayoutEffect(() => {
    const next = nodes.map((node, index) =>
      // 字体取该元素的计算样式（量尺内部做的）；元素还没挂上就量不到 → 降级
      flowNodeSize(node.label, (line) => measure(textRefs.current[index] ?? null, line)),
    );
    setSizes((previous) => (sameSizes(previous, next) ? previous : next));
    /*
     * 只在「量的东西」可能变了的时候重量：文案、字体就绪、节点数、ref 挂载。
     * 依赖用稳定签名而不是 `nodes` 本身——它每帧都是新数组，进去就等于
     * 逐帧重量，逐帧重排恰恰是「帧驱动」要消灭的东西。
     */
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [measure, fontsReady, nodesKey, nodeCount, attached]);

  /* ---- 布局：纯函数，记忆化后逐帧复用（任务 8.1） ---- */
  const sizesKey = sizes
    ? sizes.map((size) => `${size.width.toFixed(2)}x${size.height.toFixed(2)}`).join('\u0003')
    : 'pending';
  const layout = useMemo(() => {
    return layoutFlow(
      nodes.map((node, index) => {
        const size = sizes ? sizes[index] : undefined;
        return {
          id: node.id,
          width: size ? size.width : estimatedWidth(node.label) + FLOW_NODE_PAD_X * 2,
          height: size ? size.height : FLOW_NODE_LINE_PX + FLOW_NODE_PAD_Y * 2,
        };
      }),
      edges,
    );
    // eslint 依赖用稳定签名：nodes / edges / sizes 每帧都是新数组
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodesKey, edgesKey, sizesKey, nodeCount]);

  /* ---- 连线几何：布局确定时算一次（含解析长度），逐帧只算进度（任务 8.3） ---- */
  const geometries = useMemo(() => {
    return layout.edges.map((edge) => edgeGeometry(edge.points));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  /* ---- 节点索引：连线按端点取入场时刻 ---- */
  const indexOfId = useMemo(() => {
    const map = new Map<string, number>();
    nodes.forEach((node, index) => map.set(node.id, index));
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodesKey, nodeCount]);

  /* ---- 逐帧时序：节点依次入场，焦点连续交接，连线在两端之间画出来 ---- */
  const enterStart = beat(fig, 0.1);
  const windowFrames = Math.max(beat(fig, 0.72) - enterStart, nodeCount * 3);
  const stagger = clamp(windowFrames / Math.max(nodeCount, 1), 3, 14);
  const startAt = (index: number) => enterStart + index * stagger;
  const activate = (index: number) =>
    clamp((localFrame - startAt(index)) / Math.max(stagger, 1), 0, 1);

  return (
    <>
      {titleText ? (
        <h2
          className="section-title"
          data-el="title"
          data-a2v-fit="title"
          ref={title.ref}
          style={title.style}
        >
          {titleText}
        </h2>
      ) : null}
      <svg className="fig fig-flow" viewBox={`0 0 ${FLOW_VIEW.W} ${FLOW_VIEW.H}`} aria-hidden="true">
        <g transform={flowViewTransform(layout)}>
          {/*
            连线先画（在节点的下层）：线从源节点的边框出发，节点盒子入场后
            盖住它的起点，交界处因此不需要精确的贴边计算。
          */}
          <g data-el="edges">
            {layout.edges.map((edge, index) => {
              const geo: FlowEdgeGeometry = geometries[index]!;
              const sourceIndex = indexOfId.get(edge.from) ?? 0;
              const drawStart = startAt(sourceIndex);
              const drawFrames = stagger * 1.6;
              const draw = drawPathStyle(
                fig.api.progress(localFrame, drawStart, drawFrames),
                geo.length,
              );
              const arrowIn = clamp((localFrame - drawStart - drawFrames * 0.8) / (drawFrames * 0.2), 0, 1);
              return (
                <g key={`${edge.from}-${edge.to}-${index}`}>
                  <path
                    className="flow-edge ln ln-soft"
                    data-edge={String(index)}
                    d={geo.path}
                    strokeDasharray={draw.strokeDasharray}
                    strokeDashoffset={draw.strokeDashoffset}
                    style={{ opacity: draw.opacity }}
                  />
                  <polygon
                    className="flow-arrow"
                    data-arrow={String(index)}
                    points={geo.arrow.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ')}
                    opacity={svgOpacity(arrowIn)}
                  />
                </g>
              );
            })}
          </g>
          <g data-el="nodes">
            {nodes.map((node, index) => {
              const size = sizes ? sizes[index] : undefined;
              const width = size ? size.width : estimatedWidth(node.label) + FLOW_NODE_PAD_X * 2;
              const height = size ? size.height : FLOW_NODE_LINE_PX + FLOW_NODE_PAD_Y * 2;
              const laid = layout.nodes[index]!;
              const cx = laid.x;
              const cy = laid.y;

              // 入场：弹性缩放 + 落下，与飞轮节点同一配方
              const enterP = spring(fig.api.since(localFrame, startAt(index)), SPRINGS['enter']);
              const nodeScale = fig.api.range(enterP, 0.94, 1, { clamp: false });

              // 焦点连续交接：a_i × (1 − a_{i+1})，相邻两者的混合比例相加恒为 1
              const activation = activate(index);
              const nextActivation = index + 1 < nodeCount ? activate(index + 1) : 0;
              const focusMix = clamp(activation * (1 - nextActivation), 0, 1);
              const nodeState = focusMix > 0 ? 'focus' : 'rest';

              const textLines = size
                ? flowTextLines(size, cx, cy)
                : [{ text: node.label, x: cx, y: cy }];

              return (
                <g
                  key={node.id}
                  data-node={String(index)}
                  transform={svgTransform(
                    cx * (1 - nodeScale),
                    cy * (1 - nodeScale) + (1 - fig.api.clamp(enterP, 0, 1)) * 24,
                    0,
                    nodeScale,
                  )}
                  opacity={svgOpacity(fig.api.clamp(enterP, 0, 1))}
                >
                  <rect
                    className="flow-node-box a2v-surface"
                    data-a2v-state={nodeState}
                    x={(cx - width / 2).toFixed(2)}
                    y={(cy - height / 2).toFixed(2)}
                    width={width.toFixed(2)}
                    height={height.toFixed(2)}
                    rx={FLOW_NODE_RX}
                    ry={FLOW_NODE_RX}
                    style={
                      focusMix > 0
                        ? ({ '--a2v-focus-mix': focusMix.toFixed(4) } as CSSProperties)
                        : undefined
                    }
                  />
                  <text
                    ref={attachText[index]}
                    className="flow-node-text a2v-label"
                    data-a2v-state={nodeState}
                    data-a2v-inside=".flow-node-box"
                    x={cx}
                    y={cy}
                  >
                    {textLines.map((line, lineIndex) => (
                      <tspan key={lineIndex} x={line.x} y={line.y}>
                        {line.text}
                      </tspan>
                    ))}
                  </text>
                </g>
              );
            })}
          </g>
        </g>
      </svg>
    </>
  );
};
