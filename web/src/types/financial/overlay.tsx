/**
 * 金融画面覆盖层：对账单式标题、收束区账目、底部统计口径与安全区校验。
 *
 * 覆盖层文案与几何全部由 `view` 与 props 算出；`assertOverlaySafeArea` 只读 DOM
 * 包围盒，按 `LAYOUT_BOUNDS` 判定文字与端点是否越界或相互重叠。
 */
import {
  HEIGHT, LAYOUT_BOUNDS, LOSS_COLOR, NEUTRAL_COLOR, PROFIT_COLOR, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
  STATEMENT_CLOSING_RULE_Y, STATEMENT_MASTHEAD_RULE_Y, STATEMENT_RULE_OPACITY,
  TITLE_PREMISE_MIN, TITLE_PREMISE_SIZE, TITLE_SUBJECT_MIN, TITLE_SUBJECT_SIZE,
  displayDate, investmentAmountText, measuredTextWidth, moneyText, transformedBounds, wrapSvgText,
  type FinancialTimeSeriesProps, type FinancialView, type Investment,
} from './chart';
import {resolveDesign, withAlpha, type FinancialTitleMode} from './design';

export type OverlayCopy = {
  isCrypto: boolean;
  displayName: string;
  titleMode: FinancialTitleMode;
  subject: string;
  premise: string;
  title: string;
  subjectFontSize: number;
  premiseFontSize: number;
  titleFontSize: number;
  showValue: boolean;
  gainColor: string;
  valueFontSize: number;
  liveValue: string;
  liveDate: string;
  principalLabel: string;
  principalText: string;
  startText: string;
  ruleColor: string;
  notes: {
    rationaleY: number;
    summaryY: number;
    legalY: number;
    riskY: number;
  };
  summaryLinesToRender: string[];
  rationaleLines: string[];
  legalNoticeLines: string[];
  riskLines: string[];
  contentLayoutKey: string;
};

