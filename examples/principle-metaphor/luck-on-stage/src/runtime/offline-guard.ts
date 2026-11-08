/**
 * 运行期隔离：阻断非本地网络请求（Remotion Chromium 路径的边界层）。
 *
 * 静态闸门在源码层面拒绝网络 API；这层兜底运行期：即使代码用拼接等
 * 方式绕过静态检查，对非本地地址的 fetch / XHR / WebSocket 也会被拒绝，
 * 且每次阻断都会记录到 `window.__M2V_VIOLATIONS__`，契约页路径把它
 * 读出来并入体检失败。允许的地址只有本机（localhost / 127.0.0.1）、
 * 相对路径与 data:/blob: 这类不入网协议——预览、评审与渲染全部离线可跑。
 */

/** 判断 URL 是否指向本地资源；判定标准与契约页服务器的挂载一致。 */
export function isLocalUrl(rawUrl: string, origin?: string): boolean {
  // 无 window 的环境（单测、SSR 预算）以 localhost 为基准：相对路径仍可解析
  const base = origin ?? (typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
  if (rawUrl.startsWith('data:') || rawUrl.startsWith('blob:') || rawUrl.startsWith('about:')) {
    return true;
  }
  try {
    const url = new URL(rawUrl, base);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      return false;
    }
    const host = url.hostname;
    return host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]';
  } catch {
    return false;
  }
}

type Recorder = (message: string) => void;

let installed = false;

/**
 * 安装守卫。幂等：重复调用不会二次包装原生 API。
 * 返回 recorder 供测试注入；生产路径记录到 `window.__M2V_VIOLATIONS__`。
 */
export function installOfflineGuard(recorder?: Recorder): void {
  if (installed) return;
  installed = true;
  const record =
    recorder ??
    ((message: string) => {
      const bag = (window as unknown as { __M2V_VIOLATIONS__?: string[] });
      bag.__M2V_VIOLATIONS__ = bag.__M2V_VIOLATIONS__ ?? [];
      bag.__M2V_VIOLATIONS__.push(message);
    });

  const block = (kind: string, url: string): Error =>
    new Error(`M2V 运行期隔离：${kind} 非本地请求被阻断（${url}）。画面必须离线可渲染。`);

  const originalFetch = window.fetch.bind(window);
  window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (!isLocalUrl(url)) {
      const error = block('fetch', url);
      record(error.message);
      return Promise.reject(error);
    }
    return originalFetch(input, init);
  }) as typeof window.fetch;

  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function open(
    this: XMLHttpRequest,
    method: string,
    url: string | URL,
    ...rest: unknown[]
  ): void {
    if (!isLocalUrl(String(url))) {
      const error = block('XMLHttpRequest', String(url));
      record(error.message);
      throw error;
    }
    (originalOpen as (...args: unknown[]) => void).apply(this, [method, url, ...rest]);
  } as typeof XMLHttpRequest.prototype.open;

  const OriginalWebSocket = window.WebSocket;
  if (OriginalWebSocket) {
    const GuardedWebSocket = function WebSocket_(this: unknown, url: string | URL, ...rest: unknown[]) {
      if (!isLocalUrl(String(url))) {
        const error = block('WebSocket', String(url));
        record(error.message);
        throw error;
      }
      return new (OriginalWebSocket as unknown as new (u: string, ...r: unknown[]) => WebSocket)(
        String(url),
        ...rest,
      );
    };
    window.WebSocket = GuardedWebSocket as unknown as typeof window.WebSocket;
  }
}
