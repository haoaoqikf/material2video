/**
 * 图表幕（任务 7.2）：柱状 / 折线 / 饼图，数据与标注全部来自分镜。
 *
 * 结构分两层，对应体检的两条判定路径：
 *
 * - **canvas 层**（`.fig-chart-plot`）：ECharts 按 `options.ts` 的纯函数
 *   逐帧重画。代价在 `charts/echarts.ts` 里写明了——DOM 探针读不到 canvas
 *   内部的文字，K7/K8 对图形内部不适用；
 * - **DOM 文本层**（数值列 / 标题 / 注写）：把关键数值**以最终值**同时输出为
 *   DOM 文本（任务 7.4）。文本显示最终值而不是随帧滚动，与数字幕 `ROLL_MIN`
 *   是同一条纪律：可读（不透明度 ≥ 0.5）的文字必须等于最终值，否则画面
 *   先展示一个错误数字再跳变。数值列的入场时刻与 canvas 的显影节奏共用
 *   同一份 `REVEAL_TIMING`，两层在同一帧出现在同一进度上。
 *
 * 组件里**没有任何默认数据**：`values` 缺失或非法在 `parseChartPoints` 抛错，
 * 「画不出来要报错」，静默空白会让缺陷拖到成片里才被发现。
 * 示意标记（`figure.schematic`）由分镜声明，画面上出现「示意」标——
 * 无来源数值不许长得像实测结果（任务 7.5）。
 */
import { useMemo, type CSSProperties } from 'react';

import { useTokenColors } from '@/charts/colors';
import { buildChartOption } from '@/charts/options';
import {
  formatValue,
  parseChartPoints,
  parseChartType,
  REVEAL_TIMING,
  revealProgresses,
  revealStartFrame,
} from '@/charts/series';
import { useFrameChart } from '@/charts/useFrameChart';
import { enterStyle, plainText, sinceBeat, useFigure, useFit } from '@/runtime/figures';

export const ChartFigure: React.FC = () => {
  const fig = useFigure();
  const data = fig.data;
  const { localFrame } = fig.state;

  const points = useMemo(() => parseChartPoints(data['values']), [data]);
  const type = useMemo(() => parseChartType(data['chart']), [data]);
  const colors = useTokenColors(fig.active);

  // 切片每帧都是新的：option 因此每帧重建，实例不携带跨帧状态
  const reveals = revealProgresses(fig.state, points.length);
  const option = useMemo(
    () => buildChartOption(type, points, reveals, colors),
    [type, points, reveals, colors],
  );
  const plotRef = useFrameChart(option, fig.active);

  const titleText = plainText(data['title']);
  const title = useFit({ level: 'title', text: titleText });
  const labels = fig.spec.labels;
  const unit = plainText(labels['unit']);
  const note = plainText(labels['note']);
  const schematic = fig.spec.schematic;

  // 数值列与 canvas 共用同一份显影节奏：两层在同一帧出现
  const revealStart = revealStartFrame(fig.state);

  return (
    <div className="fig-chart" data-chart-type={type}>
      {titleText ? (
        <h2
          className="fig-chart-title"
          data-el="title"
          data-a2v-fit="title"
          ref={title.ref}
          style={{ ...enterStyle(fig, sinceBeat(fig, 0.05)), ...title.style }}
        >
          {titleText}
        </h2>
      ) : null}
      <div className="fig-chart-plot" ref={plotRef} aria-hidden="true" />
      <ul className="fig-chart-values">
        {points.map((point, index) => {
          const seconds = fig.api.since(localFrame, revealStart + index * REVEAL_TIMING.STAGGER_FRAMES);
          const style: CSSProperties = enterStyle(fig, seconds);
          return (
            <li key={`${point.label}-${index}`} className="fig-chart-row" style={style}>
              <span className="fig-chart-row-label">{point.label}</span>
              {/* data-el 落在数值上而不是整行：探针要的是「关键数值」本身 */}
              <span className="fig-chart-row-value" data-el={`value-${index}`}>
                {formatValue(point.value)}
                {unit}
              </span>
            </li>
          );
        })}
      </ul>
      {schematic ? (
        <span className="fig-chart-schematic" data-el="schematic">
          示意
        </span>
      ) : null}
      {note ? (
        <p className="fig-chart-note" data-el="note" style={enterStyle(fig, sinceBeat(fig, 0.32))}>
          {note}
        </p>
      ) : null}
    </div>
  );
};
