import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, Sequence, useCurrentFrame } from 'remotion';

/**
 * 在线素材剪辑的画面：静图做推拉平移、短视频按裁剪入出点播放、幕间硬切或交叉淡化。
 *
 * 时间轴与运动参数全部由 Python 侧准备阶段编译，这里只做帧到视觉的映射，不推导
 * 时序。素材地址是 `mediaBase`（渲染期注入的回环地址）加上作品内相对路径，因此
 * 画面本身不依赖任何外部网络。
 */
export type StockMontageAsset = {
  kind: 'video' | 'photo';
  path: string;
  trimStartFrames: number;
  author: string;
  sourceUrl: string;
  license: string;
  width: number;
  height: number;
};
export type StockMontageMotion = {
  zoomFrom: number; zoomTo: number;
  panXFrom: number; panXTo: number;
  panYFrom: number; panYTo: number;
};
export type StockMontageScene = {
  id: string;
  startFrame: number; endFrame: number; durationInFrames: number; transitionFrames: number;
  providerName: string;
  asset: StockMontageAsset;
  motion: StockMontageMotion | null;
};
export type StockMontageProps = {
  schemaVersion: 1; topic: string; fps: number; width: number; height: number; durationInFrames: number;
  theme: 'dark' | 'light'; attribution: string; mediaBase: string;
  compiledScenes: StockMontageScene[];
  subtitleCues: Array<{ startFrame: number; endFrame: number; text: string }>;
};

const palettes = {
  dark: { bg: '#0d1117', ink: '#f3f4f6', shadow: '0 2px 10px rgba(0,0,0,.85)', band: 'rgba(6,10,14,.55)' },
  light: { bg: '#f4f2ed', ink: '#161c24', shadow: '0 2px 10px rgba(255,255,255,.9)', band: 'rgba(255,255,255,.62)' },
};

/** 幕内进度：0 是首帧，1 是末帧；单帧幕直接取 1，避免除零。 */
export function sceneProgress(scene: StockMontageScene, frame: number): number {
  if (scene.durationInFrames <= 1) return 1;
  const local = Math.min(Math.max(frame - scene.startFrame, 0), scene.durationInFrames - 1);
  return local / (scene.durationInFrames - 1);
}

/** 入场幕在重叠帧内从不透明到完全显示；硬切与首幕恒为 1。 */
export function sceneOpacity(scene: StockMontageScene, frame: number): number {
  const overlap = scene.transitionFrames;
  if (!overlap || overlap <= 1) return 1;
  const local = frame - scene.startFrame;
  if (local >= overlap) return 1;
  return Math.max(0, Math.min(1, local / (overlap - 1)));
}

/** 静图变换：缩放与平移在整幕内线性推进，参数由准备阶段给出。 */
export function photoTransform(motion: StockMontageMotion | null, progress: number): string {
  if (!motion) return 'scale(1)';
  const zoom = motion.zoomFrom + (motion.zoomTo - motion.zoomFrom) * progress;
  const panX = (motion.panXFrom + (motion.panXTo - motion.panXFrom) * progress) * 100;
  const panY = (motion.panYFrom + (motion.panYTo - motion.panYFrom) * progress) * 100;
  return `translate(${panX.toFixed(3)}%, ${panY.toFixed(3)}%) scale(${zoom.toFixed(4)})`;
}

export function activeSubtitle(cues: StockMontageProps['subtitleCues'], frame: number): string | null {
  const cue = (cues ?? []).find(item => item.startFrame <= frame && frame < item.endFrame);
  return cue ? cue.text : null;
}

export function mediaUrl(base: string, path: string): string {
  return `${base}${path.split('/').map(encodeURIComponent).join('/')}`;
}

function SceneMedia({ scene, frame, base }: { scene: StockMontageScene; frame: number; base: string }): React.ReactElement {
  const source = mediaUrl(base, scene.asset.path);
  if (scene.asset.kind === 'video') {
    return (
      <OffthreadVideo
        data-m2v-asset-kind="video"
        src={source}
        trimBefore={scene.asset.trimStartFrames}
        trimAfter={scene.asset.trimStartFrames + scene.durationInFrames}
        muted
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />
    );
  }
  return (
    <Img
      data-m2v-asset-kind="photo"
      src={source}
      style={{
        width: '100%', height: '100%', objectFit: 'cover',
        transform: photoTransform(scene.motion, sceneProgress(scene, frame)),
      }}
    />
  );
}

export const StockMontage: React.FC<StockMontageProps> = props => {
  const frame = useCurrentFrame();
  const palette = palettes[props.theme];
  const subtitle = activeSubtitle(props.subtitleCues, frame);
  const current = props.compiledScenes.find(
    scene => scene.startFrame <= frame && frame < scene.endFrame) ?? props.compiledScenes[0];
  return (
    <AbsoluteFill style={{ background: palette.bg }}>
      {props.compiledScenes.map(scene => (
        <Sequence key={scene.id} from={scene.startFrame} durationInFrames={scene.durationInFrames} layout="none">
          <AbsoluteFill data-m2v-scene={scene.id} style={{ opacity: sceneOpacity(scene, frame) }}>
            <SceneMedia scene={scene} frame={frame} base={props.mediaBase} />
          </AbsoluteFill>
        </Sequence>
      ))}
      <AbsoluteFill data-m2v-attribution="" style={{
        top: 'auto', height: 92, background: palette.band, color: palette.ink,
        fontFamily: 'M2V Sans, sans-serif', fontSize: 26, lineHeight: 1.35,
        padding: '12px 48px', display: 'flex', alignItems: 'center', justifyContent: 'center',
        textAlign: 'center', textShadow: palette.shadow,
      }}>
        {current ? `${props.attribution} · 本幕素材：${current.asset.author}（${current.providerName}）` : props.attribution}
      </AbsoluteFill>
      {subtitle && (
        <div data-m2v-subtitle="" style={{
          position: 'absolute', left: 96, right: 96, bottom: 168,
          fontFamily: 'M2V Sans, sans-serif', fontSize: 46, lineHeight: 1.4, fontWeight: 600,
          color: palette.ink, textAlign: 'center', textShadow: palette.shadow, overflowWrap: 'anywhere',
        }}>
          {subtitle}
        </div>
      )}
    </AbsoluteFill>
  );
};
