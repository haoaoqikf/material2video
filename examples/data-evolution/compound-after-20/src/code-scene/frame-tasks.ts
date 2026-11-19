/** 宿主拥有的异步绘制队列；只等待工作，不驱动作品时钟。 */
type Settlement = {ok: true} | {ok: false; error: unknown};

export class FrameTasks {
  private pending: Promise<Settlement>[] = [];
  private active = false;

  begin(): void {
    if (this.active) throw new Error('上一帧绘制尚未完成，不能重叠提交');
    this.active = true;
  }

  end(): void {this.active = false;}

  track(task: PromiseLike<unknown>): void {
    if (task === null || !['object', 'function'].includes(typeof task) || typeof task.then !== 'function') {
      throw new Error('waitForFrame 需要 PromiseLike 绘制任务');
    }
    // 登记即处理拒绝；宿主稍后等待时再传播，避免两者之间发生未处理拒绝。
    this.pending.push(Promise.resolve(task).then(
      () => ({ok: true} as const), error => ({ok: false, error} as const)));
  }

  async drain(): Promise<void> {
    let failed = false;
    let failure: unknown;
    while (this.pending.length) {
      const batch = this.pending.splice(0);
      for (const result of await Promise.all(batch)) {
        if (!result.ok && !failed) {failed = true; failure = result.error;}
      }
    }
    if (failed) throw failure instanceof Error ? failure : new Error(`异步绘制失败：${String(failure)}`);
  }

  async finish(paint: () => Promise<void>): Promise<void> {
    // 同步场景复用clock.flush已有屏障，不额外增加一次浏览器绘制等待。
    if (!this.pending.length) return;
    do {
      await this.drain();
      await paint();
    } while (this.pending.length);
  }
}
