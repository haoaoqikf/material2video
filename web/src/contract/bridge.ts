import type { PlayerRef } from '@remotion/player';
import { ensureFonts } from '@/fonts';
import { totalFrames } from '@/runtime/timeline';
import type { Storyboard } from '@/schema/storyboard';

/**
 * 渲染契约（version 3）。
 *
 * 这是画面实现与渲染/体检脚本之间**唯一**的接口。它由本页实现，实现者是
 * `@remotion/player`：验收与量测（K 系列、M 系列、组件契约探针）继续用
 * Playwright 驱动这个页面，因此既有约 90KB 已实测的判定逻辑不需要重写。
 *
 * v3 契约中的 `ready()` 保证 `Player` 与字体已经就绪
 * （除字体与首帧之外，还要保证 Player 已经挂载），因此版本号从 1 升到 2。
 * 渲染入口按版本号拒绝旧页面，避免「等超时之后报一句看不懂的话」。
 */
export interface A2VContractV3 {
  version: 3;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  ready: () => Promise<void>;
  seekToFrame: (frame: number) => Promise<void>;
  /** 诊断用：当前实际落在哪一帧。不属于契约要求，渲染脚本不依赖它。 */
  currentFrame: () => number;
}

declare global {
  interface Window {
    __A2V__?: A2VContractV3;
  }
}

/** 单次 seek 的等待上限。超时报错比静默截图更有用。 */
const SEEK_TIMEOUT_MS = 10_000;

/** 代码场景首批本地资源（字体之外：图片等）的就绪等待上限。 */
const CODE_READY_TIMEOUT_MS = 10_000;

/**
 * 收集代码场景包装器的就绪状态。
 *
 * `0` 表示还没完成首次提交与首批资源加载；`error` 表示本地资源加载失败
 * ——那是硬失败，必须显式报错，不能把未完成画面截成空白帧。
 */
function codeSceneState(): { pending: number; errors: string[] } {
  const wrappers = Array.from(document.querySelectorAll<HTMLElement>('[data-a2v-code-scene]'));
  const errors: string[] = [];
  let pending = 0;
  for (const element of wrappers) {
    const state = element.dataset.a2vCodeReady;
    if (state === 'error') errors.push(element.dataset.a2vCodeError ?? '(未知错误)');
    else if (state !== '1') pending += 1;
  }
  return { pending, errors };
}

/**
 * 等待全部代码场景就绪。
 *
 * 清单里的场景在首帧全部挂载（非当前幕只是隐藏），因此就绪是**一次性**
 * 状态：等所有包装器翻位即可，不需要按幕区分。
 */
async function waitForCodeScenes(): Promise<void> {
  const start = Date.now();
  for (;;) {
    const { pending, errors } = codeSceneState();
    if (errors.length > 0) {
      throw new Error(`代码场景本地资源加载失败：${errors.join('；')}`);
    }
    if (pending === 0) return;
    if (Date.now() - start > CODE_READY_TIMEOUT_MS) {
      throw new Error(
        `代码场景未就绪：${pending} 个场景在 ${CODE_READY_TIMEOUT_MS}ms 内没有完成首批资源加载`,
      );
    }
    await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));
  }
}

/** 等两次 rAF：第一次进入下一帧，第二次确保那一帧已经画出来。 */
function nextPaint(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
}

/**
 * 把画面定位到某一帧并等它真的落定。
 *
 * 两种完成信号取先到者：Player 的 `seeked` 事件，或轮询到 `getCurrentFrame()`
 * 等于目标帧。**两者都要**——当目标帧与当前帧相同时 Player 不发 `seeked`，
 * 只等事件会挂住；只轮询则在目标帧与当前帧不同、而 Player 需要跨帧调度时会忙等。
 */
async function settleOnFrame(player: PlayerRef, frame: number): Promise<void> {
  player.pause();

  if (player.getCurrentFrame() === frame) {
    await nextPaint();
    return;
  }

  await new Promise<void>((resolve, reject) => {
    let settled = false;

    const cleanup = (): void => {
      window.clearTimeout(timer);
      player.removeEventListener('seeked', onSeeked);
    };

    const finish = (): void => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      resolve();
    };

    const fail = (error: Error): void => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      reject(error);
    };

    const onSeeked = (event: { detail: { frame: number } }): void => {
      if (event.detail.frame === frame) {
        finish();
      }
    };

    const poll = (): void => {
      if (settled) {
        return;
      }
      if (player.getCurrentFrame() === frame) {
        finish();
        return;
      }
      requestAnimationFrame(poll);
    };

    const timer = window.setTimeout(() => {
      fail(
        new Error(
          `seekToFrame(${frame}) 超时：Player 在 ${SEEK_TIMEOUT_MS}ms 内没有落到该帧` +
            `（当前为第 ${player.getCurrentFrame()} 帧）`,
        ),
      );
    }, SEEK_TIMEOUT_MS);

    player.addEventListener('seeked', onSeeked);
    player.seekTo(frame);
    requestAnimationFrame(poll);
  });

  await nextPaint();
}

export interface CreateContractOptions {
  player: PlayerRef;
  storyboard: Storyboard;
}

export function createContract({ player, storyboard }: CreateContractOptions): A2VContractV3 {
  const durationInFrames = totalFrames(storyboard);

  return {
    version: 3,
    fps: storyboard.fps,
    width: storyboard.width,
    height: storyboard.height,
    durationInFrames,

    async ready(): Promise<void> {
      // 字体先行：否则首帧会用回退字体排版，且首帧与后续帧字宽不一致。
      // 这一步与渲染入口的 `delayRender` 等的是**同一个** Promise。
      await ensureFonts();
      await document.fonts.ready;
      // 代码场景与首批本地资源：未就绪时明确失败，不截空白帧
      await waitForCodeScenes();
      const target = Math.min(Math.max(player.getCurrentFrame(), 0), durationInFrames - 1);
      await settleOnFrame(player, target);
      await document.fonts.ready;
    },

    async seekToFrame(frame: number): Promise<void> {
      if (!Number.isFinite(frame)) {
        throw new Error(`seekToFrame 需要有限数值，收到 ${String(frame)}`);
      }
      const clamped = Math.min(Math.max(Math.floor(frame), 0), durationInFrames - 1);
      await settleOnFrame(player, clamped);
      // 跨幕切换可能首次挂载新的代码场景：等它就绪再返回
      await waitForCodeScenes();
      // 字体可能在首次取档时被替换，落到帧之后再确认一次
      await document.fonts.ready;
    },

    currentFrame: () => player.getCurrentFrame(),
  };
}
