import type { PlayerRef } from '@remotion/player';

/**
 * 渲染契约（version 5）。
 *
 * 这是画面实现与量测脚本之间**唯一**的接口：契约页实现它，实现者是
 * `@remotion/player`；布局量测用 Playwright 驱动这个页面。
 *
 * `ready()` 保证字体、首帧与全部本地图片已经就绪。渲染与量测都按版本号
 * 拒绝旧页面，避免「等超时之后报一句看不懂的话」。
 */
export interface M2VContractV5 {
  version: 5;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  ready: () => Promise<void>;
  seekToFrame: (frame: number) => Promise<void>;
  /** 只读诊断读数，不参与求帧完成的判定。 */
  currentFrame: () => number;
}

declare global {
  interface Window {
    __M2V__?: M2VContractV5;
  }
}

/** 单次 seek 的等待上限。超时报错比静默截图更有用。 */
const SEEK_TIMEOUT_MS = 10_000;

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
export async function settleOnFrame(player: PlayerRef, frame: number): Promise<void> {
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
