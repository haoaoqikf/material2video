import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import {
  StockMontage, activeSubtitle, mediaUrl, photoTransform, sceneOpacity, sceneProgress,
  type StockMontageProps, type StockMontageScene,
} from './StockMontage';

const currentFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return {
    ...actual,
    AbsoluteFill: ({ children, ...rest }: { children: React.ReactNode }) => <div {...rest}>{children}</div>,
    Sequence: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Img: (props: Record<string, unknown>) => <img {...props} />,
    OffthreadVideo: (props: Record<string, unknown>) => <video {...props} />,
    useCurrentFrame: () => currentFrame.value,
  };
});

const photo: StockMontageScene = {
  id: 'night', startFrame: 100, endFrame: 200, durationInFrames: 100, transitionFrames: 12,
  providerName: 'pexels',
  asset: { kind: 'photo', path: 'assets/stock/pexels-photo-201.jpg', trimStartFrames: 0,
    author: '作者丙', sourceUrl: 'https://example.org/photo/201', license: 'Pexels License', width: 1080, height: 1920 },
  motion: { zoomFrom: 1.12, zoomTo: 1, panXFrom: 0, panXTo: -0.02, panYFrom: 0, panYTo: 0 },
};
const video: StockMontageScene = {
  id: 'opening', startFrame: 0, endFrame: 100, durationInFrames: 100, transitionFrames: 0,
  providerName: 'pexels',
  asset: { kind: 'video', path: 'assets/stock/pexels-video-101.mp4', trimStartFrames: 15,
    author: '作者甲', sourceUrl: 'https://example.org/video/101', license: 'Pexels License', width: 1080, height: 1920 },
  motion: null,
};

const props: StockMontageProps = {
  schemaVersion: 1, topic: '城市清晨通勤', fps: 30, width: 1080, height: 1920, durationInFrames: 188,
  theme: 'dark', attribution: '素材来源：测试图库', mediaBase: 'http://127.0.0.1:9999/',
  compiledScenes: [video, photo],
  subtitleCues: [{ startFrame: 20, endFrame: 60, text: '第一句。' }],
};

describe('stock montage composition', () => {
  it('keeps motion and opacity on the compiled frame axis', () => {
    expect(sceneProgress(photo, photo.startFrame)).toBe(0);
    expect(sceneProgress(photo, photo.endFrame - 1)).toBe(1);
    expect(sceneProgress({ ...photo, durationInFrames: 1 }, photo.startFrame)).toBe(1);
    expect(sceneOpacity(photo, photo.startFrame)).toBe(0);
    expect(sceneOpacity(photo, photo.startFrame + photo.transitionFrames)).toBe(1);
    expect(sceneOpacity(video, video.startFrame)).toBe(1);
    expect(photoTransform(photo.motion, 0)).toContain('scale(1.1200)');
    expect(photoTransform(photo.motion, 1)).toContain('translate(-2.000%');
    expect(photoTransform(null, 0.5)).toBe('scale(1)');
  });

  it('encodes every media path segment and resolves the active subtitle', () => {
    expect(mediaUrl('http://127.0.0.1:9999/', 'assets/stock/a b.mp4'))
      .toBe('http://127.0.0.1:9999/assets/stock/a%20b.mp4');
    expect(activeSubtitle(props.subtitleCues, 30)).toBe('第一句。');
    expect(activeSubtitle(props.subtitleCues, 60)).toBeNull();
  });

  it('renders the video trim, the photo motion, the subtitle and the attribution', () => {
    currentFrame.value = 150;
    const markup = renderToStaticMarkup(<StockMontage {...props} />);
    expect(markup).toContain('data-m2v-scene="night"');
    expect(markup).toContain('data-m2v-scene="opening"');
    expect(markup).toContain('data-m2v-asset-kind="photo"');
    expect(markup).toContain('data-m2v-asset-kind="video"');
    expect(markup).toContain('http://127.0.0.1:9999/assets/stock/pexels-video-101.mp4');
    expect(markup).toContain('data-m2v-attribution');
    expect(markup).toContain('本幕素材：作者丙（pexels）');
    expect(markup).not.toContain('data-m2v-subtitle');
    expect(markup).not.toContain('<audio');
  });

  it('shows the subtitle only inside its frame window', () => {
    currentFrame.value = 30;
    const markup = renderToStaticMarkup(<StockMontage {...props} />);
    expect(markup).toContain('data-m2v-subtitle');
    expect(markup).toContain('第一句。');
  });
});
