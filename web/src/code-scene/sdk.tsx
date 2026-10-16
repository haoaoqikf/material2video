/** 可信作品代码场景 API；只在实时录制页使用，不进入 Remotion composition。 */
import {createContext, useContext, useEffect, useRef} from 'react';
import * as echarts from 'echarts';
import type {Theme} from '../palette';
export {motion, AnimatePresence} from 'motion/react';
export {gsap} from 'gsap';
export * as THREE from 'three';
export {Canvas, useFrame, useThree} from '@react-three/fiber';
export {Float, Stars, PerspectiveCamera} from '@react-three/drei';
export {echarts};

export type CodeSceneProps = {
  props: Record<string, unknown>; fps: number; durationInFrames: number;
  segmentWindows: Record<string, {startFrame: number; endFrame: number}>;
  /** 录制页按该主题设置背景与前景色，作品代码可据此配色。 */
  theme: Theme;
};
export type SceneContext = {running: boolean; elapsedSeconds: number; progress: number; ready: () => void};
export const SceneContextProvider = createContext<SceneContext | null>(null);
export function useSceneContext(): SceneContext {
  const context = useContext(SceneContextProvider);
  if (!context) throw new Error('代码场景必须在录制上下文中运行');
  return context;
}

/** 固定画布、关闭交互并在卸载时释放图表；option 动画使用 ECharts 原生时钟。 */
export function Chart({option, width = 864, height = 920}: {option: echarts.EChartsOption; width?: number; height?: number}) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const chart = echarts.init(host.current!, undefined, {width, height, renderer: 'canvas'});
    chart.setOption({...option, tooltip: {show: false}, toolbox: {show: false}, dataZoom: []});
    return () => chart.dispose();
  }, [option, width, height]);
  return <div ref={host} style={{width, height, pointerEvents: 'none'}}/>;
}
