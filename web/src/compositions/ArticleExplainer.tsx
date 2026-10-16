import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, useCurrentFrame} from 'remotion';
import {composition, layout, motion, palettes, shape, typeScale, typography,
  type Composition, type Layout, type Motion, type Palette, type Shape, type Theme, type TypeScale, type Typography} from '../palette';
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
  visual: {theme: Theme}; durationInFrames: number; compiledScenes: ExplainerScene[];
  subtitleCues: Array<{startFrame: number; endFrame: number; text: string}>;
};

/** 一套主题解析后的全部画面取值。一次解出、逐层下传，避免每个组件各自按名字再取一遍。 */
type Look = {palette: Palette; type: Typography; shape: Shape; layout: Layout;
  scale: TypeScale; where: Composition; move: Motion};

function itemStart(scene: ExplainerScene, item: DisplayItem): number {
  return item.segmentId ? scene.segmentWindows[item.segmentId].startFrame : scene.startFrame;
}

/** 线性：控制点为 `[0,0,1,1]`。默认值走这条通路，既有画面因此逐帧不变。 */
const LINEAR = [0, 0, 1, 1] as const;
const curves = new Map<string, (x: number) => number>();

const bezierComponent = (first: number, second: number, t: number): number =>
  ((1 - 3 * second + 3 * first) * t + (3 * second - 6 * first)) * t * t + 3 * first * t;
const bezierSlope = (first: number, second: number, t: number): number =>
  3 * (1 - 3 * second + 3 * first) * t * t + 2 * (3 * second - 6 * first) * t + 3 * first;

/** 三次贝塞尔缓动。逐帧求值，不产生 CSS 动画，因此源码闸门不受影响。
 *  先用牛顿法逼近，退化时退回二分——两者都是纯算术，同一帧的结果与 seek 历史无关。 */
function easingCurve([x1, y1, x2, y2]: readonly number[]): (x: number) => number {
  if (x1 === y1 && x2 === y2) return x => x;
  const key = `${x1},${y1},${x2},${y2}`;
  const cached = curves.get(key);
  if (cached) return cached;
  const curve = (x: number): number => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let step = 0; step < 8; step++) {
      const error = bezierComponent(x1, x2, t) - x;
      if (Math.abs(error) < 1e-6) return bezierComponent(y1, y2, t);
      const slope = bezierSlope(x1, x2, t);
      if (Math.abs(slope) < 1e-6) break;
      t -= error / slope;
    }
    let low = 0, high = 1;
    t = x;
    for (let step = 0; step < 24; step++) {
      const value = bezierComponent(x1, x2, t);
      if (Math.abs(value - x) < 1e-6) break;
      if (value < x) low = t; else high = t;
      t = (low + high) / 2;
    }
    return bezierComponent(y1, y2, t);
  };
  curves.set(key, curve);
  return curve;
}

