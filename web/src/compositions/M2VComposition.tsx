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

export type M2VProps = Storyboard;

/**
 * 共享 composition：唯一的时间轴定位者，把当前幕交给对应渲染器。
 *
 * 每幕按 `renderer` 选择画面路径：缺省与显式 `tree` 走场景树解释器，
 * `code` 走代码场景包装器（模块来自构建前生成的静态清单）。
 * 两条路径共用同一时间轴、同一安全区、同一主题令牌与**同一份节拍状态**——
 * 作品不注册自己的 Remotion 根或 composition，也不实现预览页，
 * 更不自己解析字幕或挂钟。
 */
export const M2VComposition: React.FC<M2VProps> = (storyboard) => {
  const frame = useCurrentFrame();
  const starts = useMemo(() => sceneStartFrames(storyboard), [storyboard]);
  const timelines = useMemo(() => storyboard.scenes.map((scene) => beatTimeline(scene)), [storyboard]);
  const activeIndex = sceneAt(storyboard, frame).index;
  const theme = storyboard.visual?.theme ?? 'dark';
  const preset = storyboard.visual?.preset;
  const presetEnabled = preset === 'keynote';
  const stylePack = storyboard.directingBrief.stylePack;
  const activeLocalFrame = Math.min(Math.max(frame - starts[activeIndex]!, 0), storyboard.scenes[activeIndex]!.durationInFrames - 1);
  const activeContinuity = continuityFor(storyboard, activeIndex);
  const showOutgoing = isContinuityActive(activeContinuity, activeLocalFrame);
  const subtitle = storyboard.subtitleCues?.find((cue) => cue.start <= frame / storyboard.fps && frame / storyboard.fps < cue.end);

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.m2vTheme = theme;
    if (preset) root.dataset.m2vPreset = preset; else delete root.dataset.m2vPreset;
    if (stylePack) root.dataset.m2vStylePack = stylePack; else delete root.dataset.m2vStylePack;
    root.style.setProperty('--m2v-width', `${storyboard.width}px`);
    root.style.setProperty('--m2v-height', `${storyboard.height}px`);
  }, [theme, preset, stylePack, storyboard.width, storyboard.height]);

  return <AbsoluteFill><div className={`m2v-stage${storyboard.subtitleCues ? ' m2v-with-subtitles' : ''}`} data-m2v-stage="">
    <div className="m2v-bg-glow stage-bg" aria-hidden="true" />
    <div className="m2v-bg-grid stage-bg" aria-hidden="true" />
    <div className="m2v-bg-grain stage-bg" aria-hidden="true" />
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
      return <section key={scene.id} data-m2v-scene="" data-scene-id={scene.id} data-layout={scene.visualIntent.composition}
        data-m2v-continuity-kind={(active ? continuity : activeContinuity)?.kind ?? ''}
        data-m2v-continuity-source={(active ? continuity : activeContinuity)?.sourceIds.join(',') ?? ''}
        data-m2v-continuity-target={(active ? continuity : activeContinuity)?.targetIds.join(',') ?? ''}
        data-m2v-continuity-phase={continuityState?.phase ?? ''}
        data-m2v-camera-focus={scene.camera?.focus ?? ''}
        data-m2v-camera-kind={currentCamera.kind}
        data-m2v-camera-progress={currentCamera.progress.toFixed(4)}
        data-m2v-camera-velocity={currentCamera.velocity.toFixed(6)}
        // 节拍状态同时写到 DOM：契约探针（A 系列闸门）量的是页面上的真实值，
        // 而不是再算一遍分镜——两处算法不同就会出现「报告说通过、画面不同步」。
        data-m2v-beat-current={beats.state.current ?? ''}
        data-m2v-beat-progress={beats.state.progress.toFixed(4)}
        data-m2v-beat-completed={beats.state.completed.join(',')}
        data-m2v-beat-estimated={beats.state.estimated ? '1' : '0'}
        style={active ? { ...transitionStyle(scene, localFrame, stylePack), zIndex: 1 } : outgoing ? { zIndex: 2 } : { display: 'none' }}>
        {/* code 场景同样置于安全区内；它不经过场景树排版与取档逻辑 */}
        <div className="m2v-safe" data-m2v-figure="" data-scene-tree-version={storyboard.schemaVersion}>
          <div className="m2v-camera" data-m2v-code-camera={isCode ? '' : undefined} style={cameraStyle(scene, localFrame)} data-m2v-camera={scene.camera.segments.map((segment) => segment.kind).join(',')}>
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
        {preset ? <div className="m2v-scene-index"><span>{scene.visual?.kicker ?? ''}</span></div> : null}
      </section>;
    })}
    {subtitle ? <div className="m2v-subtitle" data-m2v-subtitle="">{subtitle.text}</div> : null}
  </div></AbsoluteFill>;
};
