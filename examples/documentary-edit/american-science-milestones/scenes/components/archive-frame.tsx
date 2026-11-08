/** 档案媒体框：图片或视频铺底，轻微缩放/漂移/去饱和；不覆盖主体，不加额外装饰。 */
import {useEffect, useRef, type CSSProperties} from 'react';
import {archiveGradient} from './kit';

export type ArchiveFrameProps = {
  src: string;
  kind: 'image' | 'video';
  progress?: number;
  ready?: () => void;
  style?: CSSProperties;
  startOffsetSeconds?: number;
  objectFit?: CSSProperties['objectFit'];
};

export default function ArchiveFrame({
  src, kind, progress = 0, ready, style, startOffsetSeconds = 0,
  objectFit = 'cover',
}: ArchiveFrameProps) {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (kind !== 'video') return;
    const element = video.current;
    if (!element) return;
    const seekAndPlay = () => {
      element.muted = true;
      if (startOffsetSeconds > 0) {
        element.currentTime = Math.min(startOffsetSeconds, Math.max(0, element.duration - 0.1));
      }
      void element.play().catch(() => undefined);
    };
    element.addEventListener('loadedmetadata', seekAndPlay, {once: true});
    if (element.readyState >= 1) seekAndPlay();
    return () => element.removeEventListener('loadedmetadata', seekAndPlay);
  }, [kind, startOffsetSeconds]);

  const base: CSSProperties = {
    width: '100%', height: '100%', objectFit,
    ...archiveGradient(progress),
    ...style,
  };
  if (kind === 'video') {
    return (
      <video
        ref={video}
        src={src}
        muted
        playsInline
        preload="auto"
        onCanPlay={ready}
        style={base}
      />
    );
  }
  return (
    <img
      src={src}
      onLoad={ready}
      style={base}
    />
  );
}
