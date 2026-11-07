/** 象形图与图标阵列：一格代表一个单位，填充量只由数值与进度决定。 */
import type {CSSProperties} from 'react';
import {clampProgress, type Easing} from '../primitives';

const IDENTITY: Easing = value => value;

export type PictogramProps = {
  /** 总格数。 */
  count: number;
  /** 填充单位数，可带小数；与 progress 相乘后逐格显示。 */
  value: number;
  progress?: number;
  easing?: Easing;
  columns?: number;
  cellSize?: number;
  gap?: number;
  color?: string;
  dimColor?: string;
  shape?: 'square' | 'circle';
  /** 有图标时用路径替换方块/圆点；坐标按 iconViewBox 归一。 */
  icon?: string;
  iconViewBox?: number;
  className?: string;
  style?: CSSProperties;
};

/** 象形图；部分填充的格子用透明度表示，不裁切图标。 */
export function Pictogram({
  count, value, progress = 1, easing = IDENTITY, columns = 10, cellSize = 28, gap = 8,
  color = '#F8D893', dimColor = 'rgba(255, 255, 255, 0.12)', shape = 'square', icon,
  iconViewBox = 24, className, style,
}: PictogramProps) {
  const safeColumns = Math.max(1, Math.floor(columns));
  const total = Math.max(0, Math.floor(count));
  const rows = Math.ceil(total / safeColumns);
  const width = safeColumns * cellSize + (safeColumns - 1) * gap;
  const height = Math.max(0, rows * cellSize + (rows - 1) * gap);
  const filled = Math.max(0, Math.min(total, value * easing(clampProgress(progress))));
  const scale = (cellSize - cellSize * 0.18 * 2) / iconViewBox;
  return (
    <svg className={className} width={width} height={height}
      viewBox={`0 0 ${width} ${height}`} style={{overflow: 'visible', ...style}}>
      {Array.from({length: total}, (_, index) => {
        const x = (index % safeColumns) * (cellSize + gap);
        const y = Math.floor(index / safeColumns) * (cellSize + gap);
        const amount = Math.max(0, Math.min(1, filled - index));
        const common = {opacity: amount};
        return (
          <g key={index}>
            {icon ? (
              <>
                <g transform={`translate(${x + cellSize * 0.18}, ${y + cellSize * 0.18}) scale(${scale})`}>
                  <path d={icon} fill={dimColor}/>
                </g>
                {amount > 0 ? (
                  <g transform={`translate(${x + cellSize * 0.18}, ${y + cellSize * 0.18}) scale(${scale})`}>
                    <path d={icon} fill={color} {...common}/>
                  </g>
                ) : null}
              </>
            ) : (
              <>
                {shape === 'circle' ? (
                  <circle cx={x + cellSize / 2} cy={y + cellSize / 2} r={cellSize / 2}
                    fill={dimColor}/>
                ) : (
                  <rect x={x} y={y} width={cellSize} height={cellSize} rx={cellSize * 0.12}
                    fill={dimColor}/>
                )}
                {amount > 0 ? shape === 'circle' ? (
                  <circle cx={x + cellSize / 2} cy={y + cellSize / 2} r={cellSize / 2}
                    fill={color} {...common}/>
                ) : (
                  <rect x={x} y={y} width={cellSize} height={cellSize} rx={cellSize * 0.12}
                    fill={color} {...common}/>
                ) : null}
              </>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export type IconGridProps = Omit<PictogramProps, 'shape'> & {icon: string};

/** 图标阵列：与象形图同一填充语义，强制使用图标。 */
export function IconGrid(props: IconGridProps) {
  return <Pictogram {...props} shape="square"/>;
}
