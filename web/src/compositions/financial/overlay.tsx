/**
 * 金融画面覆盖层：顶部年份/市值、底部统计口径、起点说明、法律地位与风险提示，
 * 以及整体居中与安全区校验（字幕避让）。
 *
 * 覆盖层文案与几何全部由 `view` 与 props 算出；`assertOverlaySafeArea` 只读 DOM
 * 包围盒，按 `LAYOUT_BOUNDS` 判定文字与端点是否越界或相互重叠。
 */
import {
  HEIGHT, LAYOUT_BOUNDS, LOSS_COLOR, PROFIT_COLOR, WIDTH,
  displayDate, investmentAmountText, measuredTextWidth, moneyText, transformedBounds, wrapSvgText,
  type FinancialTimeSeriesProps, type FinancialView, type Investment,
} from './chart';

export type OverlayCopy = {
  isCrypto: boolean;
  displayName: string;
  title: string;
  titleFontSize: number;
  year: string;
  showValue: boolean;
  gainColor: string;
  valueFontSize: number;
  liveValue: string;
  liveDate: string;
  summaryLinesToRender: string[];
  rationaleLines: string[];
  legalNoticeLines: string[];
  riskLines: string[];
  contentLayoutKey: string;
};

/** 顶部年份/市值与底部说明的全部文案、字号与颜色；越界容量在这里立刻失败。 */
export function overlayCopy(props: FinancialTimeSeriesProps, view: FinancialView, investment: Investment): OverlayCopy {
  const { request, prices, plan } = props;
  const isCrypto = request.instrument.kind === 'crypto';
  const displayName = request.instrument.displayName ?? request.instrument.name;
  const investmentAmount = investmentAmountText(investment.principal);
  const investmentYear = investment.date?.slice(0, 4) ?? investment.year;
  const title = isCrypto
    ? `假如你${investmentYear}年${Number(investment.date!.slice(5, 7))}月买入${investmentAmount}元${displayName}`
    : request.instrument.kind === 'index'
      ? `假如你${investmentYear}年按比例投资${investmentAmount}元${displayName}`
      : `假如你${investmentYear}年买入${investmentAmount}元${displayName}`;
  const titleWidth = LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left;
  const titleFontSize = Math.min(48, (titleWidth / measuredTextWidth(title, 48)) * 48);
  if (titleFontSize < 26) throw new Error('投资假设标题过长，无法在安全区内保持可读的单行字号');
  const gainColor = view.gain !== null && view.gain > 0 ? PROFIT_COLOR : LOSS_COLOR;
  const liveDate = view.latest ? displayDate(view.latest.date) : '';
  const year = (view.latest?.date ?? plan.axis.dateRange[0]).slice(0, 4);
  const liveValue = view.latest ? moneyText(view.latest.close) : '';
  const yearWidth = measuredTextWidth(year, 64);
  const valueWidth = LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left - yearWidth - 32;
  const valueFontSize = Math.min(56, valueWidth / Math.max(measuredTextWidth(liveValue, 56) * 1.08, 1) * 56);
  const summaryText = [isCrypto
    ? 'BTC/USD 日收盘价按历史 USD/CNY 汇率折算；休市日沿用此前汇率，不计手续费及税费'
    : `${prices.priceBasis === 'official-index-points' ? `指数类型 ${prices.indexType}；按点位比例模拟，不代表指数可直接持有` : '仅拆合股调整，不计分红再投资'}；按比例持仓，不计手续费及税费`];
  const summaryLines = summaryText.flatMap((line) => wrapSvgText(line, LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 24));
  if (summaryLines.length > 4) throw new Error('统计口径超出说明区域四行容量');
  const rationaleLines = isCrypto && investment.startRationale
    ? wrapSvgText(investment.startRationale, LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 18) : [];
  if (rationaleLines.length > 2) throw new Error('起点说明超出两行容量');
  const legalNoticeLines = isCrypto && investment.legalStatusNotice
    ? wrapSvgText(investment.legalStatusNotice, LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 20) : [];
  if (legalNoticeLines.length > 2) throw new Error('法律地位说明超出两行容量');
  const hasLegalNotice = legalNoticeLines.length > 0;
  const summaryLinesToRender = isCrypto && hasLegalNotice ? [] : summaryLines;
  const riskLines = hasLegalNotice ? [] : wrapSvgText('过往业绩不代表未来表现。本视频仅作信息展示，不构成投资建议。', LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 20);
  if (riskLines.length > 2) throw new Error('风险提示超出说明区域两行容量');
  const contentLayoutKey = JSON.stringify([title, titleFontSize, summaryLinesToRender, rationaleLines, legalNoticeLines, riskLines]);
  return { isCrypto, displayName, title, titleFontSize, year, showValue: view.latest !== null, gainColor,
    valueFontSize, liveValue, liveDate, summaryLinesToRender, rationaleLines, legalNoticeLines, riskLines, contentLayoutKey };
}

/** 把整体内容在画布纵向居中；超出可用高度时明确失败。 */
export function canvasCenterOffset(bounds: { y: number; height: number }): number {
  if (bounds.height > LAYOUT_BOUNDS.bottom - LAYOUT_BOUNDS.top) throw new Error('金融画面整体内容高于纵向布局可用高度');
  return Math.round((HEIGHT / 2 - (bounds.y + bounds.height / 2)) * 100) / 100;
}

