/** 复利作品的题材布局：丘、取出组与索引；不依赖风格包，供前端数学测试直接导入。 */
export type Point = {x: number; y: number};

/**
 * S5 取出组：10 枚米白本金作底排，30 枚暗金分三排叠在其上，
 * 合起来是可数的 40 枚整块，而不是“柱 + 架”两个分离对象。
 */
export function withdrawBlockPositions(x0 = 300, baseY = 536, gap = 42) {
  const white = Array.from({length: 10}, (_, index) => ({x: x0 + index * gap, y: baseY}));
  const dark = Array.from({length: 30}, (_, index) => ({
    x: x0 + (index % 10) * gap,
    y: baseY - (Math.floor(index / 10) + 1) * gap,
  }));
  return {white, dark};
}

const HILL_ROWS = [26, 25, 24, 22, 20, 18, 16, 8];

/** 米白丘：8 行阶梯堆叠 + 确定性微抖，顶部一行中央留给第一年那枚。
 * 末行 8 枚包含 0.631 的分数圆片，使 158.631 个单位不被四舍五入掉。 */
export function hillPositions(count = 158, centerX = 1360, baseY = 940, pitch = 34, gap = 40): Point[] {
  const points: Point[] = [];
  for (let rowIndex = 0; rowIndex < HILL_ROWS.length; rowIndex++) {
    const n = HILL_ROWS[rowIndex];
    for (let i = 0; i < n; i++) {
      if (points.length >= count) return points;
      const lastRow = rowIndex === HILL_ROWS.length - 1;
      const jitterX = lastRow && i === 3 ? 0 : ((Math.sin((rowIndex * 31 + i) * 12.9898) * 43758.5453) % 1) * 3 - 1.5;
      const jitterY = lastRow && i === 3 ? 0 : ((Math.sin((rowIndex * 17 + i) * 78.233) * 12345.6789) % 1) * 2 - 1;
      points.push({x: centerX + (i - (n - 1) / 2) * gap + jitterX, y: baseY - rowIndex * pitch + jitterY});
    }
  }
  return points;
}

export const FIRST_DISC_INDEX = HILL_ROWS.slice(0, -1).reduce((a, b) => a + b, 0) + 3;
