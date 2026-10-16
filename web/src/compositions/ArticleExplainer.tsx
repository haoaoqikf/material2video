import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, useCurrentFrame} from 'remotion';
import {palettes, type Palette} from '../palette';
import {FONT_STACK} from '../fonts';

export type DisplayItem = {text: string; segmentId?: string; keywords?: string[]};
type Node = DisplayItem & {id: string};
type Link = DisplayItem & {from: string; to: string};
export type ExplainerScene = {
  id: string; template: 'point' | 'compare' | 'steps' | 'cause' | 'image' | 'video' | 'code';
  startFrame: number; endFrame: number; durationInFrames: number; transitionFrames: number;
  segmentWindows: Record<string, {startFrame: number; endFrame: number}>;
  content: {title: string; summary?: DisplayItem; columns?: Array<{title: string; items: DisplayItem[]}>;
    items?: DisplayItem[]; nodes?: Node[]; links?: Link[]; caption?: DisplayItem; fit?: 'contain' | 'cover'; photoZoom?: number};
  levels?: Record<string, number>; mediaPath?: string; trimStartFrames?: number;
};
export type ArticleExplainerProps = {
  version: 7; schemaVersion: 7; fps: 30; width: 1080; height: 1920; title: string; mediaBase?: string;
  visual: {theme: 'dark' | 'light'}; durationInFrames: number; compiledScenes: ExplainerScene[];
  subtitleCues: Array<{startFrame: number; endFrame: number; text: string}>;
};

function itemStart(scene: ExplainerScene, item: DisplayItem): number {
  return item.segmentId ? scene.segmentWindows[item.segmentId].startFrame : scene.startFrame;
}

export function revealProgress(frame: number, startFrame: number): number {
  return Math.max(0, Math.min(1, (frame - startFrame) / 8));
}
export function selectedStep(scene: ExplainerScene, frame: number): number {
  return (scene.content.items ?? []).reduce((current, item, index) =>
    frame >= itemStart(scene, item) ? index : current, -1);
}
export function highlightParts(text: string, keywords: string[]): Array<{text: string; highlight: boolean}> {
  const words = [...new Set(keywords)].filter(Boolean).sort((a, b) => b.length - a.length);
  const result: Array<{text: string; highlight: boolean}> = [];
  let cursor = 0;
  while (cursor < text.length) {
    const match = words.find(word => text.startsWith(word, cursor));
    if (match) {result.push({text: match, highlight: true}); cursor += match.length;}
    else {const last = result[result.length - 1]; if (last && !last.highlight) last.text += text[cursor];
      else result.push({text: text[cursor], highlight: false}); cursor++;}
  }
  return result;
}
function Copy({item, palette}: {item: DisplayItem; palette: Palette}) {
  return <span data-m2v-copy="">{highlightParts(item.text, item.keywords ?? []).map((part, i) =>
    <span key={i} style={part.highlight ? {color: palette.accent, fontWeight: 750} : {}}>{part.text}</span>)}</span>;
}
function Reveal({item, scene, frame, children, style}: {item: DisplayItem; scene: ExplainerScene; frame: number;
  children: React.ReactNode; style?: React.CSSProperties}) {
  const progress = revealProgress(frame, itemStart(scene, item));
  return <div data-m2v-reveal="" style={{...style, opacity: progress,
    transform: `translateY(${(1 - progress) * 12}px)`}}>{children}</div>;
}
const bodyStyle: React.CSSProperties = {fontSize: 40, lineHeight: 1.5, overflowWrap: 'anywhere'};

