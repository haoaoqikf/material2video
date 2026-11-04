import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, useCurrentFrame} from 'remotion';
import {TransitionSeries} from '@remotion/transitions';
import {transitionPresentation, transitionTiming, type SceneTransition} from '../../transitions';
import type {SubtitleStyle} from '../../frames';
import {FONT_STACK} from '../../fonts';

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
export type ArticleExplainerProps = {
  version: 8; schemaVersion: 8; fps: number; width: number; height: number; title: string; mediaBase?: string;
  subtitle: SubtitleStyle; durationInFrames: number; compiledScenes: ExplainerScene[];
  subtitleCues: Array<{startFrame: number; endFrame: number; text: string}>;
};

/** 底板内边距随字号缩放：字幕几何只有一处真源（`frames.json`），比例留在这里。 */
const platePadding = (size: number): string => `${Math.round(size * 0.2)}px ${Math.round(size * 0.5)}px`;

export const ArticleExplainer: React.FC<ArticleExplainerProps> = props => {
  const frame = useCurrentFrame();
  const {subtitle} = props;
  const {safeArea} = subtitle;
  const cue = props.subtitleCues.find(item => item.startFrame <= frame && frame < item.endFrame);
  return (
    // 片段铺满整张画布，因此这一层底色只在转场期间透出；首幕固定 cut，实际不会看到。
    <AbsoluteFill style={{background: '#000'}}>
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
      <div data-m2v-subtitle="" style={{position: 'absolute', zIndex: 2,
        left: safeArea.x, top: safeArea.y, width: safeArea.width, height: safeArea.height,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: FONT_STACK, fontSize: subtitle.fontSize, lineHeight: subtitle.lineHeight,
        color: subtitle.textColor, textAlign: 'center'}}>
        {cue && <span data-m2v-copy="" style={{maxWidth: '100%', overflowWrap: 'anywhere',
          background: subtitle.plateColor, padding: platePadding(subtitle.fontSize)}}>{cue.text}</span>}
      </div>
    </AbsoluteFill>
  );
};
