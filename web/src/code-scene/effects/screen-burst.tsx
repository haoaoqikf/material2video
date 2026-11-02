/**
 * 整屏粒子层：透明 Canvas 2D 覆盖层，用闭式粒子 + 预渲染 sprite 绘制爆散。
 *
 * 位置、尺寸、透明度只由 `frame`、`progress` 与显式 seed 求值；不读挂钟、
 * `Math.random`、上一帧状态或 rAF。sprite 只做柔光/虚化观感，颜色、数量与
 * 事件时刻全部由调用方传入。
 */
import {useLayoutEffect, useRef, type ReactElement} from 'react';
import {explosionField, expandingRings, impactEnvelope, moteField, type Vec2} from '../dynamics';
import {motionCurve} from '../motion';

export type BurstColor = {core: string; primary: string; secondary: string};

export type BurstSpec = {
  id: string;
  origin: Vec2;
  startFrame: number;
  durationFrames: number;
  count: number;
  reach: number;
  color: BurstColor;
  seed?: string;
  /** 0–1；叠加在整组上的总透明度。 */
  opacity?: number;
  bokehRatio?: number;
  streakRatio?: number;
  dustRatio?: number;
  lifetime?: number;
  drag?: number;
  gravity?: number;
  rings?: {count: number; travel: number; thickness: number; opacity: number};
  /** 0–1；核心闪光的最大不透明度。 */
  flash?: number;
};

export type DustSpec = {
  count: number;
  opacity: number;
  drift: number;
  seed?: string;
  size?: number;
  cycles?: number;
};

export type ScreenBurstLayerProps = {
  frame: number;
  width: number;
  height: number;
  bursts: readonly BurstSpec[];
  dust?: DustSpec;
  /** 用于微尘相位；默认按 1740 帧的全片。 */
  totalFrames?: number;
  /** 外部整体缩放（如缓慢推近）；用于分配足够的后备缓冲，默认 1。 */
  overscan?: number;
  /** 从该 y 坐标向下淡出粒子，保护字幕；默认 82% 画高。 */
  maskBottom?: number;
};

type SpriteKind = 'core' | 'soft' | 'bokeh' | 'streak';

const spriteCache = new Map<string, HTMLCanvasElement>();

function rgba(hex: string, alpha: number): string {
  const raw = hex.replace('#', '');
  const full = raw.length === 3 ? raw.split('').map(char => char + char).join('') : raw;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) return `rgba(255,255,255,${alpha})`;
  const value = parseInt(full, 16);
  return `rgba(${(value >> 16) & 255},${(value >> 8) & 255},${value & 255},${alpha})`;
}

function makeSprite(kind: SpriteKind, color: string): HTMLCanvasElement {
  const key = `${kind}:${color}`;
  const cached = spriteCache.get(key);
  if (cached) return cached;
  const size = kind === 'bokeh' ? 256 : kind === 'streak' ? 128 : 96;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  ctx.clearRect(0, 0, size, size);
  if (kind === 'streak') {
    const gradient = ctx.createLinearGradient(0, 0, size, 0);
    gradient.addColorStop(0, rgba(color, 0));
    gradient.addColorStop(0.35, rgba(color, 0.55));
    gradient.addColorStop(0.5, rgba('#FFFFFF', 0.95));
    gradient.addColorStop(0.65, rgba(color, 0.55));
    gradient.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = gradient;
    ctx.fillRect(0, size * 0.3, size, size * 0.4);
  } else {
    const radius = size / 2;
    const gradient = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
    if (kind === 'bokeh') {
      gradient.addColorStop(0, rgba(color, 0.34));
      gradient.addColorStop(0.55, rgba(color, 0.18));
      gradient.addColorStop(0.82, rgba(color, 0.06));
      gradient.addColorStop(1, rgba(color, 0));
    } else if (kind === 'core') {
      gradient.addColorStop(0, rgba('#FFFFFF', 0.98));
      gradient.addColorStop(0.22, rgba(color, 0.9));
      gradient.addColorStop(0.6, rgba(color, 0.35));
      gradient.addColorStop(1, rgba(color, 0));
    } else {
      gradient.addColorStop(0, rgba(color, 0.55));
      gradient.addColorStop(0.5, rgba(color, 0.2));
      gradient.addColorStop(1, rgba(color, 0));
    }
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  }
  spriteCache.set(key, canvas);
  return canvas;
}

function screenScale(): number {
  const config = (window as unknown as {__M2V_CODE_CONFIG__?: {captureScale?: number}})
    .__M2V_CODE_CONFIG__;
  const value = config?.captureScale;
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 1;
}

function drawDust(
  ctx: CanvasRenderingContext2D, frame: number, totalFrames: number, width: number, height: number,
  dust: DustSpec | undefined, opacity: number,
) {
  if (!dust || dust.count <= 0) return;
  const motes = moteField({
    count: dust.count, progress: frame / Math.max(1, totalFrames - 1),
    seed: dust.seed ?? 'screen-dust',
    width, height, drift: dust.drift, size: dust.size ?? 1.2, opacity: dust.opacity,
    cycles: dust.cycles ?? 4,
  });
  const sprite = makeSprite('soft', '#E6BE55');
  ctx.globalCompositeOperation = 'lighter';
  for (const mote of motes) {
    const size = Math.max(2, mote.size * 6);
    ctx.globalAlpha = mote.opacity * opacity;
    ctx.drawImage(sprite, mote.x - size / 2, mote.y - size / 2, size, size);
  }
}