/** 整体内容层必须落在项目布局范围内（含整体居中后的位移）。 */
export function assertContentLayerWithinBounds(contentLayer: SVGGElement): void {
  const layerBounds = transformedBounds(contentLayer);
  if (layerBounds.x < LAYOUT_BOUNDS.left || layerBounds.x + layerBounds.width > LAYOUT_BOUNDS.right
    || layerBounds.y < LAYOUT_BOUNDS.top || layerBounds.y + layerBounds.height > LAYOUT_BOUNDS.bottom) {
    throw new Error(`金融画面整体内容超出项目布局范围（${layerBounds.x},${layerBounds.y},${layerBounds.width},${layerBounds.height}）`);
  }
}

/** 字幕避让：所有文字、横轴标签与曲线端点都必须落在项目布局范围内且互不重叠。 */
export function assertOverlaySafeArea(svg: SVGSVGElement): void {
  for (const element of svg.querySelectorAll('text')) {
    const bounds = transformedBounds(element);
    if (bounds.x < LAYOUT_BOUNDS.left || bounds.x + bounds.width > LAYOUT_BOUNDS.right || bounds.y < LAYOUT_BOUNDS.top || bounds.y + bounds.height > LAYOUT_BOUNDS.bottom) {
      throw new Error(`金融画面文字超出项目布局范围：${element.textContent ?? ''}（${bounds.x},${bounds.y},${bounds.width},${bounds.height}）`);
    }
  }
  const labelBounds = [...svg.querySelectorAll<SVGTextElement>('[data-m2v-axis-label="true"]')]
    .map(transformedBounds).sort((a, b) => a.x - b.x);
  for (let index = 1; index < labelBounds.length; index++) {
    if (labelBounds[index]!.x - (labelBounds[index - 1]!.x + labelBounds[index - 1]!.width) < 12) {
      throw new Error('金融画面横轴标签实际字体边界发生重叠');
    }
  }
  for (const endpoint of svg.querySelectorAll<SVGCircleElement>('circle')) {
    const center = new DOMPoint(Number(endpoint.getAttribute('cx')), Number(endpoint.getAttribute('cy'))).matrixTransform(endpoint.getCTM()!);
    const x = center.x;
    const y = center.y;
    const radius = Number(endpoint.getAttribute('r'));
    if (x - radius < LAYOUT_BOUNDS.left || x + radius > LAYOUT_BOUNDS.right || y - radius < LAYOUT_BOUNDS.top || y + radius > LAYOUT_BOUNDS.bottom) {
      throw new Error('金融画面曲线端点超出项目布局范围');
    }
  }
}

/** 顶部覆盖层：投资假设标题、当前年份与实时市值。 */
export function TopOverlay({copy}: {copy: OverlayCopy}) {
  const {title, titleFontSize, year, showValue, gainColor, valueFontSize, liveValue, liveDate} = copy;
  return <>
    <text data-m2v-investment-title="true" x={WIDTH / 2} y="270" textAnchor="middle" fill="#f6f8fc" fontSize={titleFontSize} fontWeight="700">{title}</text>
    <text data-m2v-live-year="true" x={LAYOUT_BOUNDS.left} y="390" fill="#f6f8fc" fontSize="64" fontWeight="700" style={{ fontVariantNumeric: 'tabular-nums' }}>{year}</text>
    {showValue && <g>
      <text data-m2v-value-heading="true" x={LAYOUT_BOUNDS.right} y="330" textAnchor="end" fill="#b9c7d9" fontSize="24">当前市值</text>
      <text data-m2v-live-value="true" x={LAYOUT_BOUNDS.right} y="396" textAnchor="end" fill={gainColor} fontSize={valueFontSize} fontWeight="700" style={{ fontVariantNumeric: 'tabular-nums' }}>{liveValue}</text>
      <text data-m2v-live-date="true" x={LAYOUT_BOUNDS.right} y="442" textAnchor="end" fill="#b9c7d9" fontSize="24" fontWeight="500">{liveDate}</text>
    </g>}
  </>;
}

/** 底部覆盖层：起点说明、统计口径、法律地位与风险提示。 */
export function BottomOverlay({copy}: {copy: OverlayCopy}) {
  const {isCrypto, rationaleLines, summaryLinesToRender, legalNoticeLines, riskLines} = copy;
  return <>
    {rationaleLines.map((line, index) => <text data-m2v-start-rationale="true" key={`rationale-${index}`} x={LAYOUT_BOUNDS.left} y={(isCrypto ? 1310 : 0) + index * 24} fill="#9ba9bc" fontSize="18">{line}</text>)}
    {summaryLinesToRender.map((line, index) => <text data-m2v-summary="true" key={`summary-${index}`} x={LAYOUT_BOUNDS.left} y={(isCrypto ? 1370 : 1320) + index * 32} fill="#b9c7d9" fontSize="24">{line}</text>)}
    {legalNoticeLines.map((line, index) => <text data-m2v-legal-status-notice="true" key={`legal-notice-${index}`} x={LAYOUT_BOUNDS.left} y={1370 + index * 28} fill="#b9c7d9" fontSize="20">{line}</text>)}
    {riskLines.map((line, index) => <text data-m2v-risk-disclaimer="true" key={`risk-${index}`} x={LAYOUT_BOUNDS.left} y={(isCrypto ? 1510 : 1460) + index * 28} fill="#8b9ab0" fontSize="20">{line}</text>)}
  </>;
}
