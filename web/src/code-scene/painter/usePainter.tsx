/**
 * 绘制层的 React 绑定：一块按采集像素密度分配后备缓冲的画布，外加同源的量测代理。
 *
 * 与既有 `Canvas`（R3F/WebGL）区分：这是 2D，用于辉光质感、高密度粒子、
 * 线条生长与逐字显影这类镜头；需要可选中文本、就地排版与风格包组件时仍用
 * DOM/SVG，需要真实三维与后期时仍用 three。
 *
 * 像素密度取自录制配置：`lookdev` 的 2 倍原生采集要求后备缓冲达到逻辑尺寸的
 * 两倍，否则采集会以「画布像素不足」失败。未声明时按 1 倍。
 */
import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {useSceneContext} from '../context';
import {Painter, type Mark} from './frame';
import {compose} from './bloom';
import {MeasureProxy, reviewState} from './measure-proxy';

export type PainterFrame = {
  frameIndex: number;
  elapsedSeconds: number;
  width: number;
  height: number;
};

export type PainterCanvasProps = {
  width: number;
  height: number;
  /** 每帧的内容层绘制。必须只依赖 `state`，不读挂钟或随机源。 */
  paint: (frame: Painter, state: PainterFrame) => void;
  /** 画在辉光之后的锐利层：文字与细线放这里，避免被自己的光晕冲出重影。 */
  overlay?: (frame: Painter, state: PainterFrame) => void;
  /** 底；铺满整张画布。 */
  background?: (frame: Painter) => void;
  /** 底之上、内容之下；不参加辉光。 */
  under?: (frame: Painter) => void;
  /** 出帧后的全幅效果。 */
  post?: (frame: Painter) => void;
  /** 辉光强度；默认 1。实心物体多时调低。 */
  bloom?: number;
  /** 颗粒强度；默认 0.04。 */
  grain?: number;
  /** 颗粒种子；同一镜头内保持不变。 */
  seed?: number;
  /** 是否把绘制清单写成量测代理；默认开。关掉即回到「观测范围未验证」。 */
  measurable?: boolean;
  style?: React.CSSProperties;
};

function pixelScale(): number {
  const config = (window as unknown as {__M2V_CODE_CONFIG__?: {captureScale?: number; fps?: number}})
    .__M2V_CODE_CONFIG__;
  const value = config?.captureScale;
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 1;
}

function sceneFps(): number {
  const config = (window as unknown as {__M2V_CODE_CONFIG__?: {fps?: number}}).__M2V_CODE_CONFIG__;
  return typeof config?.fps === 'number' && config.fps > 0 ? config.fps : 30;
}

export function PainterCanvas({
  width, height, paint, overlay, background, under, post,
  bloom = 1, grain = .04, seed, measurable = true, style,
}: PainterCanvasProps): React.ReactElement {
  const {elapsedSeconds} = useSceneContext();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scale = pixelScale();
  const frameIndex = Math.round(elapsedSeconds * sceneFps());
  const [marks, setMarks] = useState<Mark[]>([]);

  // 绘制、合成与代理必须在同一个布局 effect 里完成：分两次提交会让截图窗口
  // 落在画面已更新、代理还没挂上的状态上，量测拿到的是上一帧的几何。
  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const bufferWidth = Math.max(1, Math.round(width * scale));
    const bufferHeight = Math.max(1, Math.round(height * scale));
    if (canvas.width !== bufferWidth || canvas.height !== bufferHeight) {
      canvas.width = bufferWidth;
      canvas.height = bufferHeight;
    }
    const state: PainterFrame = {frameIndex, elapsedSeconds, width, height};
    const drawn: Record<string, {canvas: HTMLCanvasElement; marks: Mark[]}> = {};
    for (const [name, draw] of Object.entries({
      background, under, content: paint, overlay, post,
    })) {
      if (!draw) continue;
      const layer = document.createElement('canvas');
      layer.width = bufferWidth;
      layer.height = bufferHeight;
      const painter = new Painter(layer.getContext('2d')!, width, height, scale);
      draw(painter, state);
      drawn[name] = {canvas: layer, marks: painter.marks};
    }
    compose(canvas, {
      width, height, scale, bloom, grain, seed, frame: frameIndex,
      background: drawn.background?.canvas ?? null,
      under: drawn.under?.canvas ?? null,
      content: drawn.content.canvas,
      overlay: drawn.overlay?.canvas ?? null,
      post: drawn.post?.canvas ?? null,
    });
    // 清单顺序 = 底、底层内容、内容层、锐利层；代理按同一顺序排列，便于逐项对照。
    const all = [...(drawn.background?.marks ?? []), ...(drawn.under?.marks ?? []),
                 ...drawn.content.marks, ...(drawn.overlay?.marks ?? [])];
    setMarks(all);
    const global = window as unknown as {__M2V_REVIEW_STATE__?: unknown};
    if (measurable) global.__M2V_REVIEW_STATE__ = reviewState(all);
    else delete global.__M2V_REVIEW_STATE__;
  }, [width, height, scale, frameIndex, measurable, bloom, grain, seed]);

  useEffect(() => () => {
    // 卸载时清掉探针，避免下一幕读到上一幕的状态。
    delete (window as unknown as {__M2V_REVIEW_STATE__?: unknown}).__M2V_REVIEW_STATE__;
  }, []);

  return (
    <>
      <canvas
        ref={canvasRef}
        style={{position: 'absolute', left: 0, top: 0, width, height, ...style}}
      />
      {measurable ? <MeasureProxy marks={marks}/> : null}
    </>
  );
}
