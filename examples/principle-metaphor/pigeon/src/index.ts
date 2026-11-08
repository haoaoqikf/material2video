import { cancelRender, continueRender, delayRender, registerRoot } from 'remotion';
import { ensureFonts } from './fonts';
import { installOfflineGuard } from './runtime/offline-guard';
import { RemotionRoot } from './Root';

// 运行期隔离：Remotion 的 Chromium 同样不许发出非本地请求；
// 静态闸门管源码，这一层管运行期（拼接 URL 之类绕过静态检查的写法）。
installOfflineGuard();

/**
 * Remotion 的渲染入口。`remotion render src/index.ts M2V --props <分镜>` 从这里开始。
 *
 * 契约页走的是另一个入口（`contract.html` → `src/scene-film/contract-main.tsx`），
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
