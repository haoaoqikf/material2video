import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, expect, it, vi } from 'vitest';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';
let frame = 0;
vi.mock('remotion', () => ({ AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, useCurrentFrame: () => frame }));
import { M2VComposition } from './M2VComposition';

beforeEach(() => { frame = 0; });
it('共享 composition 字幕在真实帧边界显示，结束边界不显示', () => {
  const props = { ...EMPTY_STORYBOARD, subtitleCues: [{ start: 1, end: 2, text: '共同音轨与时间轴' }] };
  frame = 30;
  expect(renderToStaticMarkup(<M2VComposition {...props} />)).toContain('共同音轨与时间轴');
  frame = 60;
  expect(renderToStaticMarkup(<M2VComposition {...props} />)).not.toContain('共同音轨与时间轴');
});
