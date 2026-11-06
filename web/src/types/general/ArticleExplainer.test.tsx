import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { frameOf } from '../../frames';
import { ArticleExplainer, type ArticleExplainerProps } from './ArticleExplainer';

const currentFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('@remotion/transitions', async importOriginal => {
  const actual = await importOriginal<typeof import('@remotion/transitions')>();
  const Series = ({children}: {children: React.ReactNode}) => <div>{children}</div>;
  return {...actual, TransitionSeries: Object.assign(Series, {
    Sequence: ({children, durationInFrames}: {children: React.ReactNode; durationInFrames: number}) =>
      <div data-duration={durationInFrames}>{children}</div>,
    Transition: ({timing}: {timing: {getDurationInFrames: (args: {fps: number}) => number}}) =>
      <span data-overlap={timing.getDurationInFrames({fps: 30})}/>,
  })};
});
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return {
    ...actual,
    AbsoluteFill: ({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) =>
      <div data-m2v-fill="" style={style}>{children}</div>,
    OffthreadVideo: ({ src, style }: { src: string; style?: React.CSSProperties }) =>
      <video data-m2v-clip="" src={src} style={style} />,
    Sequence: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    useCurrentFrame: () => currentFrame.value,
  };
});

const portrait = frameOf(1080, 1920);
const landscape = frameOf(1920, 1080);

function props(overrides: Partial<ArticleExplainerProps> = {}): ArticleExplainerProps {
  const frame = landscape;
  return {
    version: 8, schemaVersion: 8, fps: 30, width: frame.width, height: frame.height, title: '测试',
    subtitle: frame.subtitle, durationInFrames: 90,
    compiledScenes: [{ id: 'a', startFrame: 0, endFrame: 72, durationInFrames: 72, transitionFrames: 0, transition: 'cut', mediaPath: 'outputs/code-cache/a.mp4' },
      { id: 'b', startFrame: 60, endFrame: 90, durationInFrames: 30, transitionFrames: 12, transition: 'crossfade', mediaPath: 'outputs/code-cache/b.mp4' }],
    subtitleCues: [{ startFrame: 0, endFrame: 30, text: '第一句字幕' }, { startFrame: 60, endFrame: 90, text: '第二句字幕' }],
    ...overrides,
  };
}

function render(frame: number, overrides: Partial<ArticleExplainerProps> = {}): string {
  currentFrame.value = frame;
  return renderToStaticMarkup(<ArticleExplainer {...props(overrides)} />);
}

describe('通用作品合成层', () => {
  it('字幕只在对应的旁白帧内出现，无讲话的帧不显示', () => {
    expect(render(0)).toContain('第一句字幕');
    expect(render(29)).toContain('第一句字幕');
    expect(render(30)).not.toContain('第一句字幕');
    expect(render(45)).not.toContain('data-m2v-copy');
    expect(render(60)).toContain('第二句字幕');
    expect(render(89)).toContain('第二句字幕');
  });

  it('字幕容器就是该画幅的安全区矩形，且与清单取值一致', () => {
    const markup = render(0, {width: 1080, height: 1920, subtitle: portrait.subtitle});
    for (const value of [`left:${portrait.subtitle.safeArea.x}px`, `top:${portrait.subtitle.safeArea.y}px`,
      `width:${portrait.subtitle.safeArea.width}px`, `height:${portrait.subtitle.safeArea.height}px`]) {
      expect(markup).toContain(value);
    }
    expect(markup).toContain(`font-size:${portrait.subtitle.fontSize}px`);
    const wide = render(0, {width: 1920, height: 1080, subtitle: landscape.subtitle});
    expect(wide).toContain(`left:${landscape.subtitle.safeArea.x}px`);
    expect(wide).toContain(`top:${landscape.subtitle.safeArea.y}px`);
    expect(wide).toContain(`font-size:${landscape.subtitle.fontSize}px`);
  });

  it('字幕用不透明深色底板与白字，不读取作品配色', () => {
    const wide = render(0, {width: 1920, height: 1080, subtitle: landscape.subtitle});
    expect(wide).toContain(`background:${landscape.subtitle.plateColor}`);
    expect(wide).toContain(`color:${landscape.subtitle.textColor}`);
    expect(landscape.subtitle.plateColor).toBe('#0b0d12');
    expect(landscape.subtitle.textColor).toBe('#ffffff');
  });

  it('合成直接采用准备样式中的作品字号，且不修改画幅默认值', () => {
    const markup = render(0, {subtitle: {...landscape.subtitle, fontSize: 52}});
    expect(markup).toContain('font-size:52px');
    expect(markup).toContain(`line-height:${landscape.subtitle.lineHeight}`);
    expect(landscape.subtitle.fontSize).toBe(40);
  });

  it('片段时长和重叠窗口交给统一转场，首幕没有转场', () => {
    const first = render(0);
    expect(first).toContain('outputs/code-cache/a.mp4');
    expect(first).toContain('data-duration="72"');
    expect(first).toContain('data-duration="30"');
    expect(first.match(/data-overlap=/g)).toHaveLength(1);
    expect(first).toContain('data-overlap="12"');
  });

  it('画幅不同也走同一条合成路径：片段铺满画布', () => {
    const wide = render(0, {width: 1920, height: 1080, subtitle: landscape.subtitle});
    expect(wide).toContain('outputs/code-cache/a.mp4');
    expect(wide).toContain('width:100%;height:100%');
  });
});
