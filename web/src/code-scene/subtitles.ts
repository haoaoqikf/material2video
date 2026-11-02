/**
 * 屏幕字幕的共享时间与切分工具：激活窗口、行模型、进出包络与关键词切分。
 *
 * 只处理时间与字符串，不绑定字体、颜色、字号或视觉风格。逐字/逐词动画由
 * 调用方用 `staggerReveal` 或自己的几何决定；本文件不读帧号之外的时钟。
 */
import {clampProgress} from './primitives';
import {easeMotion} from './motion';

export type ScreenSubtitleItem = {startFrame: number; endFrame: number; text: string};
export type TextSegment = {text: string; emphasis: boolean};

/** 当前窗口内的字幕；窗口左闭右开，重叠时取第一条，调用方应避免重叠。 */
export function activeScreenSubtitle(
  items: readonly ScreenSubtitleItem[], frame: number,
): ScreenSubtitleItem | null {
  return items.find(item => frame >= item.startFrame && frame < item.endFrame) ?? null;
}

/** 按换行切行；超过上限时明确失败，不静默截断。 */
export function splitScreenSubtitle(text: string, maxLines = 2): string[] {
  if (typeof text !== 'string' || !text.trim()) throw new Error('屏幕字幕不能为空');
  const lines = text.split('\n');
  if (lines.length > maxLines) throw new Error(`屏幕字幕最多 ${maxLines} 行：${text}`);
  return lines;
}

/**
 * 进出包络：进入用 easeOutCubic，退出用 easeInOutSine；两者取较小值。
 *
 * `minVisible` 只在窗口内生效，给按帧文字量测保留可识别下限；窗口外为 0。
 * 它不是“视觉上永远 55%”的旧包络，组件仍可在窗口内做位移、遮罩与逐字。
 */
export function screenSubtitleEnvelope({
  frame, startFrame, endFrame, enterFrames = 8, exitFrames = 8, minVisible = 0.2,
}: {
  frame: number; startFrame: number; endFrame: number;
  enterFrames?: number; exitFrames?: number; minVisible?: number;
}): number {
  if (frame < startFrame || frame >= endFrame) return 0;
  // 窗口较短时压缩进/出时长，保证中间至少有一个满亮帧，不让两段包络互相吃掉。
  const half = Math.max(1, Math.floor((endFrame - startFrame) / 2));
  const enterFramesSafe = Math.min(Math.max(1, enterFrames), half);
  const exitFramesSafe = Math.min(Math.max(1, exitFrames), half);
  const enter = easeMotion('easeOutCubic', clampProgress((frame - startFrame) / enterFramesSafe));
  const exit = 1 - easeMotion('easeInOutSine',
    clampProgress((frame - (endFrame - exitFramesSafe)) / exitFramesSafe));
  return Math.max(Math.min(1, Math.max(0, minVisible)), Math.min(enter, exit));
}

/**
 * 按正则切出可高亮片段；不改变文本内容与空白，只标记 emphasis。
 *
 * 模式没有 `g` 标志时会复制一个带 `g` 的正则；零宽匹配被跳过，避免死循环。
 */
export function splitEmphasis(text: string, pattern?: RegExp): TextSegment[] {
  if (!pattern) return [{text, emphasis: false}];
  const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
  const global = new RegExp(pattern.source, flags);
  const segments: TextSegment[] = [];
  let cursor = 0;
  for (const match of text.matchAll(global)) {
    const index = match.index ?? 0;
    if (!match[0]) continue;
    if (index > cursor) segments.push({text: text.slice(cursor, index), emphasis: false});
    segments.push({text: match[0], emphasis: true});
    cursor = index + match[0].length;
  }
  if (cursor < text.length) segments.push({text: text.slice(cursor), emphasis: false});
  return segments.length ? segments : [{text, emphasis: false}];
}
