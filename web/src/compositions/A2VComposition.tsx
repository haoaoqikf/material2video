import { useLayoutEffect, useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import type { Storyboard } from '@/schema/storyboard';
import { SceneTree } from '@/primitives/SceneTree';
import { CodeSceneHost } from './CodeSceneHost';
import { sceneAt, sceneStartFrames } from '@/runtime/timeline';
import { beatStateAt, beatTimeline } from '@/runtime/beats';
import { cameraState, cameraStyle } from '@/runtime/camera';
import { transitionStyle } from '@/runtime/transition';
import { continuityFor, isContinuityActive, type ContinuityRenderState } from '@/runtime/continuity';

export type A2VProps = Storyboard;

/**
 * 共享 composition：唯一的时间轴定位者，把当前幕交给对应渲染器。
 *
 * 每幕按 `renderer` 选择画面路径：缺省与显式 `tree` 走场景树解释器，
 * `code` 走代码场景包装器（模块来自构建前生成的静态清单）。
 * 两条路径共用同一时间轴、同一安全区、同一主题令牌与**同一份节拍状态**——
 * 作品不注册自己的 Remotion 根或 composition，也不实现预览页，
 * 更不自己解析字幕或挂钟。
 */
export const A2VComposition: React.FC<A2VProps> = (storyboard) => {
  const frame = useCurrentFrame();
  const starts = useMemo(() => sceneStartFrames(storyboard), [storyboard]);
  const timelines = useMemo(() => storyboard.scenes.map((scene) => beatTimeline(scene)), [storyboard]);
  const activeIndex = sceneAt(storyboard, frame).index;
  const theme = storyboard.visual?.theme ?? 'dark';
  const preset = storyboard.visual?.preset;
  const presetEnabled = preset === 'keynote';
  const stylePack = storyboard.directingBrief?.stylePack;
  const activeLocalFrame = Math.min(Math.max(frame - starts[activeIndex]!, 0), storyboard.scenes[activeIndex]!.durationInFrames - 1);
  const activeContinuity = continuityFor(storyboard, activeIndex);
  const showOutgoing = isContinuityActive(activeContinuity, activeLocalFrame);

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.a2vTheme = theme;
    if (preset) root.dataset.a2vPreset = preset; else delete root.dataset.a2vPreset;
    if (stylePack) root.dataset.a2vStylePack = stylePack; else delete root.dataset.a2vStylePack;
    root.style.setProperty('--a2v-width', `${storyboard.width}px`);
    root.style.setProperty('--a2v-height', `${storyboard.height}px`);
  }, [theme, preset, stylePack, storyboard.width, storyboard.height]);

  return <AbsoluteFill><div className="a2v-stage" data-a2v-stage="">
    <div className="a2v-bg-glow stage-bg" aria-hidden="true" />
    <div className="a2v-bg-grid stage-bg" aria-hidden="true" />
    <div className="a2v-bg-grain stage-bg" aria-hidden="true" />
    {storyboard.scenes.map((scene, index) => {
      const active = index === activeIndex;
      const outgoing = showOutgoing && index === activeIndex - 1;
      const localFrame = active ? activeLocalFrame : outgoing ? scene.durationInFrames - 1 : 0;
      const isCode = scene.renderer?.kind === 'code';
      const timeline = timelines[index]!;
      const beats = { timeline, state: beatStateAt(timeline, localFrame) };
      const continuity = continuityFor(storyboard, index);
      const currentCamera = cameraState(scene, localFrame);
      const continuityState: ContinuityRenderState | undefined = active && activeContinuity
        ? { relation: activeContinuity, phase: 'target', frame: activeLocalFrame }
        : outgoing && activeContinuity
          ? { relation: activeContinuity, phase: 'source', frame: activeLocalFrame }
          : undefined;
      return <section key={scene.id} data-a2v-scene="" data-scene-id={scene.id} data-layout={scene.visualIntent.composition}
        data-a2v-continuity-kind={(active ? continuity : activeContinuity)?.kind ?? ''}
        data-a2v-continuity-source={(active ? continuity : activeContinuity)?.sourceIds.join(',') ?? ''}
        data-a2v-continuity-target={(active ? continuity : activeContinuity)?.targetIds.join(',') ?? ''}
        data-a2v-continuity-phase={continuityState?.phase ?? ''}
        data-a2v-camera-focus={scene.camera?.focus ?? ''}
        data-a2v-camera-kind={currentCamera.kind}
        data-a2v-camera-progress={currentCamera.progress.toFixed(4)}
        data-a2v-camera-velocity={currentCamera.velocity.toFixed(6)}
        // 节拍状态同时写到 DOM：契约探针（A 系列闸门）量的是页面上的真实值，
        // 而不是再算一遍分镜——两处算法不同就会出现「报告说通过、画面不同步」。
        data-a2v-beat-current={beats.state.current ?? ''}
        data-a2v-beat-progress={beats.state.progress.toFixed(4)}
        data-a2v-beat-completed={beats.state.completed.join(',')}
        data-a2v-beat-estimated={beats.state.estimated ? '1' : '0'}
        style={active ? { ...transitionStyle(scene, localFrame, stylePack), zIndex: 1 } : outgoing ? { zIndex: 2 } : { display: 'none' }}>
        {/* code 场景同样置于安全区内；它不经过场景树排版与取档逻辑 */}
        <div className="a2v-safe" data-a2v-figure="" data-scene-tree-version={storyboard.schemaVersion}>
          <div className="a2v-camera" style={cameraStyle(scene, localFrame)} data-a2v-camera={scene.camera?.movement ?? 'none'}>
          {isCode ? (
            <CodeSceneHost
              scene={scene}
              frame={frame}
              localFrame={localFrame}
              fps={storyboard.fps}
              theme={theme}
              preset={preset}
              width={storyboard.width}
              height={storyboard.height}
              beats={beats}
              continuity={continuityState}
            />
          ) : (
            <SceneTree scene={scene} frame={localFrame} preset={presetEnabled} beats={beats} stylePack={stylePack} continuity={continuityState} />
          )}
          </div>
        </div>
        {preset ? <div className="a2v-scene-index"><span>{scene.visual?.kicker ?? ''}</span></div> : null}
      </section>;
    })}
  </div></AbsoluteFill>;
};
