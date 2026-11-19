/** 使用显式几何参数生成圆弧路径。 */
export type ArcPoint = {x: number; y: number};

/** 0° 在正上方、顺时针；整圆用两段半圆避免起终点重合退化。 */
export function arcPath(
  cx: number, cy: number, radius: number, startAngle: number, endAngle: number,
): string {
  if (radius <= 0) return '';
  if (endAngle - startAngle >= 360) {
    return `M ${cx} ${cy - radius} A ${radius} ${radius} 0 1 1 ${cx} ${cy + radius} `
      + `A ${radius} ${radius} 0 1 1 ${cx} ${cy - radius}`;
  }
  if (endAngle <= startAngle) return '';
  const pointAt = (angle: number): ArcPoint => {
    const radians = ((angle - 90) * Math.PI) / 180;
    return {x: cx + radius * Math.cos(radians), y: cy + radius * Math.sin(radians)};
  };
  const start = pointAt(startAngle);
  const end = pointAt(endAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}
