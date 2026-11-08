/**
 * 画幅与字幕几何：与 Python 的 `m2v.engine.frames` 读**同一份** `frames.json`。
 *
 * 过去字幕盒写在 `tokens.css`、量测边界又各写一份常量，「改一个值」只会改到画面
 * 那一半。现在安全区、字号、行高与底板颜色只有这一处真源；准备阶段把解析结果
 * 注入 composition 的 props 与作品 SDK 的录制配置，前端另外只在注册 composition
 * 的占位默认值里用到它。
 */
import spec from './frames.json';

export type SubtitleSafeArea = {x: number; y: number; width: number; height: number};
/** 字幕样式独立于作品配色：白字配不透明深色底板，保证任何作品背景上都可读。 */
export type SubtitleStyle = {
  safeArea: SubtitleSafeArea;
  fontSize: number;
  lineHeight: number;
  textColor: string;
  plateColor: string;
};
export type Frame = {width: number; height: number; subtitle: SubtitleStyle};

const FRAMES: Frame[] = spec.frames.map(frame => ({
  width: frame.width,
  height: frame.height,
  subtitle: {
    safeArea: {
      x: frame.subtitle.x,
      y: frame.subtitle.y,
      width: frame.subtitle.width,
      height: frame.subtitle.height,
    },
    fontSize: frame.subtitle.fontSize,
    lineHeight: frame.subtitle.lineHeight,
    textColor: frame.subtitle.textColor,
    plateColor: frame.subtitle.plateColor,
  },
}));

/** 某个画幅的取值；未支持的组合直接失败，不静默落回某一档。 */
export function frameOf(width: number, height: number): Frame {
  const found = FRAMES.find(frame => frame.width === width && frame.height === height);
  if (!found) throw new Error(`画幅清单里没有 ${width}×${height}`);
  return found;
}

/** 尺寸均省略时使用的画幅，与清单的 `default` 保持一致。 */
export const DEFAULT_FRAME: Frame = FRAMES.find(frame => `${frame.width}x${frame.height}` === spec.default) ?? FRAMES[0];
