import { cancelRender, continueRender, delayRender, registerRoot } from 'remotion';
import { ensureFonts } from './fonts';
import { RemotionRoot } from './Root';

/**
 * Remotion 的渲染入口。`remotion render src/index.ts A2V --props <分镜>` 从这里开始。
 *
 * 契约页走的是另一个入口（`contract.html` → `src/contract/main.tsx`），
 * 两者复用同一份 composition、同一份样式源码与同一份字体注册。
 *
 * 字体在这里用 `delayRender` 拦住：Remotion 不会在句柄未释放前取帧，
 * 因此不会出现「首帧用了回退字体」。契约页不能这么做（那是普通浏览器页面），
 * 它在 `ready()` 里等同一个 `ensureFonts()`。
 */
const fontHandle = delayRender('加载随仓库分发的字体');
ensureFonts()
  .then(() => continueRender(fontHandle))
  .catch((error: unknown) => cancelRender(error));

registerRoot(RemotionRoot);
