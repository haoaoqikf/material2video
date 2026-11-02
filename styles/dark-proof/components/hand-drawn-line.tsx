/**
 * 手绘描线：按显式进度画出外部传入的 path。
 *
 * 路径与题材留在作品内；本组件只负责线宽、圆头、双层轻微错位与生长进度。
 * 不使用滤镜或动画计时器，同一进度在任何机器上画出同一条线。
 */
export type HandDrawnLineProps = {
  d: string;
  color?: string;
  width?: number;
  progress?: number;
  opacity?: number;
  /** 第二层淡笔的横向错位；0 时关闭双层。 */
  ghostOffset?: number;
  /** 只画轮廓的虚线；仍由进度控制生长。 */
  dashed?: boolean;
};

export default function HandDrawnLine({
  d, color = '#F3EDDC', width = 9, progress = 1, opacity = 1, ghostOffset = 1.4, dashed = false,
}: HandDrawnLineProps) {
  const value = Math.min(1, Math.max(0, progress));
  if (!d || value <= 0) return null;
  const dash = dashed ? '0.014 0.012' : '1';
  return (
    <g opacity={opacity}>
      {ghostOffset !== 0 ? (
        <g transform={`translate(${ghostOffset} ${-ghostOffset * 0.6})`} opacity={0.32}>
          <path d={d} fill="none" stroke={color} strokeWidth={Math.max(1, width * 0.55)}
            strokeLinecap="round" strokeLinejoin="round"
            pathLength={1} strokeDasharray={dash} strokeDashoffset={dashed ? 0 : 1 - value}/>
        </g>
      ) : null}
      <path d={d} fill="none" stroke={color} strokeWidth={width}
        strokeLinecap="round" strokeLinejoin="round"
        pathLength={1} strokeDasharray={dash} strokeDashoffset={dashed ? 0 : 1 - value}/>
    </g>
  );
}
