/**
 * 无旁白屏幕字幕：安全区内的中英双语，中文逐字展开、英文延迟进入、关键词高亮。
 *
 * `text` 以换行分成两行：第一行中文，第二行英文短标签。英文只做纹理，不逐字
 * 直译。所有动画由帧号求值；逐字 span 不改变文本内容、换行、字号或安全区。
 */
import type {ReactNode} from 'react';
import {
  activeScreenSubtitle, motionCurve, screenSubtitleEnvelope, splitEmphasis,
  splitScreenSubtitle, staggerReveal,
} from 'm2v/code-scene';
import {clamp01, LATIN, SANS, T} from './kit';

export type ScreenSubtitleItem = {startFrame: number; endFrame: number; text: string};
export type SubtitleVariant = {
  enter?: 'rise' | 'settle' | 'wipe';
  exit?: 'drift' | 'dissolve' | 'mask';
  enterFrames?: number;
  exitFrames?: number;
  englishDelayFrames?: number;
};
export type ScreenSubtitleProps = {
  items: ScreenSubtitleItem[];
  frame: number;
  safeArea: {x: number; y: number; width: number; height: number};
  size?: number;
  enSize?: number;
  color?: string;
  enColor?: string;
  role?: string;
  emphasis?: RegExp;
  glow?: number;
  variants?: Record<number, SubtitleVariant>;
  enterFrames?: number;
  exitFrames?: number;
  risePx?: number;
  driftPx?: number;
  englishDelayFrames?: number;
  /** 节拍脉冲（0–1），只加强关键词的辉光与轻微缩放，不改变字号与换行。 */
  pulse?: number;
  /** 0–1 相位；逐字轻微亮度呼吸，不改变布局。 */
  shimmer?: number;
};

const MAX_ZH = 30;
const MAX_EN = 70;

function emphasisColor(emphasis: boolean, normal: string): string {
  return emphasis ? T.colors.gold : normal;
}

function glowShadow(amount: number): string {
  if (amount <= 0) return 'none';
  return `0 0 ${Math.round(4 + amount * 14)}px rgba(230, 190, 85, ${0.18 + amount * 0.22})`;
}

