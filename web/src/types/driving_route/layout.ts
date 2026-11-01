/** 自驾路线画面与底图的共享布局常量（Python 读取同一份 JSON）。 */
import raw from './layout.json';

export type ContentRect = {
  top: number;
  bottom: number;
  left: number;
  right: number;
  innerTop: number;
  innerBottom: number;
  innerLeft: number;
  innerRight: number;
  cx: number;
  cy: number;
};

export const LAYOUT = raw;

/** 标题带以下的内容区；相机全程取景使用其中的 inner 矩形。 */
export function contentRect(width: number = LAYOUT.width, height: number = LAYOUT.height): ContentRect {
  const top = LAYOUT.title.height + LAYOUT.content.topGap;
  const bottom = height - LAYOUT.content.bottomMargin;
  const left = LAYOUT.content.sideMargin;
  const right = width - LAYOUT.content.sideMargin;
  const padding = LAYOUT.content.padding;
  return {
    top, bottom, left, right,
    innerTop: top + padding,
    innerBottom: bottom - padding,
    innerLeft: left + padding,
    innerRight: right - padding,
    cx: (left + right) / 2,
    cy: (top + bottom) / 2,
  };
}
