import {describe, expect, it, vi} from 'vitest';
import {FrameTasks} from './frame-tasks';

const deferred = () => {
  let resolve!: () => void;
  const promise = new Promise<void>(done => {resolve = done;});
  return {promise, resolve};
};

describe('异步帧工作边界', () => {
  it('等待所有任务及其链式新增工作，再执行绘制屏障', async () => {
    const queue = new FrameTasks(), first = deferred(), second = deferred();
    const paint = vi.fn(async () => {});
    queue.track(first.promise.then(() => {queue.track(second.promise);}));
    let finished = false;
    const result = queue.finish(paint).then(() => {finished = true;});
    first.resolve();
    await Promise.resolve(); await Promise.resolve();
    expect(finished).toBe(false); expect(paint).not.toHaveBeenCalled();
    second.resolve(); await result;
    expect(paint).toHaveBeenCalledOnce();
  });

  it('提前吸收拒绝，等其余工作收敛后传播原错误，后续提交可恢复', async () => {
    const queue = new FrameTasks(), remaining = deferred(), failure = new Error('gpu failed');
    queue.begin(); queue.track(Promise.reject(failure)); queue.track(remaining.promise);
    await Promise.resolve();
    const result = queue.finish(async () => {});
    const observed = result.catch(error => error);
    remaining.resolve(); expect(await observed).toBe(failure);
    queue.end(); queue.begin(); queue.track(Promise.resolve());
    await queue.finish(async () => {}); queue.end();
  });

  it('拒绝非法任务，接受标准thenable', async () => {
    const queue = new FrameTasks();
    for (const invalid of [null, undefined, 1, {}, {then: true}]) {
      expect(() => queue.track(invalid as unknown as PromiseLike<unknown>)).toThrow('PromiseLike');
    }
    queue.track({then: resolve => resolve?.(undefined)} as PromiseLike<unknown>);
    await queue.finish(async () => {});
  });

  it('拒绝重叠提交而不清掉已有工作', async () => {
    const queue = new FrameTasks(), task = deferred();
    queue.begin(); queue.track(task.promise);
    expect(() => queue.begin()).toThrow('不能重叠');
    task.resolve(); await queue.finish(async () => {}); queue.end();
    expect(() => queue.begin()).not.toThrow(); queue.end();
  });

  it('合成屏障中新增工作仍要等待，同步场景不增加屏障', async () => {
    const queue = new FrameTasks(), extra = deferred();
    const paint = vi.fn(async () => {
      if (paint.mock.calls.length === 1) {queue.track(extra.promise); extra.resolve();}
    });
    await queue.finish(paint); expect(paint).not.toHaveBeenCalled();
    queue.track(Promise.resolve()); await queue.finish(paint);
    expect(paint).toHaveBeenCalledTimes(2);
  });
});
