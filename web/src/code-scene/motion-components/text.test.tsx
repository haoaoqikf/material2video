import {renderToStaticMarkup} from 'react-dom/server';
import {describe, expect, it} from 'vitest';
import {AutoFitText, TextBlock, tokenizeForWrap, wrapText} from './index';

const measure = (text: string) => Array.from(text).length * 10;

describe('text layout', () => {
  it('keeps CJK closing punctuation attached to the previous cell', () => {
    expect(tokenizeForWrap('中文，测试')).toEqual(['中', '文，', '测', '试']);
    expect(tokenizeForWrap('hello world')).toEqual(['hello', ' ', 'world']);
  });

  it('wraps Latin words at spaces and CJK between characters', () => {
    expect(wrapText('abcd efgh', {maxWidth: 50, measure})).toEqual(['abcd', 'efgh']);
    expect(wrapText('中文测试', {maxWidth: 20, measure})).toEqual(['中文', '测试']);
  });

  it('hard-breaks an overlong word and truncates to the requested line count', () => {
    expect(wrapText('abcdef', {maxWidth: 20, measure})).toEqual(['ab', 'cd', 'ef']);
    expect(wrapText('abcdef', {maxWidth: 20, measure, maxLines: 1})).toEqual(['a…']);
  });

  it('falls back to maxFontSize when no DOM measurement is available', () => {
    expect(renderToStaticMarkup(
      <AutoFitText text="标题" withinWidth={400} fontFamily="M2V Sans" maxFontSize={64}/>,
    )).toContain('font-size:64px');
  });

  it('reveals TextBlock characters by progress and works without DOM', () => {
    const shown = renderToStaticMarkup(<TextBlock text={'ab\ncd'} maxWidth={200} fontFamily="M2V Sans"
      fontSize={32} progress={1}/>);
    const hidden = renderToStaticMarkup(<TextBlock text={'ab\ncd'} maxWidth={200} fontFamily="M2V Sans"
      fontSize={32} progress={0}/>);
    expect(shown).toContain('>a</span>');
    expect(shown).toContain('>c</span>');
    expect(hidden).toContain('opacity:0.12');
    expect(hidden.match(/opacity:0.12/g)?.length).toBe(4);
  });
});
