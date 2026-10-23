/**
 * 人生五选择：七幕、60 秒、1920×1080 的 2.5D 横屏时间轴。
 *
 * 画面由 render.ts 在 Canvas 上逐帧同步绘制；大字由 DOM 层排版。
 * 所有时间变化只读 elapsedSeconds，不读挂钟、不使用 CSS 动画。
 */
import {useEffect, useLayoutEffect, useRef} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {drawFrame, type CopyItem, type LifeProps} from './render';
import {span} from './geometry';

const TONE: Record<CopyItem['tone'], string> = {
  primary: '#f4f7fb',
  secondary: '#9aa7b4',
  accent: '#cfe4ff',
};

function CopyLayer({items, t}: {items: CopyItem[]; t: number}) {
  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 2}}>
      {items.map((item) => {
        const inP = span(t, item.from, item.from + 0.55);
        const outP = span(t, item.to - 0.55, item.to);
        const holdToEnd = item.to >= 59.99;
        const opacity = inP * (holdToEnd ? 1 : 1 - outP);
        if (opacity <= 0.001) return null;
        const giant = item.size >= 150;
        const transform = giant
          ? `translateY(${(1 - inP) * 8}px) scale(${0.975 + 0.025 * inP})`
          : `translateY(${(1 - inP) * 10}px)`;
        return (
          <div
            key={item.id}
            style={{
              position: 'absolute',
              left: item.x,
              top: item.y,
              width: item.width,
              textAlign: item.align,
              color: TONE[item.tone] ?? TONE.primary,
              fontSize: item.size,
              fontWeight: item.weight,
              letterSpacing: item.spacing,
              lineHeight: 1.2,
              opacity,
              transform,
              transformOrigin: 'center center',
              textShadow: '0 4px 30px rgba(0, 0, 0, 0.92)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {item.text}
          </div>
        );
      })}
    </div>
  );
}

export default function Life(config: CodeSceneProps) {
  const clock = useSceneContext();
  const canvas = useRef<HTMLCanvasElement>(null);
  const props = config.props as unknown as LifeProps;
  if (!props || !Array.isArray(props.copy) || !props.labels) {
    throw new Error('人生五选择缺少 content.props.copy 或 content.props.labels');
  }
  const scale = config.captureScale ?? 1;
  // stillT 只用于临时检查项目的单帧取样；正式分镜不写该字段。
  const t = typeof props.stillT === 'number' ? props.stillT : clock.elapsedSeconds;

  useEffect(() => {
    clock.ready();
  }, []);

  useLayoutEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const ctx = element.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    drawFrame(ctx, t, config.width, config.height, props);
  }, [t, clock.running, scale, config.width, config.height, props]);

  return (
    <div style={{
      position: 'relative',
      width: config.width,
      height: config.height,
      overflow: 'hidden',
      background: '#05070a',
    }}>
      <canvas
        ref={canvas}
        width={Math.round(config.width * scale)}
        height={Math.round(config.height * scale)}
        style={{position: 'absolute', inset: 0, width: config.width, height: config.height,
          display: 'block'}}
      />
      <CopyLayer items={props.copy} t={t}/>
    </div>
  );
}
