import type { ReactNode } from 'react';
import type { StoryboardV4 } from '@/schema/storyboardV4';
import type { Scene, SceneNode } from '@/schema/storyboard';
import type { CompiledStateTrack } from '@/runtime/stateTracksV4';
import { worldTreeAtFrame } from '@/runtime/worldTreeV4';
import { SceneTree } from '@/primitives/SceneTree';
import type { GeometryBox } from '@/runtime/motionPlan';
import { stageAt, type V4Timeline } from '@/runtime/timelineV4';

export function layoutSampleFrames(totalFrames: number, tracks: readonly CompiledStateTrack[], stages: readonly { startFrame: number; endFrame: number }[] = []): number[] {
  const frames = new Set([0, Math.max(0, totalFrames - 1)]);
  for (const stage of stages) {
    frames.add(Math.min(totalFrames - 1, stage.startFrame));
    frames.add(Math.min(totalFrames - 1, Math.max(0, stage.endFrame - 1)));
  }
  for (const track of tracks) {
    frames.add(Math.min(totalFrames - 1, track.startFrame));
    frames.add(Math.min(totalFrames - 1, Math.max(0, track.endFrame - 1)));
  }
  return [...frames].filter((frame) => frame >= 0 && frame < totalFrames).sort((a, b) => a - b);
}

export function unionGeometryBoxes(...samples: readonly ReadonlyMap<string, GeometryBox>[]): ReadonlyMap<string, GeometryBox> {
  const boxes = new Map<string, GeometryBox>();
  for (const sample of samples) for (const [id, box] of sample) {
    const current = boxes.get(id);
    const left = Math.min(current?.x ?? box.x, box.x), top = Math.min(current?.y ?? box.y, box.y);
    const right = Math.max((current?.x ?? box.x) + (current?.width ?? box.width), box.x + box.width);
    const bottom = Math.max((current?.y ?? box.y) + (current?.height ?? box.height), box.y + box.height);
    boxes.set(id, { x: left, y: top, width: right - left, height: bottom - top, radius: Math.max(current?.radius ?? 0, box.radius) });
  }
  return boxes;
}

export function mergeMeasuredGeometry(samples: readonly HTMLElement[], width: number, height: number): ReadonlyMap<string, GeometryBox> {
  const bounds = new Map<string, { left: number; top: number; right: number; bottom: number }>();
  for (const sample of samples) {
    const origin = sample.getBoundingClientRect();
    for (const node of sample.querySelectorAll<HTMLElement>('[data-a2v-node-id]')) {
      if (getComputedStyle(node).visibility === 'hidden') continue;
      const rect = node.getBoundingClientRect();
      if (!rect.width || !rect.height) continue;
      const current = bounds.get(node.dataset.a2vNodeId!);
      const left = rect.left - origin.left, top = rect.top - origin.top;
      const next = { left: Math.min(current?.left ?? left, left), top: Math.min(current?.top ?? top, top),
        right: Math.max(current?.right ?? left + rect.width, left + rect.width),
        bottom: Math.max(current?.bottom ?? top + rect.height, top + rect.height) };
      bounds.set(node.dataset.a2vNodeId!, next);
    }
  }
  return new Map([...bounds].map(([id, box]) => [id, {
    x: box.left / width, y: box.top / height, width: (box.right - box.left) / width,
    height: (box.bottom - box.top) / height,
    radius: Math.max(box.right - box.left, box.bottom - box.top) / (2 * Math.max(width, height)),
  }]));
}

export function findLayoutFailures(samples: readonly HTMLElement[]): ReadonlySet<string> {
  const failures = new Set<string>();
  for (const sample of samples) {
    const safe = sample.querySelector<HTMLElement>('.a2v-safe')?.getBoundingClientRect();
    if (!safe) continue;
    for (const node of sample.querySelectorAll<HTMLElement>('[data-a2v-primitive="text"][data-a2v-fit-measured="true"]')) {
      const rect = node.getBoundingClientRect();
      const surface = node.parentElement?.closest<HTMLElement>('[data-a2v-primitive="surface"]');
      const container = surface?.getBoundingClientRect() ?? safe;
      const style = surface ? getComputedStyle(surface) : undefined;
      const left = container.left + Number.parseFloat(style?.paddingLeft ?? '0');
      const right = container.right - Number.parseFloat(style?.paddingRight ?? '0');
      const top = container.top + Number.parseFloat(style?.paddingTop ?? '0');
      const bottom = container.bottom - Number.parseFloat(style?.paddingBottom ?? '0');
      if (rect.left < left - 1 || rect.right > right + 1 || rect.top < top - 1 || rect.bottom > bottom + 1) {
        failures.add(node.dataset.a2vNodeId!);
      }
    }
  }
  return failures;
}

function legacyTreeRefs(node: SceneNode): SceneNode {
  const copy = { ...node, ...(node.children ? { children: node.children.map(legacyTreeRefs) } : {}) };
  if (copy.contentRef && !copy.contentRef.startsWith('data.')) copy.contentRef = `data.${copy.contentRef}`;
  if (copy.sourceRef && !copy.sourceRef.startsWith('data.')) copy.sourceRef = `data.${copy.sourceRef}`;
  return copy;
}

export function LayoutGeometryPreflight({ storyboard, timeline, tracks, frames }: {
  storyboard: StoryboardV4; timeline: V4Timeline; tracks: readonly CompiledStateTrack[]; frames: readonly number[];
}): ReactNode {
  if (typeof window === 'undefined' || storyboard.world.renderer.kind !== 'tree') return null;
  const world = storyboard.world;
  const samples = frames.map((frame) => {
    const state = worldTreeAtFrame(world, tracks, frame);
    const stageId = stageAt(timeline, frame) ?? timeline.stages.at(-1)!.id;
    const stage = storyboard.stages.find(({ id }) => id === stageId)!;
    const scene = { id: world.id, type: 'world', durationInFrames: frames.at(-1)! + 1,
      data: { ...state.data, ...stage.data, world: state.data, stage: stage.data },
      renderer: world.renderer, sceneTree: legacyTreeRefs(state.sceneTree), motions: [] } as unknown as Scene;
    return <div key={frame} data-a2v-layout-sample={frame} style={{ position: 'relative', width: storyboard.width,
      height: storyboard.height, overflow: 'hidden' }}>
      <div className="a2v-safe">
        <div className="a2v-camera"><SceneTree scene={scene} frame={frame} preset={storyboard.visual.preset === 'keynote'} /></div>
      </div>
    </div>;
  });
  return <div data-a2v-layout-preflight="" aria-hidden="true" style={{ position: 'fixed', left: -20000, top: 0,
    width: storyboard.width, height: storyboard.height, opacity: 0, pointerEvents: 'none', zIndex: -1 }}>
    {samples}
  </div>;
}
