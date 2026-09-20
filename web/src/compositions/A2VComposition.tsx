import { useLayoutEffect, useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import type { Storyboard } from '@/schema/storyboard';
import { SceneTree } from '@/primitives/SceneTree';
import { sceneAt, sceneStartFrames } from '@/runtime/timeline';

export type A2VProps = Storyboard;

export const A2VComposition: React.FC<A2VProps> = (storyboard) => {
  const frame = useCurrentFrame();
  const starts = useMemo(() => sceneStartFrames(storyboard), [storyboard]);
  const activeIndex = sceneAt(storyboard, frame).index;
  const theme = storyboard.visual?.theme ?? 'dark';
  const preset = storyboard.visual?.preset;
  const presetEnabled = preset === 'keynote';

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.a2vTheme = theme;
    if (preset) root.dataset.a2vPreset = preset; else delete root.dataset.a2vPreset;
    root.style.setProperty('--a2v-width', `${storyboard.width}px`);
    root.style.setProperty('--a2v-height', `${storyboard.height}px`);
  }, [theme, preset, storyboard.width, storyboard.height]);

  return <AbsoluteFill><div className="a2v-stage" data-a2v-stage="">
    <div className="a2v-bg-glow stage-bg" aria-hidden="true" />
    <div className="a2v-bg-grid stage-bg" aria-hidden="true" />
    <div className="a2v-bg-grain stage-bg" aria-hidden="true" />
    {storyboard.scenes.map((scene, index) => {
      const active = index === activeIndex;
      const localFrame = active ? Math.min(Math.max(frame - starts[index]!, 0), scene.durationInFrames - 1) : 0;
      return <section key={scene.id} data-a2v-scene="" data-scene-id={scene.id} data-layout={scene.visualIntent.composition} style={active ? undefined : { display: 'none' }}>
        <div className="a2v-safe" data-a2v-figure="" data-scene-tree-version={storyboard.schemaVersion}>
          <SceneTree scene={scene} frame={localFrame} preset={presetEnabled} />
        </div>
        {preset ? <div className="a2v-scene-index"><span>{scene.visual?.kicker ?? ''}</span><span className="a2v-scene-number">{String(index + 1).padStart(2, '0')} / {String(storyboard.scenes.length).padStart(2, '0')}</span></div> : null}
      </section>;
    })}
  </div></AbsoluteFill>;
};
