/**
 * 无旁白屏幕字幕：在共享字幕安全区内自绘单行文字，无底板、不换行。
 * 有旁白的作品不要导入本组件；屏幕字幕不进入共享字幕层，也不参与自动字幕校验。
 */
import {T, color, envelope, useNightSerif} from './kit';

export type ScreenSubtitleItem = {startFrame: number; endFrame: number; text: string};

export type ScreenSubtitleProps = {
  items: ScreenSubtitleItem[];
  frame: number;
  safeArea: {x: number; y: number; width: number; height: number};
  size?: number;
  color?: string;
  fps?: number;
  fadeFrames?: number;
  role?: string;
  state?: string;
};

export default function ScreenSubtitle({
  items, frame, safeArea, size = T.type.screenSubtitle, color: textColor = color('text'),
  fps = (typeof window === 'undefined' ? undefined : window.__M2V_CODE_CONFIG__?.fps) ?? 30,
  fadeFrames = Math.round(T.motion.screenSubtitleFadeMs / 1000 * fps),
  role = 'subtitle', state = 'visible',
}: ScreenSubtitleProps) {
  useNightSerif();
  const limit = T.type.screenSubtitleMaxChars;
  for (const item of items) {
    const length = [...item.text].length;
    if (!item.text.trim()) throw new Error('屏幕字幕不能为空');
    if (length > limit) throw new Error(`屏幕字幕超过 ${limit} 字：${item.text}`);
    if (!Number.isFinite(item.startFrame) || !Number.isFinite(item.endFrame) || item.startFrame >= item.endFrame) {
      throw new Error(`屏幕字幕窗口无效：${item.text}`);
    }
  }
  const active = items.find(item => frame >= item.startFrame && frame < item.endFrame);
  if (!active) return null;
  const opacity = envelope(frame, active.startFrame, active.endFrame, fadeFrames);
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{
      position: 'absolute', left: safeArea.x + safeArea.width / 2, top: safeArea.y + safeArea.height / 2,
      transform: 'translate(-50%, -50%)', width: safeArea.width, textAlign: 'center',
      fontFamily: '"Vibe Night Serif", "Noto Serif SC", serif',
      fontSize: size, lineHeight: T.type.lineHeight, letterSpacing: '0.06em',
      color: textColor, opacity, whiteSpace: 'nowrap', pointerEvents: 'none',
    }}>{active.text}</div>
  );
}
