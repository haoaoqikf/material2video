import type { PlayerRef } from '@remotion/player';
import { ensureFonts } from '@/fonts';
import { totalFrames } from '@/runtime/timeline';
import type { Storyboard } from '@/schema/storyboard';
import type { StoryboardV4 } from '@/schema/storyboardV4';
import { resolveStoryboardV4, type V4MediaTimeline } from '@/runtime/timelineV4';

/**
 * 渲染契约（version 3）。
 *
 * 这是画面实现与渲染/体检脚本之间**唯一**的接口。它由本页实现，实现者是
 * `@remotion/player`：验收与量测（K 系列、M 系列、组件契约探针）继续用
 * Playwright 驱动这个页面，因此既有约 90KB 已实测的判定逻辑不需要重写。
 *
 * v3 契约中的 `ready()` 保证 `Player` 与字体已经就绪
 * （除字体与首帧之外，还要保证 Player 已经挂载），因此版本号随语义变化递增
 * （当前为 3）。渲染入口按版本号拒绝旧页面，避免「等超时之后报一句看不懂的话」。
 */
export interface M2VContractBase {
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

export interface M2VContractV4 extends Omit<M2VContractBase, 'version'> {
  version: 4;
  world: () => { id: string; renderer: 'tree' | 'code'; objectIds: string[] };
  stage: () => { id: string; startFrame: number; endFrame: number };
  objectStates: () => Record<string, Record<string, unknown>>;
  camera: () => { kind: string; focus: string; x: number; y: number; scale: number; velocity: number };
  beats: () => { current: string | null; completed: string[]; plan: string[]; estimated: boolean };
}

export interface M2VContractV3 extends Omit<M2VContractBase, 'version'> { version: 3 }
export interface M2VContractV5 {
  version: 5; fps: number; width: number; height: number; durationInFrames: number;
  ready: () => Promise<void>; seekToFrame: (frame: number) => Promise<void>;
}
export type M2VContract = M2VContractV3 | M2VContractV4 | M2VContractV5;

declare global {
  interface Window {
    __M2V__?: M2VContract;
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
  const wrappers = Array.from(document.querySelectorAll<HTMLElement>('[data-m2v-code-scene]'));
  const errors: string[] = [];
  let pending = 0;
  for (const element of wrappers) {
    const state = element.dataset.m2vCodeReady;
    if (state === 'error') errors.push(element.dataset.m2vCodeError ?? '(未知错误)');
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

/** v4 tree 的字号适配与镜头几何必须在契约 ready 前完成。 */
async function waitForTreeLayout(): Promise<void> {
  const world = document.querySelector<HTMLElement>('[data-m2v-world][data-m2v-world-renderer="tree"]');
  if (!world) return;
  const start = Date.now();
  for (;;) {
    if (world.dataset.m2vLayoutError) {
      throw new Error(`场景树布局预检失败：${world.dataset.m2vLayoutError}`);
    }
    if (world.dataset.m2vLayoutReady === '1') return;
    if (Date.now() - start > SEEK_TIMEOUT_MS) {
      throw new Error(`场景树布局预检在 ${SEEK_TIMEOUT_MS}ms 内未完成`);
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

export interface CreateContractOptions {
  player: PlayerRef;
  storyboard: Storyboard | (StoryboardV4 & { mediaTimeline?: V4MediaTimeline });
}

export function createContract({ player, storyboard }: CreateContractOptions): M2VContract {
  const isV4 = storyboard.version === 4;
  const durationInFrames = isV4
    ? resolveStoryboardV4(storyboard as StoryboardV4, (storyboard as StoryboardV4 & { mediaTimeline?: V4MediaTimeline }).mediaTimeline).totalFrames
    : totalFrames(storyboard as Storyboard);
  const common = {
    fps: storyboard.fps, width: storyboard.width, height: storyboard.height, durationInFrames,
    async ready(): Promise<void> {
      await ensureFonts();
      await document.fonts.ready;
      await waitForCodeScenes();
      await waitForTreeLayout();
      const target = Math.min(Math.max(player.getCurrentFrame(), 0), durationInFrames - 1);
      await settleOnFrame(player, target);
      await document.fonts.ready;
    },
    async seekToFrame(frame: number): Promise<void> {
      if (!Number.isFinite(frame)) throw new Error(`seekToFrame 需要有限数值，收到 ${String(frame)}`);
      const clamped = Math.min(Math.max(Math.floor(frame), 0), durationInFrames - 1);
      await settleOnFrame(player, clamped);
      await waitForCodeScenes();
      await waitForTreeLayout();
      await document.fonts.ready;
    },
    currentFrame: () => player.getCurrentFrame(),
  };
  if (isV4) {
    const readWorld = () => {
      const element = document.querySelector<HTMLElement>('[data-m2v-world]');
      if (!element) throw new Error('v4 world 探针未挂载');
      const objects = JSON.parse(element.dataset.m2vWorldObjects ?? '[]') as Array<{ id: string }>;
      return { id: element.dataset.m2vWorldId ?? '', renderer: (element.dataset.m2vWorldRenderer ?? '') as 'tree' | 'code', objectIds: objects.map(({ id }) => id) };
    };
    const readStage = () => {
      const element = document.querySelector<HTMLElement>('[data-m2v-world]');
      if (!element) throw new Error('v4 stage 探针未挂载');
      return { id: element.dataset.m2vStageId ?? '', startFrame: Number(element.dataset.m2vStageStart), endFrame: Number(element.dataset.m2vStageEnd) };
    };
    const readNumber = (element: HTMLElement, key: string): number => {
      const value = Number(element.dataset[key]);
      if (!Number.isFinite(value)) throw new Error(`v4 探针 ${key} 无效`);
      return value;
    };
    const worldContract: M2VContractV4 = {
      ...common, version: 4,
      world: readWorld,
      stage: readStage,
      objectStates: () => {
        const element = document.querySelector<HTMLElement>('[data-m2v-world]');
        if (!element?.dataset.m2vWorldObjectStates) throw new Error('v4 object state 探针缺失');
        return JSON.parse(element.dataset.m2vWorldObjectStates) as Record<string, Record<string, unknown>>;
      },
      camera: () => {
        const element = document.querySelector<HTMLElement>('[data-m2v-camera="global"]');
        if (!element) throw new Error('v4 camera 探针缺失');
        return { kind: element.dataset.m2vCameraKind ?? '', focus: element.dataset.m2vCameraFocus ?? '',
          x: readNumber(element, 'm2vCameraX'), y: readNumber(element, 'm2vCameraY'),
          scale: readNumber(element, 'm2vCameraScale'), velocity: readNumber(element, 'm2vCameraVelocity') };
      },
      beats: () => {
        const element = document.querySelector<HTMLElement>('[data-m2v-world]');
        if (!element) throw new Error('v4 beat 探针缺失');
        return { current: element.dataset.m2vBeatCurrent || null,
          completed: (element.dataset.m2vBeatCompleted ?? '').split(',').filter(Boolean),
          plan: (element.dataset.m2vBeatPlan ?? '').split(',').filter(Boolean),
          estimated: element.dataset.m2vBeatEstimated === '1' };
      },
    };
    return worldContract;
  }

  return { ...common, version: 3 };
}