function drawBurst(
  ctx: CanvasRenderingContext2D, burst: BurstSpec, progress: number, opacity: number,
) {
  const envelope = impactEnvelope(progress);
  const particles = explosionField({
    count: burst.count, progress, seed: burst.seed ?? burst.id, origin: burst.origin,
    reach: burst.reach, lifetime: burst.lifetime ?? 0.85, drag: burst.drag ?? 0.9,
    gravity: burst.gravity ?? 40, bokehRatio: burst.bokehRatio ?? 0.12,
    streakRatio: burst.streakRatio ?? 0.08, dustRatio: burst.dustRatio ?? 0.06,
    easing: motionCurve('easeInOutSine'),
  });
  const {core, primary, secondary} = burst.color;
  ctx.globalCompositeOperation = 'lighter';
  if (burst.flash && envelope.flash > 0) {
    const radius = burst.reach * 0.65;
    const gradient = ctx.createRadialGradient(
      burst.origin.x, burst.origin.y, 0, burst.origin.x, burst.origin.y, radius,
    );
    gradient.addColorStop(0, rgba(core, 0.55));
    gradient.addColorStop(0.35, rgba(primary, 0.22));
    gradient.addColorStop(1, rgba(primary, 0));
    ctx.globalAlpha = envelope.flash * burst.flash * opacity;
    ctx.fillStyle = gradient;
    ctx.fillRect(burst.origin.x - radius, burst.origin.y - radius, radius * 2, radius * 2);
  }
  if (burst.rings) {
    const rings = expandingRings({
      count: burst.rings.count, progress, baseRadius: 8, travel: burst.rings.travel,
      thickness: burst.rings.thickness, life: 0.9, stagger: 0.34,
      easing: motionCurve('easeOutCubic'),
    });
    ctx.strokeStyle = rgba(primary, 0.7);
    for (const ring of rings) {
      ctx.globalAlpha = ring.opacity * burst.rings.opacity * opacity;
      ctx.lineWidth = ring.width;
      ctx.beginPath();
      ctx.arc(burst.origin.x, burst.origin.y, ring.radius, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
  for (const particle of particles) {
    if (particle.opacity <= 0) continue;
    const kind: SpriteKind = particle.layer === 'bokeh' ? 'bokeh'
      : particle.layer === 'dust' ? 'soft'
        : particle.layer === 'shell' ? 'streak' : 'core';
    const color = particle.layer === 'bokeh'
      ? (particle.index % 3 === 0 ? secondary : primary)
      : primary;
    const sprite = makeSprite(kind, color);
    ctx.globalAlpha = particle.opacity * opacity;
    const size = particle.size * (0.7 + particle.depth * 0.6);
    if (kind === 'streak' && particle.streak > 0) {
      ctx.save();
      ctx.translate(particle.x, particle.y);
      ctx.rotate(particle.angle);
      ctx.drawImage(sprite, -particle.streak / 2, -size * 0.75,
        particle.streak, size * 1.5);
      ctx.restore();
    } else {
      ctx.drawImage(sprite, particle.x - size / 2, particle.y - size / 2, size, size);
    }
  }
}

export function ScreenBurstLayer({
  frame, width, height, bursts, dust, totalFrames = 1740, overscan = 1,
  maskBottom = height * 0.82,
}: ScreenBurstLayerProps): ReactElement {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scale = screenScale() * Math.max(1, overscan);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const bufferWidth = Math.max(1, Math.round(width * scale));
    const bufferHeight = Math.max(1, Math.round(height * scale));
    if (canvas.width !== bufferWidth || canvas.height !== bufferHeight) {
      canvas.width = bufferWidth;
      canvas.height = bufferHeight;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, bufferWidth, bufferHeight);
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    drawDust(ctx, frame, totalFrames, width, height, dust, 1);
    for (const burst of bursts) {
      const progress = (frame - burst.startFrame) / Math.max(1, burst.durationFrames - 1);
      if (progress < 0 || progress > 1) continue;
      drawBurst(ctx, burst, progress, burst.opacity ?? 1);
    }
    if (maskBottom < height) {
      ctx.globalCompositeOperation = 'destination-out';
      const gradient = ctx.createLinearGradient(0, maskBottom, 0, height);
      gradient.addColorStop(0, 'rgba(0,0,0,0)');
      gradient.addColorStop(1, 'rgba(0,0,0,0.92)');
      ctx.globalAlpha = 1;
      ctx.fillStyle = gradient;
      ctx.fillRect(0, maskBottom, width, height - maskBottom);
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
  }, [frame, totalFrames, width, height, scale, bursts, dust, maskBottom]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      style={{
        position: 'absolute', inset: 0, width, height, pointerEvents: 'none',
        mixBlendMode: 'screen',
      }}
    />
  );
}
