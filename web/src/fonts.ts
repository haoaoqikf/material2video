import fontManifest from '@/assets/fonts.json';

/**
 * 字体的注册。
 *
 * 三种做法里选了「运行时用 CSS Font Loading API 注册，URL 用相对路径」：
 *
 * - **不走 CSS `url()`**：`url()` 在 Vite 里相对样式表解析、在 Remotion 的 webpack 里
 *   又是另一套规则，同一个字符串不可能在两处都对；
 * - **不用 `@remotion/fonts` 的 `loadFont()`**：它内部调用 `delayRender` / `continueRender`，
 *   那是渲染期的 API，在契约页（普通浏览器页面）里会直接报错；
 * - **相对 URL `fonts/<文件>`**：注入的 `<style>` 按文档基址解析，
 *   而契约页与 Remotion 的页面都在根路径下，因此同一个字符串两处都成立。
 *
 * `font-display: block` 是刻意的：逐帧截图会把「回退字体先渲染出来」的那一帧拍进成片。
 */
export interface RegisteredFont {
  family: string;
  file: string;
  weight: string;
  usage: string;
  license: string;
}

/** 画面实际注册的字体资产。清单是唯一真源（`src/assets/fonts.json`）。 */
export const FONTS: readonly RegisteredFont[] = fontManifest.files;

/** 字体文件的相对 URL。两个打包器都把 `public/` 放在站点根下。 */
export function fontUrl(file: string): string {
  return `fonts/${file}`;
}

let pending: Promise<void> | null = null;

/**
 * 注册全部字体，等它们真正可用后 resolve。重复调用返回同一个 Promise。
 *
 * 必须在**画第一帧之前**完成：`font-display: block` 在浏览器里是「先不画」，
 * 但如果调用方没等它，拿到的就是回退字体排出来的首帧。
 */
export function ensureFonts(): Promise<void> {
  pending ??= registerAll();
  return pending;
}

async function registerAll(): Promise<void> {
  if (typeof document === 'undefined' || typeof FontFace === 'undefined') {
    // 构建期或非浏览器环境：没有字体可注册，也不该报错
    return;
  }

  for (const font of FONTS) {
    const face = new FontFace(font.family, `url("${fontUrl(font.file)}") format("truetype")`, {
      weight: font.weight,
      style: 'normal',
      display: 'block',
    });
    await face.load();
    document.fonts.add(face);
  }

  await document.fonts.ready;
}
