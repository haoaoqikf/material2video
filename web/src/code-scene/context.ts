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

export type CodeSceneProps = {
  props: Record<string, unknown>; fps: number; durationInFrames: number;
  /** 当前录制画幅。作品代码负责铺满整张画布并绘制不透明背景。 */
  width: number;
  height: number;
  /** 字幕安全区：重要文字与主体须避让该矩形，背景可以延伸到其中。 */
  subtitleSafeArea: SubtitleSafeArea;
  segmentWindows: Record<string, {startFrame: number; endFrame: number}>;
  /** 制作档位；standard 作品不声明时为 `standard`。 */
  profile?: string;
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
