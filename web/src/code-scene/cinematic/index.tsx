/**
 * 电影级共享套件：look、镜头、确定性后期与深空元件。
 *
 * 三条硬约束（与 `cinematic-video.md` 一致）：
 *
 * 1. 一切随时间变化的东西都由 `elapsedSeconds`/帧号驱动，不用挂钟、`Math.random`
 *    或 CSS 动画；粒子与噪声用「固定种子 + 帧号」的确定性哈希。
 * 2. 后期只作用于 canvas，不影响共享字幕 DOM 层。
 * 3. 元件按需引入；standard 作品不引用它们时画面与既有一致。
 *
 * 实现按职责拆到同目录的 `camera.tsx`（镜头、路径与焦点求值）、`postfx.tsx`
 * （look 参数与后期）与 `space.tsx`（深空元件）；本文件只做重导出，导出名
 * 与拆分前逐一相同，`sdk.tsx` 的 `export * from './cinematic'` 无需改动。
 */
export * from './camera';
export * from './postfx';
export * from './space';
