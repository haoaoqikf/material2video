/** KaTeX 的排版与字体是离线资源；调用方须 await ensureMathReady() 后 ready()。 */
import {useMemo, type CSSProperties} from 'react';
import katex from 'katex';
import css from 'katex/dist/katex.min.css?raw';
import {mathFonts} from './math-fonts';
import {dataAttrs} from './motion-components/internal';

let pending: Promise<void> | undefined;

export function ensureMathReady(): Promise<void> {
  if (typeof document === 'undefined') return Promise.resolve();
  pending ??= (async () => {
    const style = document.createElement('style');
    style.dataset.m2vMath = 'katex-0.19.1';
    // 排版规则复用原包；移除其 font-face，避免 woff/ttf 或在线回退路径。
    style.textContent = css.replace(/@font-face\s*\{[^}]*\}/g, '');
    document.head.append(style);
    await Promise.all(mathFonts.map(async font => {
      const face = new FontFace(font.family, `url("${font.url}") format("woff2")`,
        {weight: font.weight, style: font.style, display: 'block'});
      await face.load();
      document.fonts.add(face);
    }));
    await document.fonts.ready;
  })();
  return pending;
}

export function MathFormula({tex, display = false, fontSize = 64, color = 'inherit', style, role, state}: {
  tex: string; display?: boolean; fontSize?: number; color?: string; style?: CSSProperties; role?: string; state?: string;
}) {
  const html = useMemo(() => katex.renderToString(tex, {
    displayMode: display, throwOnError: true, trust: false, strict: 'error', output: 'htmlAndMathml',
    maxExpand: 1000, maxSize: 20,
  }), [tex, display]);
  return <span {...dataAttrs(role, state)} style={{fontSize, color, ...style}}
    dangerouslySetInnerHTML={{__html: html}}/>;
}
