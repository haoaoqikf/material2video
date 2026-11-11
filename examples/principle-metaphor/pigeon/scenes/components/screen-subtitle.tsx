/**
 * 无旁白屏幕字幕：在共享字幕安全区内单行、逐字亮起，无底板。
 *
 * 与夜曲的整行淡入不同，寓言逐字亮起：每字 0.16s，错开 0.07s，
 * 由帧号换算，不做 CSS 动画。有旁白的作品不要导入本组件。
 */
import {T, alpha, color, envelope, useFableFrame} from './kit';

export type ScreenSubtitleItem = {startFrame: number; endFrame: number; text: string};

export type ScreenSubtitleProps = {
  items: ScreenSubtitleItem[];
  frame?: number;
  safeArea: {x: number; y: number; width: number; height: number};
  size?: number;
  color?: string;
  fps?: number;
  /** 每字亮起时长与字间错开时长，单位秒。 */
  riseSeconds?: number;
  staggerSeconds?: number;
};

export default function ScreenSubtitle({
  items, frame, safeArea, size = T.type.subtitle, color: textColor = color('ink'),
  fps = (typeof window === 'undefined' ? undefined : window.__M2V_CODE_CONFIG__?.fps) ?? 30,
  riseSeconds = T.motion.subtitleRiseSeconds, staggerSeconds = T.motion.subtitleStaggerSeconds,
}: ScreenSubtitleProps) {
  const contextFrame = useFableFrame();
  const activeFrame = frame ?? contextFrame;
  for (const item of items) {
    if (!item.text.trim()) throw new Error('屏幕字幕不能为空');
    if (!Number.isFinite(item.startFrame) || !Number.isFinite(item.endFrame) || item.startFrame >= item.endFrame) {
      throw new Error(`屏幕字幕窗口无效：${item.text}`);
    }
  }
  const active = items.find(item => activeFrame >= item.startFrame && activeFrame < item.endFrame);
  if (!active) return null;
  const raise = Math.max(1, Math.round(riseSeconds * fps));
  const stagger = Math.max(0, Math.round(staggerSeconds * fps));
  const characters = [...active.text];
  // 整句在剩余窗口内必须显完：字越多，每字越快，不超过声明的 stagger。
  const room = Math.max(1, (active.endFrame - active.startFrame) - raise);
  const step = characters.length > 1 ? Math.min(stagger, Math.floor(room / (characters.length - 1))) : 0;
  const opacity = envelope(activeFrame, active.startFrame, active.endFrame, Math.round(0.16 * fps));
  return (
    <div style={{
      position: 'absolute', left: safeArea.x, top: safeArea.y, width: safeArea.width, height: safeArea.height,
      display: 'flex', alignItems: 'center', justifyContent: 'center', opacity, pointerEvents: 'none',
      fontFamily: T.type.fontStack, fontSize: size, fontWeight: 700,
      letterSpacing: `${T.type.subtitleTrack}em`, color: textColor, whiteSpace: 'nowrap',
      textShadow: '0 3px 10px rgba(0,0,0,.6)',
    }}>
      {characters.map((character, index) => {
        const at = active.startFrame + index * step;
        const lit = Math.min(1, Math.max(0, (activeFrame - at) / raise));
        return (
          <span key={index} style={{opacity: 0.14 + 0.86 * lit}}>{character}</span>
        );
      })}
    </div>
  );
}

/** 字幕颜色辅助：关键词用金色、过量刺激用红色，由作品在词级决定。 */
export function subtitleTone(tone: 'gold' | 'red' | 'ink' = 'ink'): string {
  if (tone === 'gold') return alpha(color('gold'), 1);
  if (tone === 'red') return color('red');
  return color('ink');
}
