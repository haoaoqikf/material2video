/**
 * Lucide 与原生 SVG 的使用约束：图标与路径动画只由帧号控制。
 *
 * 约束（静态闸门 A8/A14 与本组件共同执行）：
 * - **不许外部 `<use>`**：`<use href="…">` 只能指向同文档片段（`#id`），
 *   外链 SVG 文件会在离线渲染时静默空白；Lucide 组件自绘全部路径，
 *   天然满足；
 * - **不许外链 URL**：图标与图片资源只能来自打包器解析的本地导入，
 *   `https://…` 与 `//cdn…` 在源码层面就被拒绝；
 * - **动画只由帧号驱动**：路径描边进度用 `frameStroke(progress)` 计算
 *   stroke-dasharray/offset，禁止 CSS transition/animation（A13）。
 */
import type { LucideIcon } from 'lucide-react';
import type { CSSProperties } from 'react';

export interface A2VFrameIconProps {
  /** Lucide 图标组件（来自 lucide-react 的具名导出）。 */
  icon: LucideIcon;
  /** 像素尺寸（正方形）。 */
  size?: number;
  strokeWidth?: number;
  color?: string;
  /** 随帧号变化的透明度（0..1），由帧号驱动而非 CSS。 */
  progress?: number;
  style?: CSSProperties;
  className?: string;
  /** 语义角色（内容探针/C/K 闸门用）。 */
  'aria-label'?: string;
}

/**
 * 帧驱动的 Lucide 图标。SVG 描边宽度、颜色都是纯属性注入；
 * 透明度走 style，不引入任何时间函数。
 */
export function FrameIcon({
  icon: Icon,
  size = 96,
  strokeWidth = 1.75,
  color,
  progress = 1,
  style,
  className,
  ...rest
}: A2VFrameIconProps): React.ReactElement {
  return (
    <Icon
      size={size}
      strokeWidth={strokeWidth}
      color={color}
      className={className}
      style={{ opacity: Math.min(1, Math.max(0, progress)), ...style }}
      aria-hidden={rest['aria-label'] ? undefined : true}
      {...(rest['aria-label'] ? { 'aria-label': rest['aria-label'] } : {})}
    />
  );
}

/**
 * 帧驱动的路径描边：把 0..1 进度映射成 stroke-dasharray/offset。
 *
 * `pathLength` 参数与 SVG 的 `pathLength` 属性配套：给路径声明
 * `pathLength={1}` 后，dash 值直接用进度即可，无需测量真实长度
 * （测量会依赖字体/缩放，属于渲染期不确定因素）。
 *
 * 用法：
 * ```tsx
 * <path d={arc} pathLength={1} strokeDasharray={frameStroke(progress).dasharray}
 *       strokeDashoffset={frameStroke(progress).offset} />
 * ```
 */
export function frameStroke(progress: number, pathLength = 1): { dasharray: string; offset: number } {
  const clamped = Math.min(1, Math.max(0, progress));
  const total = pathLength * 1.0001; // 覆盖浮点误差，满进度时接缝不可见
  return {
    dasharray: `${total}`,
    offset: (1 - clamped) * total,
  };
}
