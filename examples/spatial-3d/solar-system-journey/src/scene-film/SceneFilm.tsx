import React from 'react';
import {AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, useCurrentFrame} from 'remotion';
import {TransitionSeries} from '@remotion/transitions';
import {transitionPresentation, transitionTiming, type SceneTransition} from '../transitions';
import type {SubtitleStyle} from '../frames';
import {FONT_STACK} from '../fonts';

/** 准备阶段录制的无损片段：整幕画面都在里面，合成层只负责回放与转场。 */
export type ExplainerScene = {
  id: string;
  startFrame: number;
  endFrame: number;
  durationInFrames: number;
  transitionFrames: number;
  mediaPath: string;
  mediaStartFrame?: number;
  mediaDurationFrames?: number;
  /** 仅 lookdev 静帧合成注入；正式视频继续回放 mediaPath。 */
  stillPath?: string;
} & Record<'transition', SceneTransition>;
export type SceneFilmProps = {
  previewAudio?: string;
  version: 9; schemaVersion: 9; fps: number; width: number; height: number; title: string; mediaBase?: string;
  subtitle: SubtitleStyle; durationInFrames: number; compiledScenes: ExplainerScene[];
  subtitleCues: Array<{
    startFrame: number;
    endFrame: number;
    text: string;
    secondary?: string;
    backing?: {color: string; opacity: number; background: string; textColor: string};
  }>;
};

/** 字幕内边距随字号缩放，保持换行与旧版安全区一致。 */
const copyPadding = (size: number): string => `${Math.round(size * 0.2)}px ${Math.round(size * 0.5)}px`;

export const SceneFilm: React.FC<SceneFilmProps> = props => {
  const frame = useCurrentFrame();
  const {subtitle} = props;
  const {safeArea} = subtitle;
  const cue = props.subtitleCues.find(item => item.startFrame <= frame && frame < item.endFrame);
  const backing = cue?.backing;
  const textColor = backing?.textColor ?? subtitle.textColor;
  const textShadow = backing ? `0 1px 3px ${backing.color}bc, 0 2px 10px ${backing.color}91` : undefined;
  return (
    // 片段铺满整张画布，因此这一层底色只在转场期间透出；首幕固定 cut，实际不会看到。
    <AbsoluteFill style={{background: '#000'}}>
      {props.previewAudio && <Audio src={props.previewAudio}/>}
      <Sequence from={props.compiledScenes[0]?.startFrame ?? 0} layout="none">
      <TransitionSeries>
      {props.compiledScenes.flatMap((scene, index) => {
        const transition = scene.transition;
        return [index > 0 && transition !== 'cut' && scene.transitionFrames > 0
          ? <TransitionSeries.Transition key={`${scene.id}-transition`}
              presentation={transitionPresentation(transition, props.width, props.height)}
              timing={transitionTiming(scene.transitionFrames)}/> : null,
        <TransitionSeries.Sequence key={scene.id} durationInFrames={scene.durationInFrames}>
          <AbsoluteFill>
            {scene.stillPath ? <Img src={scene.stillPath} style={{width: '100%', height: '100%'}}/> :
            <Sequence from={scene.mediaStartFrame ?? 0} durationInFrames={scene.mediaDurationFrames ?? scene.durationInFrames} layout="none">
            <OffthreadVideo src={(props.mediaBase ?? '') + scene.mediaPath.split('/').map(encodeURIComponent).join('/')}
              muted trimBefore={0} trimAfter={scene.mediaDurationFrames ?? scene.durationInFrames}
              style={{width: '100%', height: '100%'}}/></Sequence>}
          </AbsoluteFill>
        </TransitionSeries.Sequence>];
      })}
      </TransitionSeries>
      </Sequence>
      {/* 字幕层压在所有片段之上；容器就是安全区矩形，换行宽度与 Python 量测判据同源。 */}
      {backing && subtitle.backing &&
        <div aria-hidden style={{position: 'absolute', zIndex: 1,
          left: 0, top: 0, right: 0, bottom: 0, pointerEvents: 'none',
          background: `radial-gradient(ellipse ${subtitle.backing.feather}px ${Math.round(safeArea.height * .59)}px at ${safeArea.x + safeArea.width / 2}px ${safeArea.y + safeArea.height / 2}px, ${backing.color} 0%, ${backing.color} 32%, transparent 100%)`,
          opacity: backing.opacity}}/>}
      <div data-m2v-subtitle="" style={{position: 'absolute', zIndex: 2,
        left: safeArea.x, top: safeArea.y, width: safeArea.width, height: safeArea.height,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: subtitle.fontFamily ?? FONT_STACK, fontSize: subtitle.fontSize,
        lineHeight: subtitle.lineHeight, color: textColor, textAlign: 'center'}}>
        {cue && <div data-m2v-copy="" style={{display: 'flex', flexDirection: 'column',
          alignItems: 'center', maxWidth: '100%', overflowWrap: 'anywhere',
          boxSizing: 'border-box', padding: copyPadding(subtitle.fontSize)}}>
          <div style={{fontFamily: subtitle.fontFamily ?? FONT_STACK, fontSize: subtitle.fontSize,
            lineHeight: subtitle.lineHeight, color: textColor, overflowWrap: 'anywhere',
            textShadow}}>{cue.text}</div>
          {cue.secondary && <div style={{fontFamily: subtitle.secondary?.fontFamily ?? FONT_STACK,
            fontSize: subtitle.secondary?.fontSize ?? Math.round(subtitle.fontSize * 0.6),
            lineHeight: subtitle.secondary?.lineHeight ?? 1.38,
            color: textColor,
            opacity: subtitle.secondary?.opacity ?? 1,
            marginTop: 12, textAlign: 'center', overflowWrap: 'anywhere',
            textShadow}}>{cue.secondary}</div>}
        </div>}
      </div>
    </AbsoluteFill>
  );
};
