import { staticFile } from 'remotion';
import fontManifest from '@/assets/fonts.json';

/**
 * 字体的注册。
 *
 * 四种做法里选了「运行时用 CSS Font Loading API 注册，URL 交给 `staticFile()`」：
 *
 * - **不走 CSS `url()`**：`url()` 在 Vite 里相对样式表解析、在 Remotion 的 webpack 里
 *   又是另一套规则，同一个字符串不可能在两处都对；
 * - **不用 `@remotion/fonts` 的 `loadFont()`**：它内部调用 `delayRender` / `continueRender`，
 *   那是渲染期的 API，在契约页（普通浏览器页面）里会直接报错；
 * - **不硬拼相对路径**：两条构建路径的静态根不一样。Remotion 把 `public/`
 *   拷到打包产物的 `public/` 子目录下（页面在根上），因此渲染时要 `/public/fonts/…`；
 *   契约页把 `public/` 的内容摊在自己的构建目录里，而页面又挂在别名前缀下，
 *   因此只有**相对**路径才对。判据是 Remotion 运行时注入的 `remotion_staticBase`：
 *   渲染器会设它，契约页没有它（见 `fontUrl`）。
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

/** 字体文件的 URL。两条构建路径的前缀不同，由 `remotion_staticBase` 决定走哪一支。 */
export function fontUrl(file: string): string {
  const relative = `fonts/${file}`;
  const staticBase = (globalThis as { remotion_staticBase?: unknown }).remotion_staticBase;
  if (typeof staticBase === 'string' && staticBase.length > 0) {
    // Remotion 渲染：`public/` 被拷到打包产物的 `public/` 子目录下，
    // 页面在打包产物根上，只有 staticBase 知道这个前缀。`staticFile()` 会给对。
    return staticFile(relative);
  }
  // 契约页：没有 staticBase，而且页面本身就挂在别名前缀下
  // （`/__m2v_web__/dist/contract/contract.html`），因此**相对**路径才是对的——
  // 绝对路径的 `/fonts/…` 会落到服务器根的 404 上。相对路径挂在哪个前缀下都对。
  return relative;
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
