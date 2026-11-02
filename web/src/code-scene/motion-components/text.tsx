/**
 * 文本排版：单行自动适配与 CJK 感知换行。
 *
 * 测量只在浏览器发生（录制页与契约页）；Node 下明确回退到调用方字号，
 * 不抛出、不猜一个"看起来差不多"的尺寸。中英文混排按字形单元断行，
 * 中文标点不落在行首，西文单词不拆开（过长时按字符硬断）。
 */
import {useEffect, useMemo, useState, type CSSProperties} from 'react';
import {fitText, measureText} from '@remotion/layout-utils';
import {ensureFonts} from '../../fonts';
import {clampProgress, type Easing} from '../primitives';
import {dataAttrs} from './internal';

export type TextFace = {
  fontFamily: string;
  fontSize: number;
  fontWeight?: number | string;
  letterSpacing?: string;
};

const CJK = /[⺀-⿿　-〿぀-ヿㇰ-ㇿ㐀-䶿一-鿿豈-﫿＀-￯]/u;
// CJK 字符范围：部首、CJK 标点、假名、注音、扩展 A、基本区、兼容区、全角区。
// 中文收尾标点：不能出现在行首，因此吸附到前一个字形单元。
const CLOSING = new Set(['，', '。', '、', '；', '：', '！', '？', '…', '—', '）', '》', '」', '』', '】', '〕', '〉', '”', '’']);

/** 测量依赖真实 DOM；纯 Node（单测、SSR）下返回 false。 */
export function canMeasureText(): boolean {
  return typeof document !== 'undefined' && typeof document.body !== 'undefined';
}

/**
 * 字体加载完成后再测量：录制页的 `ready()` 会等字体，但组件首次渲染可能更早。
 * 这里直接等待 `ensureFonts()`（与录制页同一个 Promise），字体就绪后重测；
 * 只等字体加载，不读时间源。
 */
function useFontsReady(): boolean {
  const [ready, setReady] = useState(() => typeof document === 'undefined');
  useEffect(() => {
    let active = true;
    ensureFonts().then(() => {
      if (active) setReady(true);
    }, () => {
      // 字体加载失败由录制页的 ready() 明确报错；组件保持回退字号，不吞掉全局失败。
    });
    return () => { active = false; };
  }, []);
  return ready;
}

export function measureTextWidth(text: string, face: TextFace, validateFont = true): number | null {
  if (!text || !canMeasureText()) return null;
  try {
    return measureText({
      text, fontFamily: face.fontFamily, fontSize: face.fontSize, fontWeight: face.fontWeight,
      letterSpacing: face.letterSpacing, validateFontIsLoaded: validateFont,
    }).width;
  } catch {
    return null;
  }
}

export type FitTextOptions = Omit<TextFace, 'fontSize'> & {
  text: string;
  withinWidth: number;
  validateFont?: boolean;
};

/** 单行字号适配；空文本或无法测量时返回 null，交给调用方回退。 */
export function fitFontSize({
  text, withinWidth, fontFamily, fontWeight, letterSpacing, validateFont = true,
}: FitTextOptions): number | null {
  if (!text.trim() || !Number.isFinite(withinWidth) || withinWidth <= 0 || !canMeasureText()) {
    return null;
  }
  try {
    const {fontSize} = fitText({
      text, withinWidth, fontFamily, fontWeight, letterSpacing,
      validateFontIsLoaded: validateFont,
    });
    return Number.isFinite(fontSize) && fontSize > 0 ? fontSize : null;
  } catch {
    return null;
  }
}

export type WrapOptions = {
  maxWidth: number;
  measure: (text: string) => number;
  maxLines?: number;
  ellipsis?: string;
};

/** 把一行拆成不可再分的字形单元；导出仅为测试与调试。 */
export function tokenizeForWrap(text: string): string[] {
  const tokens: string[] = [];
  let word = '';
  const flush = () => {
    if (word) {
      tokens.push(word);
      word = '';
    }
  };
  for (const char of Array.from(text)) {
    if (/\s/u.test(char)) {
      flush();
      tokens.push(' ');
      continue;
    }
    if (CJK.test(char)) {
      flush();
      const previous = tokens[tokens.length - 1];
      if (CLOSING.has(char) && previous && previous !== ' ') {
        tokens[tokens.length - 1] = previous + char;
      } else {
        tokens.push(char);
      }
      continue;
    }
    word += char;
  }
  flush();
  return tokens;
}

function ellipsize(line: string, {maxWidth, measure, ellipsis = '…'}: WrapOptions): string {
  let result = line;
  while (result && measure(result + ellipsis) > maxWidth) {
    result = Array.from(result).slice(0, -1).join('');
  }
  return result + ellipsis;
}

