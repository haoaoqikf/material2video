/**
 * 画面运行时里那些**纯函数**的契约。
 *
 * 这些函数是旧组件库手法的等价物，因此它们的取值会被逐像素对照检验：
 * 拼接格式差一个空格、强调词少包一层 `<span class="key">`、
 * 逐字揭示的节奏差一帧，都会在成片里变成可见差异。
 *
 * 这里不重复实现一遍当作「对照」——那样等于自己给自己判卷。
 * 断言的是**行为性质**（只替换第一处、转义、节奏单调、换行不占位），
 * 取值本身由 `tests/test_react_figure_parity.py` 的抽帧对照守。
 */

import { describe, expect, it } from 'vitest';

import {
  EASE,
  emphasisHtml,
  emphasisProps,
  emphasize,
  escapeHtml,
  pad,
  plainText,
  revealUnits,
  ROLL_MIN,
  splitEmphasis,
  svgOpacity,
  svgTransform,
} from '@/runtime/figures';

describe('转义与纯文本', () => {
  it('转义只会破坏标记的三个字符', () => {
    expect(escapeHtml('<b>&</b>')).toBe('&lt;b&gt;&amp;&lt;/b&gt;');
    expect(escapeHtml(null)).toBe('');
    expect(escapeHtml(0)).toBe('0');
  });

  it('空值给空串，不给 undefined', () => {
    expect(plainText(null)).toBe('');
    expect(plainText(undefined)).toBe('');
    expect(plainText(0)).toBe('0');
    expect(plainText('甲')).toBe('甲');
  });
});

describe('强调短语', () => {
  it('包成 .key，且只替换第一处', () => {
    const html = emphasize('自由与自由', ['自由']);
    expect(html).toBe(
      '<span class="key">自由</span>与自由',
    );
    expect(html.match(/class="key"/g)).toHaveLength(1);
  });

  it('可以带上按帧画出的下划线', () => {
    expect(emphasize('害怕上场', ['害怕'], true)).toContain(
      '<span class="key">害怕<span class="key-underline"></span></span>',
    );
  });

  it('短语里的标记字符会被转义，不会破坏结构', () => {
    expect(emphasize('a<b>c', ['<b>'])).toBe('a<span class="key">&lt;b&gt;</span>c');
  });

  it('找不到的短语原样留下', () => {
    expect(emphasize('甲', ['乙'])).toBe('甲');
    expect(emphasize('甲')).toBe('甲');
  });

  it('后一个短语可能因为前一个短语插入的标记而匹配不到', () => {
    /*
     * 这不是缺陷，是**旧实现的既有行为**：`emphasize` 是在已经拼好的串上
     * 依次做 replace，先插入的 `<span class="key">` 会把后面的字隔开。
     * 换成节点拼装就会悄悄改掉强调词的数量与位置，那是画面变化。
     */
    const html = emphasize('自由', ['自', '自由']);
    expect(html).toBe('<span class="key">自</span>由');
  });

  it('渲染属性与 innerHTML 一致', () => {
    expect(emphasisProps('<i>x</i>')).toEqual({
      dangerouslySetInnerHTML: { __html: '<i>x</i>' },
    });
  });
});

describe('强调串的行内值', () => {
  it('不给进度就一个行内样式都不写', () => {
    expect(emphasisHtml('要自由', ['自由'], { underline: true })).toBe(
      '要<span class="key">自由<span class="key-underline"></span></span>',
    );
  });

  it('预设下只报告光晕档位，不写行内 text-shadow', () => {
    const html = emphasisHtml('要自由', ['自由'], {
      progress: 0.5,
      preset: true,
      underline: true,
    });
    expect(html).toContain('--a2v-emphasis-glow: 0.5000;');
    expect(html).not.toContain('text-shadow');
    expect(html).toContain('transform: scaleX(0.5000);');
  });

  it('非预设下写行内 text-shadow，模糊与浓度按进度插值', () => {
    const html = emphasisHtml('要自由', ['自由'], { progress: 0.5 });
    expect(html).toContain('text-shadow: 0 0 13.0px rgba(var(--a2v-accent-rgb), 0.110);');
    expect(html).not.toContain('--a2v-emphasis-glow');
  });

  it('行内样式只落在第一个强调片段上', () => {
    // 旧实现用 `querySelector('.key')`，后面那些强调片段没有行内值
    const html = emphasisHtml('重要的事', ['重要', '事'], { progress: 1 });
    expect(html.match(/style=/g)).toHaveLength(1);
    expect(html.startsWith('<span class="key" style=')).toBe(true);
  });
});

