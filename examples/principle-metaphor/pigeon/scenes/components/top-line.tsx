/**
 * 顶部结论行：居中的一行黑体短句，字距略宽。
 * 承载「这一场要让人记住的一句话」，不用来复述字幕。
 */
import {T, color} from './kit';

export type TopLineProps = {
  text: string;
  frame?: number;
  startFrame?: number;
  fadeFrames?: number;
  opacity?: number;
  color?: string;
  y?: number;
  size?: number;
};

export default function TopLine({
  text, frame, startFrame = 0, fadeFrames = 12, opacity = 1, color: textColor = color('ink'),
  y = T.layout.topLine.y, size,
}: TopLineProps) {
  const reveal = frame === undefined ? 1 : Math.min(1, Math.max(0, (frame - startFrame) / Math.max(1, fadeFrames)));
  return (
    <div style={{
      position: 'absolute', left: 0, right: 0, top: y, transform: 'translateY(-50%)',
      textAlign: 'center', opacity: opacity * reveal, pointerEvents: 'none',
      fontFamily: T.type.fontStack, fontSize: size ?? T.type.topLine, letterSpacing: `${T.type.topLineTrack}em`,
      color: textColor, whiteSpace: 'nowrap', fontWeight: 700,
      textShadow: '0 2px 10px rgba(0,0,0,.22)',
    }}>{text}</div>
  );
}
