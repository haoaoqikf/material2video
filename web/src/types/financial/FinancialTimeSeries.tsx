/**
 * 金融时间序列 composition 入口：组装坐标求值、曲线绘制、覆盖层与逐帧布局校验。
 *
 * 曲线与坐标求值、数值/文本度量与折线裁剪校验在 `./financial/chart.tsx`；
 * 顶部/底部覆盖层、整体居中与安全区（字幕避让）校验在 `./financial/overlay.tsx`。
 * 本文件保留 composition 与 props 契约，并逐一重导出拆分前的公开名字。
 */
import { useLayoutEffect, useRef, useState } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import {
  HEIGHT, LAYOUT_BOUNDS, PLOT, WIDTH,
  assertChartPlotUnclipped, assertEndpointAboveLine, chartGeometry, compactValue, financialView, measuredTextWidth,
  type FinancialTimeSeriesProps,
} from './chart';
import {
  BottomOverlay, TopOverlay, assertContentLayerWithinBounds, assertOverlaySafeArea, canvasCenterOffset, overlayCopy,
} from './overlay';

export type { ChartPoint, FinancialPlan, FinancialTimeSeriesProps } from './chart';
export { assertFinancialPlotUnclipped, financialView, framePosition, revealedValueRange, valueTickDecimals } from './chart';
export { canvasCenterOffset } from './overlay';

export function FinancialTimeSeries(props: FinancialTimeSeriesProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const contentLayerRef = useRef<SVGGElement>(null);
  const centeredLayoutKeyRef = useRef<string | null>(null);
  const checkedLayoutKeyRef = useRef<string | null>(null);
  const [contentOffsetY, setContentOffsetY] = useState(0);
  const frame = useCurrentFrame();
  const { request, prices, plan } = props;
  const investment = request.investment ?? { year: Number(request.displayRange[0].slice(0, 4)), principal: 1_000_000 };
  const view = financialView(frame, prices.points, plan, investment, prices.fx?.points);
  const { windowStart, latest, visiblePoints, minValue, maxValue, ticks } = view;
  const copy = overlayCopy(props, view, investment);
  const { displayName, gainColor, contentLayoutKey } = copy;
  const graphTop = PLOT.top;
  const { xForDate, yForValue, linePoints, endpointX, endpointY } = chartGeometry(view, minValue, maxValue);
  const showEndpoint = latest !== null && windowStart <= latest.date;

  useLayoutEffect(() => {
    document.documentElement.style.setProperty('--m2v-width', `${WIDTH}px`);
    document.documentElement.style.setProperty('--m2v-height', `${HEIGHT}px`);
    document.documentElement.dataset.m2vTheme = 'dark';
    const svg = svgRef.current;
    const contentLayer = contentLayerRef.current;
    if (!svg || !contentLayer) return;
    if (centeredLayoutKeyRef.current !== contentLayoutKey) {
      const centeredOffset = canvasCenterOffset(contentLayer.getBBox());
      centeredLayoutKeyRef.current = contentLayoutKey;
      if (Math.abs(centeredOffset - contentOffsetY) > 0.01) {
        setContentOffsetY(centeredOffset);
        return;
      }
    }
    if (checkedLayoutKeyRef.current !== contentLayoutKey) {
      assertContentLayerWithinBounds(contentLayer);
      checkedLayoutKeyRef.current = contentLayoutKey;
    }
    assertChartPlotUnclipped(svg, contentLayer);
    if (frame % 5 === 0 || frame === props.durationInFrames - 1) {
      assertOverlaySafeArea(svg);
      assertEndpointAboveLine(svg);
    }
  }, [frame, contentOffsetY, contentLayoutKey]);

  return <AbsoluteFill style={{ background: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif' }} data-m2v-financial="line">
    <svg ref={svgRef} width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" data-m2v-financial="line" aria-label={`${displayName} 假设投资价值演变图`} data-m2v-window-start={windowStart} data-m2v-window-end={view.windowEnd}>
      {/* 裁剪和折线共用局部坐标，引用元素的整体变换会同时移动两者。 */}
      <defs><clipPath id="financial-plot" clipPathUnits="userSpaceOnUse"><rect x={PLOT.left} y={graphTop} width={PLOT.right - PLOT.left} height={PLOT.bottom - graphTop} /></clipPath></defs>
      <g ref={contentLayerRef} data-m2v-content-layer="true" data-m2v-content-offset-y={contentOffsetY} transform={`translate(0 ${contentOffsetY})`}>
      <TopOverlay copy={copy}/>
      {Array.from({ length: 5 }, (_, index) => {
        const value = minValue + ((maxValue - minValue) * index) / 4;
        const y = yForValue(value);
        const label = compactValue(value);
        const labelWidth = PLOT.left - 14 - LAYOUT_BOUNDS.left;
        const estimatedLabelWidth = measuredTextWidth(label, 14);
        return <g key={`grid-${index}`}>
          <line x1={PLOT.left} x2={PLOT.right} y1={y} y2={y} stroke="#253247" strokeWidth="1" />
          <text data-m2v-value-axis-label="true" x={PLOT.left - 14} y={y + 9} textAnchor="end" fill="#8b9ab0" fontSize="14"
            textLength={estimatedLabelWidth > labelWidth ? labelWidth : undefined}
            lengthAdjust={estimatedLabelWidth > labelWidth ? 'spacingAndGlyphs' : undefined}>{label}</text>
        </g>;
      })}
      {ticks.map(({ date: tickDate, label, opacity }) => {
        const x = xForDate(tickDate);
        const labelHalfWidth = label.length * 9;
        const labelX = Math.max(LAYOUT_BOUNDS.left + labelHalfWidth, Math.min(x, LAYOUT_BOUNDS.right - labelHalfWidth));
        return <g key={`month-${tickDate}`} opacity={opacity}><line x1={x} x2={x} y1={graphTop} y2={PLOT.bottom} stroke="#172235" /><text data-m2v-axis-label="true" x={labelX} y={PLOT.bottom + 46} textAnchor="middle" fill="#9ba9bc" fontSize="30">{label}</text></g>;
      })}
      <line x1={PLOT.left} x2={PLOT.left} y1={graphTop} y2={PLOT.bottom} stroke="#53627a" />
      <line x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} stroke="#53627a" />
      {view.linePoints.length > 0 && <g clipPath="url(#financial-plot)">
        <polyline fill="none" stroke={gainColor} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round"
          points={linePoints} data-m2v-visible-value-points={visiblePoints.length} />
      </g>}
      {showEndpoint &&
        <circle data-m2v-financial-endpoint="true" cx={endpointX} cy={endpointY} r="8" fill={gainColor} stroke="#09213a" strokeWidth="3" />}
      <BottomOverlay copy={copy}/>
      </g>
    </svg>
  </AbsoluteFill>;
}