/** 对账单层级与收束区账目的全部文案、字号与颜色；越界容量在这里立刻失败。 */
export function overlayCopy(props: FinancialTimeSeriesProps, view: FinancialView, investment: Investment): OverlayCopy {
  const { request, prices } = props;
  const isCrypto = request.instrument.kind === 'crypto';
  const displayName = request.instrument.displayName ?? request.instrument.name;
  const investmentAmount = investmentAmountText(investment.principal);
  const investmentYear = investment.date?.slice(0, 4) ?? investment.year;
  const design = resolveDesign(request.design);
  const titleMode = design.titleMode;
  const title = isCrypto
    ? `假如你${investmentYear}年${Number(investment.date!.slice(5, 7))}月买入${investmentAmount}元${displayName}`
    : request.instrument.kind === 'index'
      ? `假如你${investmentYear}年按比例投资${investmentAmount}元${displayName}`
      : `假如你${investmentYear}年买入${investmentAmount}元${displayName}`;
  const premise = isCrypto
    ? `假如你${investmentYear}年${Number(investment.date!.slice(5, 7))}月买入${investmentAmount}元`
    : request.instrument.kind === 'index'
      ? `假如你${investmentYear}年按比例投资${investmentAmount}元`
      : `假如你${investmentYear}年买入${investmentAmount}元`;
  const titleWidth = LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left;
  const fitTier = (text: string, tiers: number[], message: string): number => {
    for (const size of tiers) {
      if (measuredTextWidth(text, size) <= titleWidth) return size;
    }
    throw new Error(message);
  };
  // premise 模式保留单行公式；subject 模式用主体名承担 56/48px 的主层级。
  const subjectFontSize = titleMode === 'subject'
    ? fitTier(displayName, [TITLE_SUBJECT_SIZE, TITLE_SUBJECT_MIN], '投资主体名过长，无法保持可读主体字号')
    : 0;
  const premiseFontSize = titleMode === 'subject'
    ? fitTier(premise, [TITLE_PREMISE_SIZE, TITLE_PREMISE_MIN], '投资条件句过长，无法保持可读条件句字号')
    : 0;
  const titleFontSize = titleMode === 'premise'
    ? Math.min(40, (titleWidth / measuredTextWidth(title, 40)) * 40)
    : 40;
  if (titleMode === 'premise' && titleFontSize < 26) {
    throw new Error('投资假设标题过长，无法在安全区内保持可读的单行字号');
  }
  const gainColor = view.gain === null || view.gain === 0 ? NEUTRAL_COLOR : view.gain > 0 ? PROFIT_COLOR : LOSS_COLOR;
  const showValue = view.latest !== null;
  const liveDate = view.latest ? displayDate(view.latest.date) : '';
  const liveValue = view.latest ? moneyText(view.latest.close) : '';
  const principalLabel = '本金';
  const principalText = `${investmentAmount}元`;
  const startText = `起点 ${displayDate(view.investmentStartDate ?? request.displayRange[0])}`;
  // 左列账目决定右列可用宽度；金额覆盖左列时阻断，不靠缩小到不可读字号。
  const leftColumnWidth = Math.max(
    measuredTextWidth(principalLabel, 20),
    measuredTextWidth(principalText, 28),
    measuredTextWidth(startText, 20),
  );
  const valueAvailable = LAYOUT_BOUNDS.right - 4 - (LAYOUT_BOUNDS.left + 2 + leftColumnWidth + 32);
  const fittedValueSize = [72, 64, 56].find((size) => measuredTextWidth(liveValue, size) <= valueAvailable);
  if (showValue && fittedValueSize === undefined) {
    throw new Error('当前市值金额过长，无法与本金账目并排保持 56px 可读字号');
  }
  const valueFontSize = fittedValueSize ?? 56;
  const summaryText = [isCrypto
    ? 'BTC/USD 日收盘价按历史 USD/CNY 汇率折算；休市日沿用此前汇率，不计手续费及税费'
    : `${prices.priceBasis === 'official-index-points' ? `指数类型 ${prices.indexType}；按点位比例模拟，不代表指数可直接持有` : '仅拆合股调整，不计分红再投资'}；按比例持仓，不计手续费及税费`];
  const summaryLines = summaryText.flatMap((line) => wrapSvgText(line, LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 20));
  if (summaryLines.length > 4) throw new Error('统计口径超出说明区域四行容量');
  const rationaleLines = isCrypto && investment.startRationale
    ? wrapSvgText(investment.startRationale, LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 16) : [];
  if (rationaleLines.length > 2) throw new Error('起点说明超出两行容量');
  const legalNoticeLines = isCrypto && investment.legalStatusNotice
    ? wrapSvgText(investment.legalStatusNotice, LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 16) : [];
  if (legalNoticeLines.length > 2) throw new Error('法律地位说明超出两行容量');
  const hasLegalNotice = legalNoticeLines.length > 0;
  const summaryLinesToRender = isCrypto && hasLegalNotice ? [] : summaryLines;
  const riskLines = hasLegalNotice ? [] : wrapSvgText('过往业绩不代表未来表现。本视频仅作信息展示，不构成投资建议。', LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left, 16);
  if (riskLines.length > 2) throw new Error('风险提示超出说明区域两行容量');
  // 说明区从收束区账目下方开始按实际行数堆叠，避免固定坐标在长文案时互相覆盖。
  const notesTop = 1550;
  const rationaleY = notesTop;
  let cursor = rationaleY + rationaleLines.length * 24;
  const summaryY = cursor + (rationaleLines.length ? 10 : 0);
  cursor = summaryY + summaryLinesToRender.length * 28;
  const legalY = cursor + ((rationaleLines.length || summaryLinesToRender.length) ? 10 : 0);
  cursor = legalY + legalNoticeLines.length * 24;
  const riskY = cursor + ((rationaleLines.length || summaryLinesToRender.length || legalNoticeLines.length) ? 12 : 0);
  const notesBottom = Math.max(
    rationaleY + Math.max(rationaleLines.length - 1, 0) * 24,
    summaryY + Math.max(summaryLinesToRender.length - 1, 0) * 28,
    legalY + Math.max(legalNoticeLines.length - 1, 0) * 24,
    riskY + Math.max(riskLines.length - 1, 0) * 26,
  );
  if (notesBottom + 8 > LAYOUT_BOUNDS.bottom) throw new Error('底部说明超出项目布局范围');
  const contentLayoutKey = JSON.stringify([titleMode, displayName, subjectFontSize, premise, premiseFontSize,
    title, titleFontSize, showValue, valueFontSize, principalText, startText,
    summaryLinesToRender, rationaleLines, legalNoticeLines, riskLines]);
  return { isCrypto, displayName, titleMode, subject: displayName, premise, title,
    subjectFontSize, premiseFontSize, titleFontSize, showValue, gainColor,
    valueFontSize, liveValue, liveDate, principalLabel, principalText, startText,
    ruleColor: withAlpha(design.rule, STATEMENT_RULE_OPACITY),
    notes: {rationaleY, summaryY, legalY, riskY},
    summaryLinesToRender, rationaleLines, legalNoticeLines, riskLines, contentLayoutKey };
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
    // 报出具体越界元素，避免只给整体包围盒后还要逐层排查。
    const offenders = [...contentLayer.querySelectorAll('*')]
      .filter((element): element is SVGGraphicsElement => element instanceof SVGGraphicsElement)
      .map((element) => ({ element, bounds: transformedBounds(element) }))
      .filter(({ bounds }) => bounds.x < LAYOUT_BOUNDS.left || bounds.x + bounds.width > LAYOUT_BOUNDS.right
        || bounds.y < LAYOUT_BOUNDS.top || bounds.y + bounds.height > LAYOUT_BOUNDS.bottom)
      .map(({ element, bounds }) => `${element.tagName}「${(element.textContent ?? '').slice(0, 16)}」(${bounds.x.toFixed(2)},${bounds.y.toFixed(2)},${bounds.width.toFixed(2)},${bounds.height.toFixed(2)})`)
      .join('；');
    throw new Error(`金融画面整体内容超出项目布局范围（${layerBounds.x},${layerBounds.y},${layerBounds.width},${layerBounds.height}）：${offenders}`);
  }
}