export function graphPositions(scene: ExplainerScene): Record<string, {x: number; y: number}> {
  const nodes = scene.content.nodes ?? [];
  const levels = scene.levels ?? {};
  const maximum = Math.max(0, ...Object.values(levels));
  const result: Record<string, {x: number; y: number}> = {};
  for (let level = 0; level <= maximum; level++) {
    const row = nodes.filter(node => levels[node.id] === level);
    row.forEach((node, index) => {result[node.id] = {x: (index + 0.5) * 864 / row.length,
      y: maximum === 0 ? 470 : 80 + level * 900 / maximum};});
  }
  return result;
}
function Cause({scene, frame, palette}: {scene: ExplainerScene; frame: number; palette: Palette}) {
  const positions = graphPositions(scene);
  const nodes = scene.content.nodes ?? [];
  return <div style={{position: 'relative', height: 1100, width: 864}}>
    <svg width="864" height="1100" style={{position: 'absolute', inset: 0}}>
      <defs><marker id={`arrow-${scene.id}`} markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
        <path d="M0,0 L10,5 L0,10 Z" fill={palette.accent}/></marker></defs>
      {(scene.content.links ?? []).map((link, index) => {
        const a = positions[link.from], b = positions[link.to];
        const start = Math.max(itemStart(scene, link),
          ...nodes.filter(node => node.id === link.from || node.id === link.to).map(node => itemStart(scene, node)));
        return <g key={index} opacity={revealProgress(frame, start)}>
          <path d={`M${a.x},${a.y + 50} L${b.x},${b.y - 50}`} stroke={palette.accent} strokeWidth="4" markerEnd={`url(#arrow-${scene.id})`}/>
        </g>;
      })}
    </svg>
    {nodes.map(node => {
      const pos = positions[node.id];
      const peers = nodes.filter(n => scene.levels?.[n.id] === scene.levels?.[node.id]).length;
      return <Reveal key={node.id} item={node} scene={scene} frame={frame} style={{position: 'absolute',
        left: pos.x - Math.min(300, 820 / peers) / 2, top: pos.y - 50, width: Math.min(300, 820 / peers)}}>
        <div data-m2v-box="" style={{...bodyStyle, fontSize: 30, padding: '16px 12px', border: `2px solid ${palette.border}`,
          borderRadius: 16, background: palette.panel, textAlign: 'center'}}><Copy item={node} palette={palette}/></div>
      </Reveal>;
    })}
    <div style={{position: 'absolute', top: 1050, width: '100%', display: 'grid', gap: 10}}>
      {(scene.content.links ?? []).map((link, i) => <Reveal key={i} item={link} scene={scene} frame={frame}>
        <div data-m2v-box="" style={{fontSize: 26, lineHeight: 1.3, overflowWrap: 'anywhere'}}><Copy item={link} palette={palette}/></div>
      </Reveal>)}
    </div>
  </div>;
}
function SceneCard({scene, palette, frame, base}: {scene: ExplainerScene; palette: Palette; frame: number; base: string}) {
  const content = scene.content;
  const active = selectedStep(scene, frame);
  return <AbsoluteFill data-m2v-scene={scene.id} style={{zIndex: 1, background: palette.bg, color: palette.ink,
    fontFamily: FONT_STACK, padding: '160px 108px 420px', gap: 54}}>
    <div data-m2v-box="" style={{fontSize: 68, lineHeight: 1.5, fontWeight: 750, overflowWrap: 'anywhere'}}>
      <span data-m2v-copy="">{content.title}</span>
    </div>
    <div data-m2v-content="" style={{position: 'relative', flex: 1, minHeight: 0}}>
      {scene.template === 'code' && <div style={{width: 864, height: 920, overflow: 'hidden'}}>
        <OffthreadVideo src={base + scene.mediaPath!.split('/').map(encodeURIComponent).join('/')} muted
          trimBefore={0} trimAfter={scene.durationInFrames} style={{width: 864, height: 920, objectFit: 'contain'}}/>
      </div>}
      {scene.template === 'point' && content.summary && <Reveal item={content.summary} scene={scene} frame={frame}>
        <div data-m2v-box="" style={{...bodyStyle, fontSize: 50, padding: 44, background: palette.panel, borderRadius: 24}}>
          <Copy item={content.summary} palette={palette}/></div></Reveal>}
      {scene.template === 'compare' && <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28}}>
        {content.columns?.map((column, i) => <div key={i} data-m2v-box="" style={{padding: 28, borderRadius: 24,
          background: palette.panel, border: `2px solid ${palette.border}`, minWidth: 0}}>
          <div style={{fontSize: 40, lineHeight: 1.5, color: palette.accent, fontWeight: 700, marginBottom: 32}}>
            <span data-m2v-copy="">{column.title}</span></div>
          {column.items.map((item, j) => <Reveal key={j} item={item} scene={scene} frame={frame}>
            <div data-m2v-box="" style={{...bodyStyle, fontSize: 34, marginTop: 28}}><Copy item={item} palette={palette}/></div>
          </Reveal>)}
        </div>)}
      </div>}
      {scene.template === 'steps' && <div style={{display: 'grid', gap: 24}}>{content.items?.map((item, i) =>
        <Reveal key={i} item={item} scene={scene} frame={frame}><div data-m2v-box="" style={{...bodyStyle, padding: '24px 28px',
          borderRadius: 20, background: palette.panel, border: `3px solid ${i === active ? palette.accent : palette.border}`}}>
          <span style={{color: palette.accent, marginRight: 20}}>{i + 1}.</span><Copy item={item} palette={palette}/>
        </div></Reveal>)}</div>}
      {scene.template === 'cause' && <Cause scene={scene} frame={frame} palette={palette}/>}
      {(scene.template === 'image' || scene.template === 'video') && <>
        <div style={{width: '100%', height: 760, overflow: 'hidden', borderRadius: 22}}>
        {scene.template === 'video' ? <OffthreadVideo src={base + scene.mediaPath!.split('/').map(encodeURIComponent).join('/')}
          trimBefore={scene.trimStartFrames ?? 0} trimAfter={(scene.trimStartFrames ?? 0) + scene.durationInFrames} muted
          style={{width: '100%', height: '100%', objectFit: content.fit ?? 'contain'}}/> :
          <Img src={base + scene.mediaPath!.split('/').map(encodeURIComponent).join('/')} style={{width: '100%', height: '100%',
            objectFit: content.fit ?? 'contain', objectPosition: 'center',
            transform: `scale(${1 + ((content.photoZoom ?? 1) - 1) * Math.max(0, Math.min(1, (frame-scene.startFrame)/Math.max(1, scene.durationInFrames-1)))})`}}/>}
        </div>
        {content.caption && <Reveal item={content.caption} scene={scene} frame={frame}><div data-m2v-box="" style={{...bodyStyle, marginTop: 36}}>
          <Copy item={content.caption} palette={palette}/></div></Reveal>}</>}
    </div>
  </AbsoluteFill>;
}
export const ArticleExplainer: React.FC<ArticleExplainerProps> = props => {
  const frame = useCurrentFrame();
  const palette = palettes[props.visual.theme];
  const cue = props.subtitleCues.find(item => item.startFrame <= frame && frame < item.endFrame);
  return <AbsoluteFill style={{background: palette.bg}}>
    {props.compiledScenes.map(scene => <Sequence key={scene.id} from={scene.startFrame} durationInFrames={scene.durationInFrames} layout="none">
      <AbsoluteFill style={{opacity: scene.transitionFrames ? Math.max(0, Math.min(1, (frame - scene.startFrame) / (scene.transitionFrames - 1))) : 1}}>
        <SceneCard scene={scene} palette={palette} frame={frame} base={props.mediaBase ?? ''}/>
      </AbsoluteFill>
    </Sequence>)}
    {/* 场景自带 z-index: 1（见 SceneCard），字幕必须覆盖场景背景，因此为 2。 */}
    <div data-m2v-subtitle="" style={{position: 'absolute', zIndex: 2, left: 108, right: 108, top: 1580, height: 200,
      fontFamily: FONT_STACK, fontSize: 40, lineHeight: 1.5, color: palette.ink, textAlign: 'center', overflowWrap: 'anywhere'}}>
      {cue && <span data-m2v-copy="">{cue.text}</span>}
    </div>
  </AbsoluteFill>;
};
