/**
 * 金融时间序列 composition 入口：编辑式顶部、去轴化图表与逐帧布局校验。
 *
 * 曲线与坐标求值、数值/文本度量与折线裁剪校验在 `./financial/chart.tsx`；
 * 顶部/底部覆盖层、整体居中与安全区（字幕避让）校验在 `./financial/overlay.tsx`。
 * 本文件保留 composition 与 props 契约，并逐一重导出拆分前的公开名字。
 */
import { useLayoutEffect, useRef, useState } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import {
  FONT_STACK, GRID_COLOR, HEIGHT, LAYOUT_BOUNDS, PLOT, TEXT_PRIMARY, TEXT_SECONDARY, VALUE_AXIS_FONT_SIZE, VALUE_AXIS_LABEL_X, WIDTH,
  assertChartPlotUnclipped, assertEndpointAboveLine, axisTickDecimals, axisTickLabel, axisUnit, chartGeometry,
  financialView, measuredTextWidth,
  type FinancialTimeSeriesProps,
} from './chart';
import {
  BottomOverlay, TopOverlay, assertContentLayerWithinBounds, assertOverlaySafeArea, canvasCenterOffset, overlayCopy,
} from './overlay';

export type { ChartPoint, FinancialPlan, FinancialTimeSeriesProps } from './chart';
export { assertFinancialPlotUnclipped, financialView, framePosition, revealedValueRange, valueTickDecimals } from './chart';
export { canvasCenterOffset } from './overlay';

