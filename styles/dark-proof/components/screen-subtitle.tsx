/**
 * 无旁白屏幕字幕：在共享字幕安全区内自绘中英双语，不进入共享字幕层。
 *
 * `text` 以换行分成两行：第一行中文，第二行英文短标签。英文只做纹理，不逐字
 * 直译；两行都使用宿主已注册字体。有旁白的作品不要导入本组件。
 */
import {envelope, LATIN, SANS, T} from './kit';

export type ScreenSubtitleItem = {startFrame: number; endFrame: number; text: string};

export type ScreenSubtitleProps = {
  items: ScreenSubtitleItem[];
  frame: number;
  safeArea: {x: number; y: number; width: number; height: number};
  size?: number;
  enSize?: number;
  color?: string;
  enColor?: string;
  fps?: number;
  fadeFrames?: number;
  role?: string;
};

const MAX_ZH = 30;
const MAX_EN = 70;

export default function ScreenSubtitle({
  items, frame, safeArea, size = T.subtitles.zh, enSize = T.subtitles.en,
  color = T.colors.ivory, enColor = T.colors.muted,
  fps = (typeof window === 'undefined' ? 30 : window.__M2V_CODE_CONFIG__?.fps) ?? 30,
  fadeFrames = Math.round(0.2 * fps), role = 'screen-subtitle',
}: ScreenSubtitleProps) {
  for (const item of items) {
    if (!item.text.trim()) throw new Error('屏幕字幕不能为空');
    const lines = item.text.split('\n');
    if (lines.length > 2) throw new Error(`屏幕字幕最多两行：${item.text}`);
    if ([...lines[0]].length > MAX_ZH) throw new Error(`屏幕字幕中文超过 ${MAX_ZH} 字：${lines[0]}`);
    if (lines[1] && [...lines[1]].length > MAX_EN) throw new Error(`屏幕字幕英文超过 ${MAX_EN} 字：${lines[1]}`);
    if (!Number.isFinite(item.startFrame) || !Number.isFinite(item.endFrame) || item.startFrame >= item.endFrame) {
      throw new Error(`屏幕字幕窗口无效：${item.text}`);
    }
  }
  const active = items.find(item => frame >= item.startFrame && frame < item.endFrame);
  if (!active) return null;
  const [zh, en] = active.text.split('\n');
  const opacity = envelope(frame, active.startFrame, active.endFrame, fadeFrames);
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute', left: safeArea.x, top: safeArea.y,
        width: safeArea.width, height: safeArea.height,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        textAlign: 'center', opacity, whiteSpace: 'nowrap', pointerEvents: 'none',
      }}
    >
      <div style={{
        fontFamily: SANS, fontSize: size, lineHeight: 1.3, letterSpacing: '0.04em', color,
      }}>{zh}</div>
      {en ? (
        <div style={{
          fontFamily: LATIN, fontSize: enSize, lineHeight: 1.3, letterSpacing: '0.14em',
          textTransform: 'uppercase', color: enColor, marginTop: T.subtitles.lineGap,
        }}>{en}</div>
      ) : null}
    </div>
  );
}
