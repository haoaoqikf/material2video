/** 可信作品代码场景 API；只在实时录制页使用，不进入 Remotion composition。 */
import {createContext, useContext, useEffect, useRef} from 'react';
import * as echarts from 'echarts';
import type {SubtitleSafeArea} from '../frames';
export {motion, AnimatePresence} from 'motion/react';
export {gsap} from 'gsap';
export * as THREE from 'three';
export {Canvas, useFrame, useThree} from '@react-three/fiber';
export {Float, Stars, PerspectiveCamera} from '@react-three/drei';
export {echarts};

/** 已导入素材的只读解析结果；视频带实测时长，图片为 `null`。 */
export type MediaAsset = {
  src: string;
  kind: 'image' | 'video';
  width: number;
  height: number;
  durationSeconds: number | null;
};

export type CodeSceneProps = {
  props: Record<string, unknown>; fps: number; durationInFrames: number;
  /** 当前录制画幅。作品代码负责铺满整张画布并绘制不透明背景。 */
  width: number;
  height: number;
  /** 字幕安全区：重要文字与主体须避让该矩形，背景可以延伸到其中。 */
  subtitleSafeArea: SubtitleSafeArea;
  segmentWindows: Record<string, {startFrame: number; endFrame: number}>;
};
export type SceneContext = {running: boolean; elapsedSeconds: number; progress: number; ready: () => void};
export const SceneContextProvider = createContext<SceneContext | null>(null);
export function useSceneContext(): SceneContext {
  const context = useContext(SceneContextProvider);
  if (!context) throw new Error('代码场景必须在录制上下文中运行');
  return context;
}

declare global {
  interface Window {
    __M2V_CODE_CONFIG__?: CodeSceneProps & {media?: Record<string, MediaAsset>};
  }
}

/**
 * 按素材 ID 取已导入素材的本地地址与实测信息。
 *
 * 映射由 prepare 复核 `assets/media-sources.json` 后注入，只包含登记过的素材；
 * 未知 ID 明确抛错，不静默回落到占位图或空地址。作品自己决定 fit、裁切与播放
 * 入点，也自己决定何时算「可播放」——视频未就绪就调用 `ready()` 会被录制超时拦下。
 */
export function useMediaAsset(id: string): MediaAsset {
  const media = window.__M2V_CODE_CONFIG__?.media;
  const asset = media?.[id];
  if (!asset) throw new Error(`未登记的素材 ID：${id}；请先用 m2v general assets import 导入并留证`);
  return asset;
}

/**
 * 固定画布、关闭交互并在卸载时释放图表；option 动画使用 ECharts 原生时钟。
 *
 * 宽高默认取**当前画幅**：作品铺满整张画布时不必重复写一遍尺寸，需要局部图表
 * 时再显式传入。
 */
export function Chart({option, width, height}: {option: echarts.EChartsOption; width?: number; height?: number}) {
  const canvas = window.__M2V_CODE_CONFIG__;
  if (!canvas) throw new Error('Chart 只能在代码场景录制页中使用');
  const host = useRef<HTMLDivElement>(null);
  const box = {width: width ?? canvas.width, height: height ?? canvas.height};
  useEffect(() => {
    const chart = echarts.init(host.current!, undefined, {...box, renderer: 'canvas'});
    chart.setOption({...option, tooltip: {show: false}, toolbox: {show: false}, dataZoom: []});
    return () => chart.dispose();
  }, [option, box.width, box.height]);
  return <div ref={host} style={{...box, pointerEvents: 'none'}}/>;
}
