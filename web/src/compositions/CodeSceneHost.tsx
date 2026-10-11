import { useEffect, useRef, useState } from 'react';
import type { Scene } from '@/schema/storyboard';
import type { M2VBeatState, M2VCodeSceneProps, M2VThemeInfo, M2VWorldInfo, M2VStageInfo, M2VObjectStates } from '@/code-scene';
import { createSceneRandom } from '@/code-scene';
import type { BeatContext } from '@/runtime/beats';
import { codeSceneBeatState } from '@/runtime/beats';
import { cameraState } from '@/runtime/camera';
import type { CameraState } from '@/runtime/motionPlan';
import { sceneMotionPlan } from '@/runtime/motionPlan';
import type { ContinuityRenderState } from '@/runtime/continuity';
import { ACTIVE_CODE_SCENES } from '../../.gen/active-scenes';

/**
 * 代码场景包装器：共享 composition 与作品模块之间唯一的接缝。
 *
 * 职责：
 * - **模块查找**：从静态清单按模块标识取组件；查不到直接报错，
 *   绝不静默渲染空场景（校验理应拦截，这里是最后的防线）；
 * - **注入运行时**：幕数据、全局帧、幕内帧、进度、fps、画布、主题、
 *   稳定种子随机。作品拿不到时长与相邻幕，不可能形成第二套时间轴；
 * - **探针与主题**：根节点带 `data-m2v-code-scene` 与主题标记，
 *   外层 `m2v-safe` 提供与场景树一致的安全区；共享设计令牌来自
 *   `<html>` 上的 CSS 变量（composition 统一写入），字体颜色基础一致；
 * - **就绪协议**：`data-m2v-code-ready` 在场景完成首次提交且首批
 *   本地资源（图片）就绪后翻为 `"1"`；资源失败写入
 *   `data-m2v-code-error`，由契约页 ready/seek 显式报错，
 *   不会把未完成画面截成空白帧。
 *
 * 布局说明：包装器不套用场景树排版引擎，也不做取档——代码场景的
 * 自由布局只受安全区与共享令牌约束。
 */
export function CodeSceneHost({
  scene,
  frame,
  localFrame,
  fps,
  theme,
  preset,
  width,
  height,
  beats,
  continuity,
  cameraOverride,
  v4Context,
}: {
  scene: Scene;
  frame: number;
  localFrame: number;
  fps: number;
  theme: 'dark' | 'light';
  preset?: 'keynote';
  width: number;
  height: number;
  beats: BeatContext;
  continuity?: ContinuityRenderState;
  cameraOverride?: CameraState;
  v4Context?: { world: M2VWorldInfo; stage: M2VStageInfo; objectStates: M2VObjectStates; phase: M2VCodeSceneProps['motion']['phase'] };
}): React.ReactElement {
  const renderer = scene.renderer;
  const module_ = renderer?.kind === 'code' ? renderer.module : '';
  const Component = ACTIVE_CODE_SCENES[module_];
  if (!Component) {
    throw new Error(
      `场景 ${scene.id} 引用的代码场景模块未注册：${module_ || '（缺少 renderer.module）'}。` +
        '请检查分镜与 web/.gen/active-scenes.ts 是否为同一作品生成。',
    );
  }

  const ref = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // 首批本地资源就绪检查：图片是代码场景最常用的异步资源。
    // 只在挂载后执行一次；加载失败是硬失败，不是空白帧。
    const host = ref.current;
    if (!host) return;
    let cancelled = false;
    const images = Array.from(host.querySelectorAll('img'));
    const pending = images.filter((img) => !img.complete);
    if (pending.length === 0) {
      const failed = images.find((img) => img instanceof HTMLImageElement && !img.naturalWidth && img.complete);
      if (failed) {
        setError(`本地资源加载失败: ${failed.getAttribute('src') ?? '(无 src)'}`);
        return;
      }
      setReady(true);
      return;
    }
    const onDone = (): void => {
      if (!cancelled) setReady(true);
    };
    const onFail = (event: Event): void => {
      if (!cancelled) {
        const target = event.target as HTMLImageElement;
        setError(`本地资源加载失败: ${target.getAttribute('src') ?? '(无 src)'}`);
      }
    };
    pending.forEach((img) => {
      img.addEventListener('load', onDone, { once: true });
      img.addEventListener('error', onFail, { once: true });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const themeInfo: M2VThemeInfo = { theme, ...(preset ? { preset } : {}) };
  const random = createSceneRandom(v4Context?.world.id ?? scene.id);
  const beatState: M2VBeatState = codeSceneBeatState(beats);
  const plan = sceneMotionPlan(scene, beats.timeline); const phase = (Object.entries(plan.phases).find(([, span]) => span.startFrame <= localFrame && localFrame < span.endFrame)?.[0] ?? 'settle') as 'establish'|'change'|'result'|'settle';
  const relation = continuity?.relation; const continuityProgress = relation ? Math.min(1, Math.max(0, continuity.frame / relation.span)) : 0;
  const props: M2VCodeSceneProps = {
    world: v4Context?.world ?? { id: scene.id, claim: '', metaphor: '', objects: [] },
    stage: v4Context?.stage ?? { id: scene.id, data: scene.data, startFrame: 0, endFrame: scene.durationInFrames,
      progress: scene.durationInFrames <= 1 ? 1 : Math.min(1, Math.max(0, localFrame / (scene.durationInFrames - 1))) },
    objectStates: v4Context?.objectStates ?? {},
    scene: {
      id: scene.id,
      type: scene.type,
      data: scene.data,
      durationInFrames: scene.durationInFrames,
      ...(scene.visual?.kicker ? { kicker: scene.visual.kicker } : {}),
    },
    frame,
    localFrame,
    progress: scene.durationInFrames <= 1 ? 1 : Math.min(1, Math.max(0, localFrame / (scene.durationInFrames - 1))),
    fps,
    canvas: { width, height },
    theme: themeInfo,
    beats: beatState,
    motion: { phase: v4Context?.phase ?? phase, camera: cameraOverride ?? cameraState(scene, localFrame), continuity: continuity && relation ? { kind: relation.kind, phase: continuity.phase, progress: continuityProgress, sources: relation.sourceIds, targets: relation.targetIds } : null },
    random,
  };

  return (
    <div
      ref={ref}
      className="m2v-code-scene"
      data-m2v-code-scene={module_}
      data-m2v-code-ready={error ? 'error' : ready ? '1' : '0'}
      {...(error ? { 'data-m2v-code-error': error } : {})}
      data-m2v-theme={theme}
      data-m2v-continuity-mode={continuity ? 'probe-required' : 'none'}
      {...(preset ? { 'data-m2v-preset': preset } : {})}
    >
      <Component {...props} />
    </div>
  );
}