export function revealProgress(frame: number, startFrame: number, entranceFrames = 8,
  easing: readonly number[] = LINEAR): number {
  const progress = Math.max(0, Math.min(1, (frame - startFrame) / Math.max(1, entranceFrames)));
  return easingCurve(easing)(progress);
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
function Reveal({item, scene, frame, children, style, look}: {item: DisplayItem; scene: ExplainerScene; frame: number;
  children: React.ReactNode; style?: React.CSSProperties; look: Look}) {
  const progress = revealProgress(frame, itemStart(scene, item), look.move.entranceFrames, look.move.entranceEasing);
  return <div data-m2v-reveal="" style={{...style, opacity: progress,
    transform: `translateY(${(1 - progress) * 12}px)`}}>{children}</div>;
}
/** 正文块的共同样式：字号与行高都来自主题。 */
const bodyStyle = (look: Look): React.CSSProperties =>
  ({fontSize: look.scale.body, lineHeight: look.type.bodyLineHeight, overflowWrap: 'anywhere'});

/** 因果图的坐标。纵向比例相对图形高度，因此主题改图形尺寸时图会整体缩放。
 *  一张图的坐标是内容而不是令牌，所以比例留在组件里。 */
export function graphPositions(scene: ExplainerScene, figureHeight = 1100): Record<string, {x: number; y: number}> {
  const nodes = scene.content.nodes ?? [];
  const levels = scene.levels ?? {};
  const maximum = Math.max(0, ...Object.values(levels));
  const result: Record<string, {x: number; y: number}> = {};
  for (let level = 0; level <= maximum; level++) {
    const row = nodes.filter(node => levels[node.id] === level);
    row.forEach((node, index) => {result[node.id] = {x: (index + 0.5) * 864 / row.length,
      y: maximum === 0 ? figureHeight * 470 / 1100 : figureHeight * 80 / 1100 + level * (figureHeight * 900 / 1100) / maximum};});
  }
  return result;
}
function Cause({scene, frame, look}: {scene: ExplainerScene; frame: number; look: Look}) {
  const {palette, shape: skin, layout: box} = look;
  const positions = graphPositions(scene, box.causeHeight);
  const nodes = scene.content.nodes ?? [];
  return <div style={{position: 'relative', height: box.causeHeight, width: box.figureWidth}}>
    <svg width={box.figureWidth} height={box.causeHeight} style={{position: 'absolute', inset: 0}}>
      <defs><marker id={`arrow-${scene.id}`} markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
        <path d="M0,0 L10,5 L0,10 Z" fill={palette.accent}/></marker></defs>
      {(scene.content.links ?? []).map((link, index) => {
        const a = positions[link.from], b = positions[link.to];
        const start = Math.max(itemStart(scene, link),
          ...nodes.filter(node => node.id === link.from || node.id === link.to).map(node => itemStart(scene, node)));
        return <g key={index} opacity={revealProgress(frame, start, look.move.entranceFrames, look.move.entranceEasing)}>
          <path d={`M${a.x},${a.y + 50} L${b.x},${b.y - 50}`} stroke={palette.accent} strokeWidth={skin.arrowWidth}
            markerEnd={`url(#arrow-${scene.id})`}/></g>;
      })}
    </svg>
    {nodes.map(node => {
      const pos = positions[node.id];
      const peers = nodes.filter(n => scene.levels?.[n.id] === scene.levels?.[node.id]).length;
      return <Reveal key={node.id} item={node} scene={scene} frame={frame} look={look} style={{position: 'absolute',
        left: pos.x - Math.min(300, 820 / peers) / 2, top: pos.y - 50, width: Math.min(300, 820 / peers)}}>
        <div data-m2v-box="" style={{...bodyStyle(look), fontSize: look.scale.small,
          padding: `${box.nodePaddingY}px ${box.nodePaddingX}px`, border: `${skin.panelRule}px solid ${palette.border}`,
          borderRadius: skin.nodeRadius, background: palette.panel, textAlign: 'center'}}><Copy item={node} palette={palette}/></div>
      </Reveal>;
    })}
    <div style={{position: 'absolute', top: box.causeLabelTop, width: '100%', display: 'grid', gap: box.nodeGap}}>
      {(scene.content.links ?? []).map((link, i) => <Reveal key={i} item={link} scene={scene} frame={frame} look={look}>
        <div data-m2v-box="" style={{fontSize: look.scale.micro, lineHeight: 1.3, overflowWrap: 'anywhere'}}><Copy item={link} palette={palette}/></div>
      </Reveal>)}
    </div>
  </div>;
}
function SceneCard({scene, frame, base, look}: {scene: ExplainerScene; frame: number; base: string; look: Look}) {
  const {palette, type, shape: skin, layout: box, scale} = look;
  const content = scene.content;
  const active = selectedStep(scene, frame);
  // 垂直居中靠「外壳居中 + 内容块取自然高度」实现；不居中时内容块撑满，
  // 因此既有主题的位移逐像素不变。
  const centered = look.where.verticalAlign === 'center';
  return <AbsoluteFill data-m2v-scene={scene.id} style={{zIndex: 1, background: palette.bg, color: palette.ink,
    fontFamily: FONT_STACK, padding: `${box.sceneTop}px 108px ${box.sceneBottom}px`, gap: box.titleGap,
    justifyContent: centered ? 'center' : 'flex-start', textAlign: look.where.align}}>
    <div data-m2v-box="" style={{fontSize: scale.title, lineHeight: 1.5, fontWeight: type.titleWeight,
      letterSpacing: type.titleTracking, textTransform: type.titleTransform, overflowWrap: 'anywhere'}}>
      <span data-m2v-copy="">{content.title}</span>
    </div>
    <div data-m2v-content="" style={{position: 'relative', minHeight: 0, ...(centered ? {} : {flex: 1})}}>
      {scene.template === 'code' && <div style={{width: box.figureWidth, height: box.codeHeight, overflow: 'hidden',
        margin: centered ? '0 auto' : undefined}}>
        <OffthreadVideo src={base + scene.mediaPath!.split('/').map(encodeURIComponent).join('/')} muted
          trimBefore={0} trimAfter={scene.durationInFrames}
          style={{width: box.figureWidth, height: box.codeHeight, objectFit: 'contain'}}/>
      </div>}
      {scene.template === 'point' && content.summary && <Reveal item={content.summary} scene={scene} frame={frame} look={look}>
        <div data-m2v-box="" style={{...bodyStyle(look), fontSize: scale.lead, padding: box.panelPadding,
          background: palette.panel, borderRadius: skin.panelRadius}}>
          <Copy item={content.summary} palette={palette}/></div></Reveal>}
      {scene.template === 'compare' && <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: box.columnGap}}>
        {content.columns?.map((column, i) => <div key={i} data-m2v-box="" style={{padding: box.columnPadding,
          borderRadius: skin.panelRadius, background: palette.panel,
          border: `${skin.panelRule}px solid ${palette.border}`, minWidth: 0}}>
          <div style={{fontSize: scale.body, lineHeight: 1.5, color: palette.accent, fontWeight: 700, marginBottom: box.columnLabelGap}}>
            <span data-m2v-copy="">{column.title}</span></div>
          {column.items.map((item, j) => <Reveal key={j} item={item} scene={scene} frame={frame} look={look}>
            <div data-m2v-box="" style={{...bodyStyle(look), fontSize: scale.note, marginTop: box.columnItemGap}}><Copy item={item} palette={palette}/></div>
          </Reveal>)}
        </div>)}
      </div>}
      {scene.template === 'steps' && <div style={{display: 'grid', gap: box.cardGap}}>{content.items?.map((item, i) =>
        <Reveal key={i} item={item} scene={scene} frame={frame} look={look}><div data-m2v-box="" style={{...bodyStyle(look),
          padding: `${box.cardPaddingY}px ${box.cardPaddingX}px`, borderRadius: skin.cardRadius, background: palette.panel,
          border: `${skin.cardRule}px solid ${i === active ? palette.accent : palette.border}`}}>
          <span style={{color: palette.accent, marginRight: box.numberGap}}>{i + 1}.</span><Copy item={item} palette={palette}/>
        </div></Reveal>)}</div>}
      {scene.template === 'cause' && <Cause scene={scene} frame={frame} look={look}/>}
      {(scene.template === 'image' || scene.template === 'video') && <>
        <div style={{width: '100%', height: box.mediaHeight, overflow: 'hidden', borderRadius: skin.mediaRadius}}>
        {scene.template === 'video' ? <OffthreadVideo src={base + scene.mediaPath!.split('/').map(encodeURIComponent).join('/')}
          trimBefore={scene.trimStartFrames ?? 0} trimAfter={(scene.trimStartFrames ?? 0) + scene.durationInFrames} muted
          style={{width: '100%', height: '100%', objectFit: content.fit ?? 'contain'}}/> :
          <Img src={base + scene.mediaPath!.split('/').map(encodeURIComponent).join('/')} style={{width: '100%', height: '100%',
            objectFit: content.fit ?? 'contain', objectPosition: 'center',
            transform: `scale(${1 + ((content.photoZoom ?? 1) - 1) * Math.max(0, Math.min(1, (frame-scene.startFrame)/Math.max(1, scene.durationInFrames-1)))})`}}/>}
        </div>
        {content.caption && <Reveal item={content.caption} scene={scene} frame={frame} look={look}>
          <div data-m2v-box="" style={{...bodyStyle(look), marginTop: box.captionGap}}>
            <Copy item={content.caption} palette={palette}/></div></Reveal>}</>}
    </div>
  </AbsoluteFill>;
}
export const ArticleExplainer: React.FC<ArticleExplainerProps> = props => {
  const frame = useCurrentFrame();
  const theme = props.visual.theme;
  const look: Look = {palette: palettes[theme], type: typography(theme), shape: shape(theme),
    layout: layout(theme), scale: typeScale(theme), where: composition(theme), move: motion(theme)};
  const cue = props.subtitleCues.find(item => item.startFrame <= frame && frame < item.endFrame);
  return <AbsoluteFill style={{background: look.palette.bg}}>
    {props.compiledScenes.map(scene => <Sequence key={scene.id} from={scene.startFrame} durationInFrames={scene.durationInFrames} layout="none">
      <AbsoluteFill style={{opacity: scene.transitionFrames ? Math.max(0, Math.min(1, (frame - scene.startFrame) / (scene.transitionFrames - 1))) : 1}}>
        <SceneCard scene={scene} frame={frame} base={props.mediaBase ?? ''} look={look}/>
      </AbsoluteFill>
    </Sequence>)}
    {/* 场景自带 z-index: 1（见 SceneCard），字幕必须覆盖场景背景，因此为 2。 */}
    <div data-m2v-subtitle="" style={{position: 'absolute', zIndex: 2,
      left: 'var(--m2v-subtitle-inset-x)', right: 'var(--m2v-subtitle-inset-x)',
      top: 'var(--m2v-subtitle-top)', height: 'var(--m2v-subtitle-height)',
      fontFamily: FONT_STACK, fontSize: 'var(--m2v-subtitle-size)', lineHeight: 'var(--m2v-subtitle-leading)',
      color: look.palette.ink, textAlign: 'center', overflowWrap: 'anywhere'}}>
      {cue && <span data-m2v-copy="">{cue.text}</span>}
    </div>
  </AbsoluteFill>;
};