const NOISE_BACKGROUND = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E")`;

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
  const { xForDate, yForValue, linePoints, trendPath, principalY, endpointX, endpointY } = chartGeometry(
    view, minValue, maxValue, investment.principal,
  );
  const showEndpoint = latest !== null && windowStart <= latest.date;
  const unit = axisUnit(maxValue);
  const tickDecimals = axisTickDecimals(minValue, maxValue);
  const axisUnitText = unit.unit ? `${unit.unit}元` : '元';
  // 结尾冻结段停止呼吸；推进末 15 帧平滑收回，避免与终幕首帧之间跳变。
  const endingStart = plan.segments.find((segment) => segment.kind === 'ending')!.frames[0];
  const breathProgress = Math.max(0, Math.min(1, (endingStart - 1 - frame) / 15));
  const endpointRadius = 7;
  const haloRadius = 14 * (1 + 0.06 * breathProgress * (0.5 + 0.5 * Math.sin(frame / 7)));
  const glowX = 50 + Math.sin(frame / 90) * 3;
  const glowY = 22 + Math.cos(frame / 110) * 2;

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

  return <AbsoluteFill style={{
    backgroundColor: '#0A0A0B',
    backgroundImage: `radial-gradient(ellipse 120% 72% at ${glowX}% ${glowY}%, #17171B 0%, #0D0D10 46%, #08080A 100%)`,
    color: TEXT_PRIMARY, fontFamily: FONT_STACK,
  }} data-m2v-financial="line">
    <div style={{
      position: 'absolute', inset: 0, backgroundImage: NOISE_BACKGROUND, backgroundSize: '140px 140px',
      opacity: 0.03,
    }} />
    <svg ref={svgRef} width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" data-m2v-financial="line" aria-label={`${displayName} 假设投资价值演变图`} data-m2v-window-start={windowStart} data-m2v-window-end={view.windowEnd}>
      {/* 裁剪和折线共用局部坐标，引用元素的整体变换会同时移动两者。 */}
      <defs>
        <clipPath id="financial-plot" clipPathUnits="userSpaceOnUse"><rect x={PLOT.left} y={graphTop} width={PLOT.right - PLOT.left} height={PLOT.bottom - graphTop} /></clipPath>
      </defs>
      <g ref={contentLayerRef} data-m2v-content-layer="true" data-m2v-content-offset-y={contentOffsetY} transform={`translate(0 ${contentOffsetY})`}>
      <TopOverlay copy={copy}/>      {Array.from({ length: 3 }, (_, index) => {
        const value = minValue + ((maxValue - minValue) * index) / 2;
        const y = yForValue(value);
        const label = axisTickLabel(value, unit.divisor, tickDecimals);
        const labelWidth = VALUE_AXIS_LABEL_X - LAYOUT_BOUNDS.left;
        const estimatedLabelWidth = measuredTextWidth(label, VALUE_AXIS_FONT_SIZE);
        return <g key={`grid-${index}`}>
          <line x1={PLOT.left} x2={PLOT.right} y1={y} y2={y} stroke={GRID_COLOR} strokeWidth="1" />
          <text data-m2v-value-axis-label="true" x={VALUE_AXIS_LABEL_X} y={y + 7} textAnchor="end" fill={TEXT_SECONDARY} fontSize={VALUE_AXIS_FONT_SIZE}
            textLength={estimatedLabelWidth > labelWidth ? labelWidth : undefined}
            lengthAdjust={estimatedLabelWidth > labelWidth ? 'spacingAndGlyphs' : undefined}>{label}</text>
        </g>;
      })}
      <text data-m2v-value-axis-unit="true" x={VALUE_AXIS_LABEL_X} y={graphTop - 22} textAnchor="end" fill={TEXT_SECONDARY} fontSize="20">{axisUnitText}</text>
      {ticks.map(({ date: tickDate, label, opacity }) => {
        const x = xForDate(tickDate);
        const labelHalfWidth = measuredTextWidth(label, 28) / 2;
        // 留 2px 余量，避免估算字体宽度与实际字形包围盒在安全区边缘互相打架。
        const labelX = Math.max(LAYOUT_BOUNDS.left + labelHalfWidth + 2, Math.min(x, LAYOUT_BOUNDS.right - labelHalfWidth - 2));
        return <text key={`year-${tickDate}`} opacity={opacity} data-m2v-axis-label="true" x={labelX} y={PLOT.bottom + 44} textAnchor="middle" fill={TEXT_SECONDARY} fontSize="28">{label}</text>;
      })}
      {view.linePoints.length > 0 && <g clipPath="url(#financial-plot)">
        {principalY !== null && <line data-m2v-principal-line="true" x1={PLOT.left} x2={PLOT.right} y1={principalY} y2={principalY}
          stroke="#7A766F" strokeWidth="1.5" strokeDasharray="6 10" opacity="0.5" />}
        <polyline data-m2v-visible-value-points={visiblePoints.length} fill="none" stroke={gainColor} strokeWidth="2" opacity="0.26"
          strokeLinejoin="round" strokeLinecap="round" points={linePoints} />
        {trendPath && <path d={trendPath} fill="none" stroke={gainColor} strokeWidth="12" opacity="0.08"
          strokeLinejoin="round" strokeLinecap="round" />}
        {trendPath && <path data-m2v-trend-line="true" d={trendPath} fill="none" stroke={gainColor} strokeWidth="3"
          strokeLinejoin="round" strokeLinecap="round" />}
      </g>}
      {principalY !== null && <text data-m2v-principal-label="true" x={PLOT.right - 12}
        y={principalY < graphTop + 26 ? principalY + 20 : principalY - 10} textAnchor="end" fill={TEXT_SECONDARY} fontSize="20">本金</text>}
      {showEndpoint &&
        <g>
          <line data-m2v-endpoint-guide="true" x1={endpointX} x2={endpointX} y1={graphTop} y2={Math.min(PLOT.bottom, endpointY + 24)} stroke={gainColor} strokeWidth="1" opacity="0.12" />
          <circle cx={endpointX} cy={endpointY} r={haloRadius} fill="none" stroke={gainColor} strokeWidth="1.2" opacity="0.3" />
          <circle data-m2v-financial-endpoint="true" cx={endpointX} cy={endpointY} r={endpointRadius} fill={gainColor} stroke="#0A0A0B" strokeWidth="2.5" />
        </g>}
      <BottomOverlay copy={copy}/>
      </g>
    </svg>
  </AbsoluteFill>;
}
