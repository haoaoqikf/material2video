/** 无跨帧状态的事件查询；可按任意顺序求值，兼容子帧采集。 */
export function createSceneEvents(eventFrames: Readonly<Record<string, number>> = {}) {
  // 复制一次，避免调用者修改原表让同帧结果变化。
  const frames = {...eventFrames};
  for (const [id, value] of Object.entries(frames)) {
    if (!id.trim() || !Number.isSafeInteger(value) || value < 0) {
      throw new Error(`非法场景事件：${id}`);
    }
  }
  function frame(id: string): number {
    if (!Object.hasOwn(frames, id)) throw new Error(`未声明的场景事件：${id}`);
    return frames[id];
  }
  function progress(id: string, currentFrame: number, durationFrames: number, offsetFrames = 0): number {
    if (![currentFrame, durationFrames, offsetFrames].every(Number.isFinite) || durationFrames <= 0) {
      throw new Error('事件进度需要有限帧数和正持续帧数');
    }
    return Math.max(0, Math.min(1, (currentFrame - frame(id) - offsetFrames) / durationFrames));
  }
  return {frame, progress};
}
