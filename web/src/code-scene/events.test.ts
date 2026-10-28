import {describe, expect, it} from 'vitest';
import {createSceneEvents} from './events';

describe('幕内事件', () => {
  it('时间修改一次，动作、计数和强调共同移动，乱序及子帧求值一致', () => {
    const state = (contact: number, frame: number) => {
      const events = createSceneEvents({contact});
      return {motion: events.progress('contact', frame, 18, -18),
        count: Number(frame >= events.frame('contact')),
        emphasis: 1 - events.progress('contact', frame, 6)};
    };
    for (const frame of [90, 72, 89.5, 100, 90, 71, 96]) {
      expect(state(105, frame + 15)).toEqual(state(90, frame));
    }
    expect(state(90, 89.5).count).toBe(0);
    expect(state(90, 90)).toEqual({motion: 1, count: 1, emphasis: 1});
  });
  it('快照输入，拒绝缺失、继承属性和非法参数', () => {
    const source = {contact: 90};
    const events = createSceneEvents(source);
    source.contact = 10;
    expect(events.frame('contact')).toBe(90);
    expect(() => events.frame('toString')).toThrow('未声明');
    expect(() => events.frame('missing')).toThrow('未声明');
    for (const value of [-1, NaN, Infinity, 1.2]) {
      expect(() => createSceneEvents({contact: value})).toThrow('非法');
    }
    for (const duration of [0, -1, Infinity, NaN]) {
      expect(() => events.progress('contact', 90, duration)).toThrow('正持续帧数');
    }
  });
});