describe('文本切分', () => {
  it('只认第一处命中的短语', () => {
    expect(splitEmphasis('先做重要的事', ['重要', '事'])).toEqual([
      { text: '先做', key: false },
      { text: '重要', key: true },
      { text: '的事', key: false },
    ]);
  });

  it('命中的短语在开头或结尾时不产生空片段', () => {
    expect(splitEmphasis('自由', ['自由'])).toEqual([{ text: '自由', key: true }]);
    expect(splitEmphasis('要自由', ['自由'])).toEqual([
      { text: '要', key: false },
      { text: '自由', key: true },
    ]);
  });

  it('空短语与找不到的短语都退回普通片段', () => {
    expect(splitEmphasis('甲', ['', '乙'])).toEqual([{ text: '甲', key: false }]);
    expect(splitEmphasis('甲', undefined)).toEqual([{ text: '甲', key: false }]);
  });
});

describe('逐字揭示', () => {
  const text = '害怕\n上场';
  const options = { startFrame: 0, staggerFrames: 2 };

  it('换行占位但不消耗节奏', () => {
    const units = revealUnits(text, undefined, { ...options, frame: 0 });
    const chars = units[0]!.chars;
    const breaks = chars.filter((char) => char.isBreak);
    expect(breaks).toHaveLength(1);
    expect(breaks[0]!.char).toBe('\n');
    expect(breaks[0]!.opacity).toBe(1);
    // 4 个非换行字符：第 i 个在第 2i 帧开始点亮
    expect(chars.filter((char) => !char.isBreak)).toHaveLength(4);
  });

  it('不透明度随帧号单调不减', () => {
    const opacities = (frame: number) =>
      revealUnits(text, undefined, { ...options, frame })[0]!.chars
        .filter((char) => !char.isBreak)
        .map((char) => char.opacity);
    for (let frame = 1; frame <= 12; frame += 1) {
      const previous = opacities(frame - 1);
      const current = opacities(frame);
      current.forEach((value, index) => {
        expect(value).toBeGreaterThanOrEqual(previous[index]!);
      });
    }
    expect(opacities(12)).toEqual([1, 1, 1, 1]);
    expect(opacities(0)).toEqual([0, 0, 0, 0]);
  });

  it('强调片段整体晚 6 帧', () => {
    const units = revealUnits('要自由', ['自由'], { ...options, frame: 2 });
    expect(units.map((unit) => unit.key)).toEqual([false, true]);
    const plain = units[0]!.chars[0]!;
    const key = units[1]!.chars[0]!;
    // 正文第一个字在第 0 帧开始，强调第一个字在第 6 帧开始
    expect(plain.opacity).toBe(1);
    expect(key.opacity).toBe(0);
  });

  it('空文本给一个空片段，不抛错', () => {
    // 旧实现同样会留下一个空的普通片段容器（`splitEmphasis('')` 的结果），
    // 里面没有单字节点——画面因此是空的，而不是崩掉
    const units = revealUnits('', undefined, { ...options, frame: 5 });
    expect(units).toEqual([{ key: false, chars: [] }]);
  });
});

describe('SVG 属性串', () => {
  it('与旧实现同样的格式：两位小数与四位小数', () => {
    expect(svgTransform(1.5, -2.25)).toBe('translate(1.50 -2.25)');
    expect(svgTransform(1, 2, 0.5, 0.7071)).toBe(
      'translate(1.00 2.00) rotate(0.5000) scale(0.7071)',
    );
    // 旋转为 0 时不写 rotate，缩放为 undefined 时不写 scale——与旧实现一致
    expect(svgTransform(0, 0, 0, undefined)).toBe('translate(0.00 0.00)');
  });

  it('不透明度钳到 0..1', () => {
    expect(svgOpacity(-1)).toBe('0');
    expect(svgOpacity(2)).toBe('1');
    expect(svgOpacity(0.333)).toBe('0.333');
  });
});

describe('常量', () => {
  it('四条缓动曲线与旧组件库同一口径', () => {
    expect(EASE).toEqual({
      out: 'outQuint',
      soft: 'outCubic',
      symmetric: 'inOutCubic',
      linear: 'linear',
    });
  });

  it('数值滚动的最少步数是 10', () => {
    expect(ROLL_MIN).toBe(10);
  });

  it('幕号补零到两位', () => {
    expect(pad(1)).toBe('01');
    expect(pad(9)).toBe('09');
    expect(pad(10)).toBe('10');
    expect(pad(120)).toBe('120');
  });
});