function wrapParagraph(paragraph: string, options: WrapOptions): string[] {
  const tokens = tokenizeForWrap(paragraph);
  const lines: string[] = [];
  let line = '';
  for (const token of tokens) {
    if (token === ' ') {
      if (!line) continue;
      if (options.measure((line + token).trimEnd()) > options.maxWidth) {
        lines.push(line.trimEnd());
        line = '';
      } else {
        line += token;
      }
      continue;
    }
    if (!line && options.measure(token) > options.maxWidth) {
      // 单个西文长词比整行还宽：按字符硬断，避免溢出到画外。
      let chunk = '';
      for (const char of Array.from(token)) {
        if (chunk && options.measure(chunk + char) > options.maxWidth) {
          lines.push(chunk);
          chunk = char;
        } else {
          chunk += char;
        }
      }
      line = chunk;
      continue;
    }
    if (line && options.measure(line + token) > options.maxWidth) {
      lines.push(line.trimEnd());
      line = token;
    } else {
      line += token;
    }
  }
  if (line.trim()) lines.push(line.trimEnd());
  return lines.length ? lines : [''];
}

/** 纯函数换行：测量函数由调用方注入，便于测试与复用。 */
export function wrapText(text: string, options: WrapOptions): string[] {
  const lines = text.split('\n').flatMap(paragraph => (
    paragraph ? wrapParagraph(paragraph, options) : ['']
  ));
  if (options.maxLines && lines.length > options.maxLines) {
    const kept = lines.slice(0, options.maxLines);
    kept[kept.length - 1] = ellipsize(kept[kept.length - 1], options);
    return kept;
  }
  return lines;
}

export type AutoFitTextProps = {
  text: string;
  withinWidth: number;
  fontFamily: string;
  fontWeight?: number | string;
  letterSpacing?: string;
  maxFontSize?: number;
  minFontSize?: number;
  lineHeight?: number;
  validateFont?: boolean;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** 单行标题按可用宽度求字号；无法测量时使用 maxFontSize，不静默缩成 0。 */
export function AutoFitText({
  text, withinWidth, fontFamily, fontWeight, letterSpacing, maxFontSize = 200,
  minFontSize = 1, lineHeight = 1.1, validateFont = true, className, style, role, state,
}: AutoFitTextProps) {
  const fontsReady = useFontsReady();
  const fontSize = useMemo(() => {
    if (!fontsReady) return maxFontSize;
    const fitted = fitFontSize({text, withinWidth, fontFamily, fontWeight, letterSpacing, validateFont});
    if (fitted === null) return maxFontSize;
    return Math.min(maxFontSize, Math.max(minFontSize, fitted));
  }, [fontsReady, text, withinWidth, fontFamily, fontWeight, letterSpacing, maxFontSize, minFontSize, validateFont]);
  return (
    <span
      {...dataAttrs(role, state)}
      className={className}
      style={{fontFamily, fontWeight, fontSize, letterSpacing, lineHeight,
        whiteSpace: 'nowrap', display: 'inline-block', ...style}}
    >
      {text}
    </span>
  );
}

export type TextBlockProps = {
  text: string;
  maxWidth: number;
  fontFamily: string;
  fontSize: number;
  fontWeight?: number | string;
  letterSpacing?: string;
  lineHeight?: number;
  maxLines?: number;
  ellipsis?: string;
  align?: 'left' | 'center' | 'right';
  /** 0–1 时按阅读顺序逐字显影；省略即全显。 */
  progress?: number;
  easing?: Easing;
  baseOpacity?: number;
  validateFont?: boolean;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** 多行文本块：CJK 感知换行，可选逐字显影；不读取任何时间源。 */
export function TextBlock({
  text, maxWidth, fontFamily, fontSize, fontWeight, letterSpacing, lineHeight = 1.4,
  maxLines, ellipsis = '…', align = 'left', progress, easing = (value: number) => value,
  baseOpacity = 0.12, validateFont = true, className, style, role, state,
}: TextBlockProps) {
  const fontsReady = useFontsReady();
  const measure = useMemo(() => {
    if (!fontsReady || !canMeasureText()) return null;
    return (value: string) => measureTextWidth(value, {fontFamily, fontSize, fontWeight, letterSpacing}, validateFont) ?? 0;
  }, [fontsReady, fontFamily, fontSize, fontWeight, letterSpacing, validateFont]);
  const lines = useMemo(() => {
    if (!measure) {
      const fallback = text.split('\n');
      return maxLines ? fallback.slice(0, maxLines) : fallback;
    }
    return wrapText(text, {maxWidth, measure, maxLines, ellipsis});
  }, [text, maxWidth, measure, maxLines, ellipsis]);
  const eased = progress === undefined ? 1 : easing(clampProgress(progress));
  const total = lines.reduce((count, line) => count + Array.from(line).length, 0);
  const visible = Math.floor(total * eased + 1e-9);
  const rendered: {chars: string[]; start: number}[] = [];
  let offset = 0;
  for (const line of lines) {
    const chars = Array.from(line);
    rendered.push({chars, start: offset});
    offset += chars.length;
  }
  return (
    <div
      {...dataAttrs(role, state)}
      className={className}
      style={{fontFamily, fontSize, fontWeight, letterSpacing, lineHeight, textAlign: align,
        ...style}}
    >
      {rendered.map(({chars, start}, index) => (
        <div key={index} style={{whiteSpace: 'pre', lineHeight: `${fontSize * lineHeight}px`}}>
          {chars.map((char, charIndex) => {
            const position = start + charIndex;
            const opacity = eased >= 1 || position < visible ? 1 : baseOpacity;
            return <span key={charIndex} style={{opacity}}>{char}</span>;
          })}
        </div>
      ))}
    </div>
  );
}
