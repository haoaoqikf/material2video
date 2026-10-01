import { useLayoutEffect, useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import type { Scene, SceneNode } from '@/schema/storyboard';
import type { StoryboardV4 } from '@/schema/storyboardV4';
import { SceneTree } from '@/primitives/SceneTree';
import { CodeSceneHost } from './CodeSceneHost';
import { beatStateAt, type BeatContext, type BeatTimeline } from '@/runtime/beats';
import { compileStateTracks } from '@/runtime/stateTracksV4';
import { worldTreeAtFrame } from '@/runtime/worldTreeV4';
import { resolveStoryboardV4, stageAt, type V4MediaTimeline } from '@/runtime/timelineV4';
import { cameraStateV4, compileCameraV4 } from '@/runtime/cameraV4';
import { stateAt } from '@/runtime/stateTracksV4';

export type V4SubtitleCue = { start: number; end: number; text: string };
export type A2VCompositionV4Props = StoryboardV4 & { subtitleCues?: V4SubtitleCue[]; mediaTimeline?: V4MediaTimeline };

function legacyTreeRefs(node: SceneNode): SceneNode {
  const copy = { ...node, ...(node.children ? { children: node.children.map(legacyTreeRefs) } : {}) };
  if (copy.contentRef && !copy.contentRef.startsWith('data.')) copy.contentRef = `data.${copy.contentRef}`;
  if (copy.sourceRef && !copy.sourceRef.startsWith('data.')) copy.sourceRef = `data.${copy.sourceRef}`;
  return copy;
}

/** One persistent world root. Stages only change data and the frame context. */
export const A2VCompositionV4: React.FC<A2VCompositionV4Props> = (props) => {
  const storyboard = props as StoryboardV4;
  const frame = useCurrentFrame();
  const timeline = useMemo(() => resolveStoryboardV4(storyboard, props.mediaTimeline), [storyboard, props.mediaTimeline]);
  const stateTracks = useMemo(() => compileStateTracks(storyboard, timeline), [storyboard, timeline]);
  const camera = useMemo(() => compileCameraV4(storyboard, timeline, stateTracks), [storyboard, timeline, stateTracks]);
  const activeStageId = stageAt(timeline, frame) ?? timeline.stages.at(-1)!.id;
  const stage = storyboard.stages.find(({ id }) => id === activeStageId)!;
  const worldFrame = storyboard.world.renderer.kind === 'tree'
    ? worldTreeAtFrame(storyboard.world, stateTracks, frame) : undefined;
  const cameraFrame = cameraStateV4(camera, frame);
  const stageStart = timeline.stages.find(({ id }) => id === stage.id)!.startFrame;
  const stageEnd = timeline.stages.find(({ id }) => id === stage.id)!.endFrame;
  const stageDuration = stageEnd - stageStart;
  const stageProgress = stageDuration <= 1 ? 1 : Math.min(1, Math.max(0, (frame - stageStart) / (stageDuration - 1)));
  const stagePhase = timeline.phases.find((phase) => phase.stageId === stage.id && phase.startFrame <= frame && frame < phase.endFrame)?.phase ?? 'settle';
  const beats: BeatTimeline = useMemo(() => ({
    beats: timeline.beats as unknown as BeatTimeline['beats'], estimated: timeline.estimated,
  }), [timeline]);
  const beatContext: BeatContext = { timeline: beats, state: beatStateAt(beats, frame) };
  // The v4 code renderer owns one persistent world; its beat API must therefore
  // observe the same global plan regardless of which narration stage is active.
  const worldBeats = storyboard.world.renderer.kind === 'code' ? beatContext : {
    timeline: { beats: [], estimated: beatContext.timeline.estimated },
    state: { current: null, progress: 0, completed: [], estimated: beatContext.timeline.estimated },
  } as BeatContext;
  const scene = {
    id: storyboard.world.id, type: 'world', durationInFrames: timeline.totalFrames,
    data: { ...storyboard.world.data, ...stage.data, world: storyboard.world.data, stage: stage.data },
    narrationSegments: stage.narrationSegments, beats: stage.beats ?? [],
    visualIntent: stage.visualIntent, camera: { ...storyboard.world.camera, segments: [] },
    renderer: storyboard.world.renderer, sceneTree: worldFrame ? legacyTreeRefs(worldFrame.sceneTree) : undefined,
    motions: [],
  } as unknown as Scene;
  const theme = storyboard.visual.theme;
  const stylePack = storyboard.directingBrief.stylePack;
  const preset = storyboard.visual.preset === 'keynote';
  const subtitle = props.subtitleCues?.find((cue) => cue.start <= frame / storyboard.fps && frame / storyboard.fps < cue.end);

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.a2vTheme = theme;
    root.dataset.a2vPreset = 'keynote';
    root.dataset.a2vStylePack = stylePack;
    root.style.setProperty('--a2v-width', `${storyboard.width}px`);
    root.style.setProperty('--a2v-height', `${storyboard.height}px`);
  }, [theme, stylePack, storyboard.width, storyboard.height]);

  return <AbsoluteFill><div className={`a2v-stage${props.subtitleCues ? ' a2v-with-subtitles' : ''}`} data-a2v-stage="">
    <div className="a2v-bg-glow stage-bg" aria-hidden="true" />
    <div className="a2v-bg-grid stage-bg" aria-hidden="true" />
    <div className="a2v-bg-grain stage-bg" aria-hidden="true" />
    <section key={storyboard.world.id} data-a2v-world="" data-a2v-world-id={storyboard.world.id} data-a2v-stage-id={stage.id}
      data-a2v-world-renderer={storyboard.world.renderer.kind}
      data-a2v-world-objects={JSON.stringify(storyboard.world.objects.map(({ id, role }) => ({ id, role })))}
      data-a2v-world-object-states={JSON.stringify(stateAt(stateTracks, frame))}
      data-a2v-stage-index={timeline.stages.findIndex(({ id }) => id === stage.id)}
      data-a2v-stage-start={stageStart} data-a2v-stage-end={stageEnd}
      data-a2v-beat-current={beatContext.state.current ?? ''}
      data-a2v-beat-progress={beatContext.state.progress.toFixed(4)}
      data-a2v-beat-completed={beatContext.state.completed.join(',')}
      data-a2v-beat-plan={timeline.beats.map(({ id }) => id).join(',')}
      data-a2v-beat-estimated={timeline.estimated ? '1' : '0'}>
      <div className="a2v-safe" data-a2v-figure="" data-scene-tree-version="4">
        <div className="a2v-camera" data-a2v-camera="global" data-a2v-camera-kind={cameraFrame.kind}
          data-a2v-camera-focus={cameraFrame.focus} data-a2v-camera-x={cameraFrame.x}
          data-a2v-camera-y={cameraFrame.y} data-a2v-camera-scale={cameraFrame.scale}
          data-a2v-camera-velocity={cameraFrame.velocity} style={{
          transform: `translate(${cameraFrame.x}px, ${cameraFrame.y}px) scale(${cameraFrame.scale})`,
          perspective: storyboard.world.camera.depth === 'layered' ? '1200px' : undefined,
          transformOrigin: storyboard.world.camera.composition === 'left' ? '30% 50%' : storyboard.world.camera.composition === 'right' ? '70% 50%' : '50% 50%',
        }}>
          {storyboard.world.renderer.kind === 'tree' && worldFrame ? (
            <SceneTree scene={scene} frame={frame} preset={preset} beats={beatContext} stylePack={stylePack}
              hiddenNodeIds={worldFrame.hiddenNodeIds} />
          ) : (
            <CodeSceneHost scene={scene} frame={frame} localFrame={frame} fps={storyboard.fps} theme={theme}
              preset="keynote" width={storyboard.width} height={storyboard.height} beats={worldBeats}
              cameraOverride={cameraFrame} v4Context={{
                world: storyboard.world, stage: { id: stage.id, data: stage.data,
                  startFrame: stageStart, endFrame: stageEnd, progress: stageProgress },
                objectStates: stateAt(stateTracks, frame), phase: stagePhase,
              }} />
          )}
        </div>
      </div>
    </section>
    {subtitle ? <div className="a2v-subtitle" data-a2v-subtitle="">{subtitle.text}</div> : null}
  </div></AbsoluteFill>;
};
