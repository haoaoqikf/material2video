/**
 * 点阵片名卡：把标题文字采样成固定数量的点，点从散落到目标位置聚成字。
 * 文字采样在宋体就绪后同步完成；动画只由帧号推进，不使用计时器。
 */
import {useMemo} from 'react';
import {T, SERIF_FAMILY, clamp01, color, randomFor, useNightFrame, useNightSerif} from './kit';

export type TitleNightProps = {
  text: string;
  width: number;
  height: number;
  frame?: number;
  startFrame?: number;
  durationFrames?: number;
  size?: number;
  x?: number;
  y?: number;
  color?: string;
  dotSize?: number;
  spread?: number;
  seed?: string;
  role?: string;
  state?: string;
};

type Dot = {x: number; y: number; startX: number; startY: number; delay: number; radius: number; ice: boolean};

export default function TitleNight({
  text, width, height, frame, startFrame = 0, durationFrames = 34, size = T.type.title,
  x, y, color: dotColor = color('text'), dotSize = 2.1, spread = 520, seed = 'title-night', role, state,
}: TitleNightProps) {
  const contextFrame = useNightFrame();
  const activeFrame = frame ?? contextFrame;
  const loaded = useNightSerif();
  const centerX = x ?? width / 2;
  const centerY = y ?? height * 0.42;

  const dots = useMemo<Dot[]>(() => {
    if (!loaded || typeof document === 'undefined') return [];
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d', {willReadFrequently: true});
    if (!context) return [];
    const font = `400 ${size}px "${SERIF_FAMILY}", "Noto Serif SC", serif`;
    context.font = font;
    const measured = context.measureText(text);
    const padding = Math.ceil(size * 0.4);
    canvas.width = Math.max(1, Math.ceil(measured.width + padding * 2));
    canvas.height = Math.max(1, Math.ceil(size * 1.8));
    context.font = font;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillStyle = '#FFFFFF';
    context.fillText(text, canvas.width / 2, canvas.height / 2);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let step = Math.max(3, Math.round(size / 28));
    let targets: {x: number; y: number}[] = [];
    const collect = () => {
      targets = [];
      for (let py = 0; py < canvas.height; py += step) {
        for (let px = 0; px < canvas.width; px += step) {
          if (pixels[(py * canvas.width + px) * 4 + 3] > 140) {
            targets.push({x: px - canvas.width / 2, y: py - canvas.height / 2});
          }
        }
      }
    };
    collect();
    while (targets.length > 3000 && step < 14) {
      step += 1;
      collect();
    }
    const random = randomFor(seed);
    return targets.map((target, index) => ({
      x: target.x,
      y: target.y,
      startX: (random() - 0.5) * spread * 2,
      startY: (random() - 0.5) * spread * 2,
      delay: random() * 0.45,
      radius: dotSize * (0.65 + random() * 0.75),
      ice: index % 11 === 0,
    }));
  }, [loaded, text, size, seed, spread, dotSize]);

  const local = activeFrame - startFrame;
  const duration = Math.max(1, durationFrames);
  const flyFrames = duration * 0.55;
  const estimatedWidth = Math.max(1, [...text].length * size * 1.14);
  const estimatedHeight = Math.max(1, size * 1.4);
  return (
    <div style={{position: 'absolute', inset: 0, width, height, pointerEvents: 'none'}}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position: 'absolute', inset: 0}}>
        {dots.map((dot, index) => {
          const progress = clamp01((local - dot.delay * duration) / flyFrames);
          const eased = progress * progress * (3 - 2 * progress);
          const cx = centerX + dot.startX + (dot.x - dot.startX) * eased;
          const cy = centerY + dot.startY + (dot.y - dot.startY) * eased;
          const settle = eased >= 1 ? 0.9 + 0.1 * Math.sin(activeFrame * 0.06 + index) : 1;
          return (
            <circle
              key={index}
              cx={cx}
              cy={cy}
              r={dot.radius}
              fill={dot.ice ? color('ice') : dotColor}
              opacity={(0.08 + 0.92 * eased) * settle}
            />
          );
        })}
      </svg>
      {role ? (
        <div data-m2v-role={role} data-m2v-state={state} style={{
          position: 'absolute', left: centerX - estimatedWidth / 2, top: centerY - estimatedHeight / 2,
          width: estimatedWidth, height: estimatedHeight, fontSize: size, pointerEvents: 'none',
        }}/>
      ) : null}
    </div>
  );
}