/** 收束区左右两列必须并排；金额不得覆盖本金、起点或日期。 */
export function assertStatementColumns(svg: SVGSVGElement): void {
  const value = svg.querySelector<SVGTextElement>('[data-m2v-live-value="true"]');
  if (!value) return;
  const valueBounds = transformedBounds(value);
  const leftItems = ['[data-m2v-principal-amount="true"]', '[data-m2v-investment-start="true"]']
    .map((selector) => svg.querySelector<SVGTextElement>(selector))
    .filter((element): element is SVGTextElement => element !== null)
    .map(transformedBounds);
  const leftRight = Math.max(...leftItems.map((bounds) => bounds.x + bounds.width));
  if (valueBounds.x < leftRight + 31.5) {
    throw new Error(`收束区当前市值与本金账目重叠：账目右缘 ${leftRight.toFixed(2)}，金额左缘 ${valueBounds.x.toFixed(2)}`);
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

export type StatementMotion = {
  subjectOpacity: number;
  subjectRise: number;
  premiseOpacity: number;
  premiseRise: number;
  mastheadRule: number;
  chartOpacity: number;
  closingRule: number;
  closingOpacity: number;
  closingRise: number;
  closingScale: number;
  notesOpacity: number;
};

const STILL: StatementMotion = {
  subjectOpacity: 1, subjectRise: 0, premiseOpacity: 1, premiseRise: 0,
  mastheadRule: 1, chartOpacity: 1, closingRule: 1,
  closingOpacity: 1, closingRise: 0, closingScale: 1, notesOpacity: 1,
};

const ruleEnd = (progress: number) => LAYOUT_BOUNDS.left + (LAYOUT_BOUNDS.right - LAYOUT_BOUNDS.left) * progress;

/** 标题区：上方分隔线 + 主体名/条件句或单行公式。 */
export function TopOverlay({copy, motion = STILL}: {copy: OverlayCopy; motion?: StatementMotion}) {
  const {titleMode, subject, premise, title, subjectFontSize, premiseFontSize, titleFontSize, ruleColor} = copy;
  return <>
    <line data-m2v-statement-rule="masthead" x1={LAYOUT_BOUNDS.left} x2={ruleEnd(motion.mastheadRule)}
      y1={STATEMENT_MASTHEAD_RULE_Y} y2={STATEMENT_MASTHEAD_RULE_Y} stroke={ruleColor} strokeWidth="1" />
    {titleMode === 'subject' ? <>
      <text data-m2v-investment-subject="true" x={LAYOUT_BOUNDS.left + 2} y="250" textAnchor="start" fill={TEXT_PRIMARY}
        fontSize={subjectFontSize} fontWeight="700" letterSpacing="-0.03em"
        opacity={motion.subjectOpacity} transform={`translate(0 ${motion.subjectRise})`}>{subject}</text>
      <text data-m2v-investment-premise="true" x={LAYOUT_BOUNDS.left + 2} y="302" textAnchor="start" fill={TEXT_PRIMARY}
        fontSize={premiseFontSize} fontWeight="500" letterSpacing="-0.01em"
        opacity={motion.premiseOpacity} transform={`translate(0 ${motion.premiseRise})`}>{premise}</text>
    </> : <text data-m2v-investment-title="true" x={LAYOUT_BOUNDS.left + 2} y="270" textAnchor="start" fill={TEXT_PRIMARY}
      fontSize={titleFontSize} fontWeight="700" letterSpacing="-0.02em"
      opacity={motion.subjectOpacity} transform={`translate(0 ${motion.subjectRise})`}>{title}</text>}
  </>;
}

/** 收束区：分隔线、本金/起点账目与右对齐的当前市值。 */
export function ClosingOverlay({copy, motion = STILL}: {copy: OverlayCopy; motion?: StatementMotion}) {
  const {showValue, gainColor, valueFontSize, liveValue, liveDate,
    principalLabel, principalText, startText, ruleColor} = copy;
  const tabular = {fontVariantNumeric: 'tabular-nums lining-nums'} as const;
  return <>
    <line data-m2v-statement-rule="closing" x1={LAYOUT_BOUNDS.left} x2={ruleEnd(motion.closingRule)}
      y1={STATEMENT_CLOSING_RULE_Y} y2={STATEMENT_CLOSING_RULE_Y} stroke={ruleColor} strokeWidth="1" />
    <g opacity={motion.closingOpacity} transform={`translate(0 ${motion.closingRise})`}>
      <text data-m2v-principal-caption="true" x={LAYOUT_BOUNDS.left + 2} y="1404" textAnchor="start"
        fill={TEXT_SECONDARY} fontSize="20" fontWeight="500">{principalLabel}</text>
      <text data-m2v-principal-amount="true" x={LAYOUT_BOUNDS.left + 2} y="1440" textAnchor="start"
        fill={TEXT_PRIMARY} fontSize="28" fontWeight="600" letterSpacing="-0.01em" style={tabular}>{principalText}</text>
      <text data-m2v-investment-start="true" x={LAYOUT_BOUNDS.left + 2} y="1472" textAnchor="start"
        fill={TEXT_MUTED} fontSize="20">{startText}</text>
      {showValue && <>
        <text data-m2v-live-caption="true" x={LAYOUT_BOUNDS.right - 4} y="1404" textAnchor="end"
          fill={TEXT_SECONDARY} fontSize="20" fontWeight="500">当前市值</text>
        <text data-m2v-live-value="true" x={LAYOUT_BOUNDS.right - 4} y="1470" textAnchor="end" fill={gainColor}
          fontSize={valueFontSize} fontWeight="700" letterSpacing="-0.03em" style={tabular}
          transform={`translate(${LAYOUT_BOUNDS.right - 4} 1470) scale(${motion.closingScale}) translate(${-(LAYOUT_BOUNDS.right - 4)} -1470)`}>{liveValue}</text>
        <text data-m2v-live-date="true" x={LAYOUT_BOUNDS.right - 4} y="1510" textAnchor="end"
          fill={TEXT_SECONDARY} fontSize="24" style={tabular}>{liveDate}</text>
      </>}
    </g>
  </>;
}

/** 底部覆盖层：起点说明、统计口径、法律地位与风险提示。 */
export function BottomOverlay({copy, motion = STILL}: {copy: OverlayCopy; motion?: StatementMotion}) {
  const {rationaleLines, summaryLinesToRender, legalNoticeLines, riskLines, notes} = copy;
  return <g opacity={motion.notesOpacity}>
    {rationaleLines.map((line, index) => <text data-m2v-start-rationale="true" key={`rationale-${index}`} x={LAYOUT_BOUNDS.left + 2} y={notes.rationaleY + index * 24} fill={TEXT_SECONDARY} fontSize="20">{line}</text>)}
    {summaryLinesToRender.map((line, index) => <text data-m2v-summary="true" key={`summary-${index}`} x={LAYOUT_BOUNDS.left + 2} y={notes.summaryY + index * 28} fill="#B5B0A8" fontSize="24">{line}</text>)}
    {legalNoticeLines.map((line, index) => <text data-m2v-legal-status-notice="true" key={`legal-notice-${index}`} x={LAYOUT_BOUNDS.left + 2} y={notes.legalY + index * 24} fill={TEXT_SECONDARY} fontSize="20">{line}</text>)}
    {riskLines.map((line, index) => <text data-m2v-risk-disclaimer="true" key={`risk-${index}`} x={LAYOUT_BOUNDS.left + 2} y={notes.riskY + index * 26} fill={TEXT_SECONDARY} fontSize="22">{line}</text>)}
  </g>;
}
