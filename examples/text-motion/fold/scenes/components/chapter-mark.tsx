/**
 * 章节标：左上角的结构标记，编号 + 单字 +（可选）西文 + 细线。
 * 只作结构识别，不解释画面；默认低亮度、小字号，不争夺主体焦点。
 */
import {T, color, frameProgress, useNightFrame} from './kit';

export type ChapterMarkProps = {
  index: number | string;
  character: string;
  latin?: string;
  x?: number;
  y?: number;
  opacity?: number;
  frame?: number;
  startFrame?: number;
};

export default function ChapterMark({
  index, character, latin, x = 72, y = 64, opacity = 0.42, frame, startFrame = 0,
}: ChapterMarkProps) {
  const contextFrame = useNightFrame();
  const activeFrame = frame ?? contextFrame;
  const reveal = frameProgress(activeFrame, startFrame, T.motion.chapterFadeFrames);
  const number = typeof index === 'number' ? String(index).padStart(2, '0') : index;
  return (
    <div style={{
      position: 'absolute', left: x, top: y, opacity: opacity * reveal,
      display: 'flex', alignItems: 'baseline', gap: 12, pointerEvents: 'none',
      color: color('muted'), whiteSpace: 'nowrap',
    }}>
      <span style={{
        fontFamily: '"JetBrains Mono", "SF Mono", ui-monospace, monospace',
        fontSize: T.type.chapterNumber, letterSpacing: '0.18em', color: color('gold'),
      }}>{number}</span>
      <span style={{
        fontFamily: '"Vibe Night Serif", "Noto Serif SC", serif',
        fontSize: T.type.chapterCharacter, letterSpacing: '0.12em', color: color('text'),
      }}>{character}</span>
      {latin ? (
        <span style={{
          fontFamily: '"JetBrains Mono", "SF Mono", ui-monospace, monospace',
          fontSize: T.type.chapterNumber, letterSpacing: '0.22em', color: color('muted'),
        }}>{latin}</span>
      ) : null}
      <span style={{
        display: 'inline-block', width: 250, height: 1, marginLeft: 4,
        background: `linear-gradient(90deg, ${color('muted')}66, ${color('muted')}00)`,
      }}/>
    </div>
  );
}
