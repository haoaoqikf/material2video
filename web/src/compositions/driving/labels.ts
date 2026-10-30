/** 标签与里程 pill 的纯布局辅助。 */
import { LAYOUT } from './layout';

/** 粗估文本宽度：中文按 1em，ASCII 按 0.58em，空格按 0.3em。 */
export function estimateTextWidth(text: string, fontSize: number): number {
  let em = 0;
  for (const char of text) {
    if (/\s/u.test(char)) em += 0.3;
    else if (/[　-鿿＀-￯]/u.test(char)) em += 1;
    else em += 0.58;
  }
  return em * fontSize;
}

export function fitFontSize(text: string, maxWidth: number, base: number, minimum: number): number {
  const width = estimateTextWidth(text, base);
  if (width <= maxWidth) return base;
  return Math.max(minimum, Math.floor(base * (maxWidth / width)));
}

/** 缩到最小字号仍放不下时截断并加省略号，绝不越过屏幕边缘。 */
export function truncateText(text: string, maxWidth: number, fontSize: number): string {
  if (estimateTextWidth(text, fontSize) <= maxWidth) return text;
  let output = '';
  for (const char of text) {
    if (estimateTextWidth(`${output}${char}…`, fontSize) > maxWidth) break;
    output += char;
  }
  return output ? `${output}…` : '…';
}

export type LabelBox = {left: number; right: number; top: number; bottom: number};

function overlaps(first: LabelBox, second: LabelBox): boolean {
  return !(first.right < second.left || first.left > second.right
    || first.bottom < second.top || first.top > second.bottom);
}

export type Pill = {cx: number; cy: number; width: number; height: number};

/** 在车辆四角候选位置中选一个不越界、不压标题带、不压给定障碍的位置。 */
export function placeDistancePill(vehicleX: number, vehicleY: number, text: string,
                                  width: number, height: number, contentTop: number,
                                  avoid: LabelBox[] = []): Pill {
  const fontSize = LAYOUT.labels.pillSize;
  const pillHeight = LAYOUT.labels.pillHeight;
  const pillWidth = estimateTextWidth(text, fontSize) + 40;
  const margin = LAYOUT.labels.sideMargin;
  const gap = 46;
  const candidates: Pill[] = [
    {cx: vehicleX + gap + pillWidth / 2, cy: vehicleY - 58, width: pillWidth, height: pillHeight},
    {cx: vehicleX - gap - pillWidth / 2, cy: vehicleY - 58, width: pillWidth, height: pillHeight},
    {cx: vehicleX + gap + pillWidth / 2, cy: vehicleY + 58, width: pillWidth, height: pillHeight},
    {cx: vehicleX - gap - pillWidth / 2, cy: vehicleY + 58, width: pillWidth, height: pillHeight},
  ];
  const fits = (pill: Pill) => pill.cx - pill.width / 2 >= margin
    && pill.cx + pill.width / 2 <= width - margin
    && pill.cy - pill.height / 2 >= contentTop
    && pill.cy + pill.height / 2 <= height - margin;
  const asBox = (pill: Pill): LabelBox => ({
    left: pill.cx - pill.width / 2, right: pill.cx + pill.width / 2,
    top: pill.cy - pill.height / 2, bottom: pill.cy + pill.height / 2,
  });
  const chosen = candidates.find((pill) => fits(pill) && !avoid.some((box) => overlaps(asBox(pill), box)))
    ?? candidates.find(fits) ?? candidates[0];
  return {
    ...chosen,
    cx: Math.min(width - margin - chosen.width / 2, Math.max(margin + chosen.width / 2, chosen.cx)),
    cy: Math.min(height - margin - chosen.height / 2, Math.max(contentTop + chosen.height / 2, chosen.cy)),
  };
}
