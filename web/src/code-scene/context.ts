/** 录制场景的共享上下文与类型；单独成文件，供 SDK 与电影套件同时引用而不成环。 */
import {createContext, useContext} from 'react';

/** 已导入素材的只读解析结果；视频带实测时长，图片为 `null`。 */
export type MediaAsset = {
  src: string;
  kind: 'image' | 'video';
  width: number;
  height: number;
  durationSeconds: number | null;
  /** 实测色彩空间；无法判定时为 `unknown`。 */
  colorSpace: 'srgb' | 'unknown';
  /** 实测是否带 alpha 通道；决定材质是否按透明处理。 */
  alpha: boolean;
  /** 来源记录里的许可原文；未登记时为 `未知`，不能据此推断可用范围。 */
  license: string;
};

export type SubtitleSafeArea = {x: number; y: number; width: number; height: number};
export type PreparedSceneSource = {kind: 'financial-series' | 'construction' | 'vehicle-model'; data: unknown};

/** 作品声明 `capture.timebase: "global"` 时注入的全片时间轴。 */
export type SceneTimeline = {
  sceneStartFrame: number;
  sceneEndFrame: number;
  durationInFrames: number;
};

export type CodeSceneProps = {
  /** 仅包含当前幕声明并通过准备校验的结构化来源。 */
  sources?: Readonly<Record<string, PreparedSceneSource>>;
  /** 当前幕的事件 ID → 幕内整数帧；未声明事件时省略。 */
  eventFrames?: Readonly<Record<string, number>>;
  props: Record<string, unknown>; fps: number; durationInFrames: number;
  /** 当前录制画幅。作品代码负责铺满整张画布并绘制不透明背景。 */
  width: number;
  height: number;
  /** 字幕安全区：重要文字与主体须避让该矩形，背景可以延伸到其中。 */
  subtitleSafeArea: SubtitleSafeArea;
  segmentWindows: Record<string, {startFrame: number; endFrame: number}>;
  /** lookdev 的原生像素密度；缺省不改变作品画布设置。 */
  captureScale?: number;
  /** 纯时间采集模式；缺省为顺序录制。 */
  captureMode?: 'sequential' | 'pure-time';
  /** 纯模式块首帧；由采集器注入录制页，不进入片段缓存键。 */
  captureStartFrame?: number;
  /** 仅在 `content.props.capture.timebase: "global"` 时注入。 */
  timeline?: SceneTimeline;
};

export type SceneContext = {
  running: boolean;
  elapsedSeconds: number;
  progress: number;
  /** 全片帧号；未 opt-in 全局时间时等于幕内帧号。子帧保留小数。 */
  globalFrame: number;
  /** 全片秒数；未 opt-in 全局时间时等于 elapsedSeconds。 */
  globalSeconds: number;
  /** 本幕在全片时间轴上的起点；未 opt-in 时为 0。 */
  sceneStartFrame: number;
  ready: () => void;
  /** 登记本次受控状态更新的异步绘制；宿主在截图前等待其完成，拒绝会使采集失败。 */
  waitForFrame: (task: PromiseLike<unknown>) => void;
};
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
