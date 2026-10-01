import { describe, expect, it } from 'vitest';
import { countArticleCharacters, extractArticleBody, standardLengthResult } from './articleText';

describe('standard article text count', () => {
  it('applies inclusive 130–170 code point boundaries', () => {
    expect(standardLengthResult('甲'.repeat(129))).toEqual({ count: 129, pass: false });
    expect(standardLengthResult('甲'.repeat(130))).toEqual({ count: 130, pass: true });
    expect(standardLengthResult('甲'.repeat(170))).toEqual({ count: 170, pass: true });
    expect(standardLengthResult('甲'.repeat(171))).toEqual({ count: 171, pass: false });
  });

  it('excludes Unicode punctuation and White_Space while counting letters and digits individually', () => {
    expect(countArticleCharacters('甲，A1\u00a0乙！\u3000')).toBe(4);
    expect(countArticleCharacters("'‘’\"“”…！？—、。" )).toBe(0);
    expect(countArticleCharacters('é𝟙')).toBe(2);
    expect(countArticleCharacters('甲\u0085乙\u2007丙')).toBe(3);
  });

  it('excludes only a first non-empty Markdown H1', () => {
    expect(extractArticleBody('\n# 标题\n正文')).toBe('正文');
    expect(extractArticleBody('第一行是正文\n第二行')).toBe('第一行是正文\n第二行');
    expect(countArticleCharacters(extractArticleBody(`# 标题\n${'正文'.repeat(65)}`))).toBe(130);
  });
});