export default function ScreenSubtitle({
  items, frame, safeArea, size = T.subtitles.zh, enSize = T.subtitles.en,
  color = T.colors.ivory, enColor = T.colors.muted, role = 'screen-subtitle',
  emphasis, glow = T.subtitleMotion.glow, variants,
  enterFrames: enterFramesProp = T.subtitleMotion.enterFrames,
  exitFrames: exitFramesProp = T.subtitleMotion.exitFrames,
  risePx: risePxProp = T.subtitleMotion.risePx,
  driftPx: driftPxProp = T.subtitleMotion.driftPx,
  englishDelayFrames: englishDelayProp = T.subtitleMotion.englishDelayFrames,
  pulse = 0, shimmer = 0,
}: ScreenSubtitleProps) {
  for (const item of items) {
    if (!item.text.trim()) throw new Error('屏幕字幕不能为空');
    const lines = splitScreenSubtitle(item.text, 2);
    if ([...lines[0]].length > MAX_ZH) throw new Error(`屏幕字幕中文超过 ${MAX_ZH} 字：${lines[0]}`);
    if (lines[1] && [...lines[1]].length > MAX_EN) throw new Error(`屏幕字幕英文超过 ${MAX_EN} 字：${lines[1]}`);
    if (!Number.isFinite(item.startFrame) || !Number.isFinite(item.endFrame) || item.startFrame >= item.endFrame) {
      throw new Error(`屏幕字幕窗口无效：${item.text}`);
    }
  }
  const active = activeScreenSubtitle(items, frame);
  if (!active) return null;
  const [zh, en] = splitScreenSubtitle(active.text, 2);
  const variant = variants?.[active.startFrame] ?? {};
  const enterFrames = variant.enterFrames ?? enterFramesProp;
  const exitFrames = variant.exitFrames ?? exitFramesProp;
  const risePx = risePxProp;
  const driftPx = driftPxProp;
  const englishDelayFrames = variant.englishDelayFrames ?? englishDelayProp;
  const opacity = screenSubtitleEnvelope({
    frame, startFrame: active.startFrame, endFrame: active.endFrame, enterFrames, exitFrames,
  });
  const enter = motionCurve('easeOutCubic')(clamp01((frame - active.startFrame) / Math.max(1, enterFrames)));
  const exit = motionCurve('easeInOutSine')(clamp01(
    (frame - (active.endFrame - exitFrames)) / Math.max(1, exitFrames)));
  const enterMode = variant.enter ?? 'rise';
  const exitMode = variant.exit ?? 'drift';
  // 逐字步长按「每字间隔帧数」换算成窗口内比例：字越多、间隔越长，展开越缓。
  // 未展开的字保持全透明，观众看到文字从左到右长出来，而不是整句先灰后亮。
  const charCount = [...zh].length;
  const staggerSpan = Math.max(0, charCount - 1) * T.subtitleMotion.charStaggerFrames;
  const staggerSpread = staggerSpan > 0
    ? clamp01(staggerSpan / (enterFrames + staggerSpan))
    : 0;
  const reveal = staggerReveal({
    count: charCount, progress: enter, stagger: staggerSpread, easing: motionCurve('easeOutCubic'),
  });
  let index = 0;
  const zhNodes: ReactNode[] = [];
  splitEmphasis(zh, emphasis).forEach((segment, segmentIndex) => {
    [...segment.text].forEach((character, characterIndex) => {
      const progress = enterMode === 'wipe' ? 1 : reveal[index] ?? 1;
      index += 1;
      zhNodes.push(
        <span key={`${segmentIndex}-${characterIndex}`} style={{
          display: 'inline-block',
          opacity: progress * (0.92 + 0.08 * Math.sin(Math.PI * 2 * (shimmer + index * 0.055))),
          transform: `translateY(${(1 - progress) * risePx * (enterMode === 'settle' ? 0.5 : 1)}px)`
            + (segment.emphasis ? ` scale(${1 + pulse * 0.035})` : ''),
          color: emphasisColor(segment.emphasis, color),
          textShadow: glowShadow(glow * progress * (1 + (segment.emphasis ? pulse : pulse * 0.2))),
        }}>{character}</span>,
      );
    });
  });
  const enStart = active.startFrame + Math.min(englishDelayFrames,
    Math.max(0, (active.endFrame - active.startFrame) - enterFrames));
  const enProgress = motionCurve('easeOutCubic')(clamp01((frame - enStart) / Math.max(1, enterFrames)));
  const enNodes = en ? splitEmphasis(en, emphasis).map((segment, segmentIndex) => (
    <span key={segmentIndex} style={{
      color: emphasisColor(segment.emphasis, enColor),
      textShadow: glowShadow(glow * enProgress * 0.6),
    }}>{segment.text}</span>
  )) : [];
  const zhClip = enterMode === 'wipe' ? `inset(0 ${Math.round((1 - enter) * 100)}% 0 0)` : undefined;
  const exitClip = exitMode === 'mask' ? `inset(0 0 ${Math.round(exit * 100)}% 0)` : undefined;
  const drift = exitMode === 'drift' ? driftPx * exit : 0;
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute', left: safeArea.x, top: safeArea.y,
        width: safeArea.width, height: safeArea.height,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        textAlign: 'center', opacity, whiteSpace: 'nowrap', pointerEvents: 'none',
        transform: `translateY(${drift}px)`, clipPath: exitClip,
      }}
    >
      <div style={{
        fontFamily: SANS, fontSize: size, lineHeight: 1.3, letterSpacing: '0.04em',
        color, whiteSpace: 'nowrap',
      }}>
        <div style={{clipPath: zhClip}}>{zhNodes}</div>
      </div>
      {en ? (
        <div style={{
          fontFamily: LATIN, fontSize: enSize, lineHeight: 1.3, letterSpacing: '0.14em',
          textTransform: 'uppercase', color: enColor, marginTop: T.subtitles.lineGap,
          opacity: enProgress,
          transform: `translateY(${(1 - enProgress) * risePx * 0.6}px)`,
        }}>{enNodes}</div>
      ) : null}
    </div>
  );
}
