/** 测试与参考场景的本地入口；不是作品运行时依赖，也不随模板生成。 */
import {useEffect, useRef} from 'react';
import {Canvas as FiberCanvas, type CanvasProps} from '@react-three/fiber';
import * as echarts from 'echarts';
import type {MediaAsset} from '../../web/src/code-scene/context';
export {motion, AnimatePresence} from 'motion/react';
export {gsap} from 'gsap';
export * as THREE from 'three';
export {useFrame, useThree} from '@react-three/fiber';
export {Float, Stars, PerspectiveCamera} from '@react-three/drei';
export {echarts};
export {SceneContextProvider, useSceneContext} from '../../web/src/code-scene/context';
export type {CodeSceneProps, MediaAsset, PreparedSceneSource, SceneContext, SubtitleSafeArea} from '../../web/src/code-scene/context';
export * from '../../web/src/code-scene/cinematic';
export * from '../../web/src/code-scene/motion';
export * from '../../web/src/code-scene/primitives';
export * from '../../web/src/code-scene/dynamics';
export * from '../../web/src/code-scene/rhythm';
export * from '../../web/src/code-scene/subtitles';
export * from '../../web/src/code-scene/effects/screen-burst';
export {svgPathProperties} from 'svg-path-properties';
export {getStroke} from 'perfect-freehand';
export * from '../../web/src/code-scene/motion-components';
export {createSceneEvents} from '../../web/src/code-scene/events';
// 二维绘制层用 `painter` 命名空间导出：`Canvas` 已经是 R3F 包装，直接铺开
// 会让两个同名符号撞在一起。
export * as painter from '../../web/src/code-scene/painter';

/** lookdev 保留逻辑构图，但强制画布原生绘制足够的像素；普通录制仍使用作品 DPR。 */
export function Canvas(props: CanvasProps) {
  const scale = window.__M2V_CODE_CONFIG__?.captureScale;
  return <FiberCanvas {...props} dpr={scale ?? props.dpr}/>;
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
  if (!asset) throw new Error(`未登记的素材 ID：${id}；请先用 m2v author assets import 导入并留证`);
  return asset;
}

/** 按 ID 获取当前幕显式声明的结构化来源；准备记录负责校验和绑定文件。 */
export function useSceneSource(id: string) {
  const source = window.__M2V_CODE_CONFIG__?.sources?.[id];
  if (!source) throw new Error(`未声明或尚未准备的结构化来源：${id}`);
  return source;
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
    const chart = echarts.init(host.current!, undefined, {...box, renderer: 'canvas',
      ...(canvas.captureScale ? {devicePixelRatio: canvas.captureScale} : {})});
    chart.setOption({...option, tooltip: {show: false}, toolbox: {show: false}, dataZoom: []});
    return () => chart.dispose();
  }, [option, box.width, box.height]);
  return <div ref={host} style={{...box, pointerEvents: 'none'}}/>;
}
