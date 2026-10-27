/**
 * 二维绘制层：原语确定性、量测代理同源、探针形状。
 *
 * 绘制原语本身不碰 DOM；这里用最小的 2D 上下文替身验证「同一帧两次求值相同」
 * 与「清单几何与实际绘制调用一致」。
 */
import {describe, expect, it} from 'vitest';
import {Painter, type Mark} from './frame';
import {reviewState} from './measure-proxy';

/** 最小 2D 上下文替身：记录调用，不产生像素。 */
function stubContext() {
  const calls: {name: string; args: unknown[]}[] = [];
  const record = (name: string) => (...args: unknown[]) => { calls.push({name, args}); };
  const ctx = {
    canvas: {width: 0, height: 0},
    globalAlpha: 1,
    globalCompositeOperation: 'source-over',
    filter: 'none',
    fillStyle: '#000',
    strokeStyle: '#000',
    lineWidth: 1,
    lineCap: 'round',
    lineJoin: 'round',
    shadowColor: 'transparent',
    shadowBlur: 0,
    textAlign: 'left',
    textBaseline: 'middle',
    font: '10px sans-serif',
    setTransform: record('setTransform'),
    save: record('save'),
    restore: record('restore'),
    translate: record('translate'),
    rotate: record('rotate'),
    scale: record('scale'),
    beginPath: record('beginPath'),
    closePath: record('closePath'),
    moveTo: record('moveTo'),
    lineTo: record('lineTo'),
    rect: record('rect'),
    roundRect: record('roundRect'),
    arc: record('arc'),
    ellipse: record('ellipse'),
    fill: record('fill'),
    stroke: record('stroke'),
    fillRect: record('fillRect'),
    fillText: record('fillText'),
    setLineDash: record('setLineDash'),
    clip: record('clip'),
    measureText: (text: string) => ({width: text.length * 10}),
    createLinearGradient: () => ({addColorStop: () => undefined}),
    createRadialGradient: () => ({addColorStop: () => undefined}),
  };
  return {ctx: ctx as unknown as CanvasRenderingContext2D, calls};
}

function drawOnce() {
  const {ctx, calls} = stubContext();
  const frame = new Painter(ctx, 1920, 1080, 1);
  frame.clear('#010104');
  frame.spark(600, 400, 6, '#F8D893', .9);
  frame.poly([[100, 100], [400, 300], [800, 200]], {color: '#64E3F6', width: 3, k: .5});
  frame.text('夜空为什么是黑的', 960, 838, {role: 'subject', state: 'revealed', size: 76});
  frame.group({alpha: .5, at: [10, 20]}, () => frame.circle(200, 200, 40, {color: '#FFF'}));
  return {frame, calls};
}

describe('二维绘制原语', () => {
  it('同一帧两次求值产生相同的清单与调用序列', () => {
    const first = drawOnce();
    const second = drawOnce();
    expect(first.frame.marks).toEqual(second.frame.marks);
    expect(first.calls.map(call => call.name)).toEqual(second.calls.map(call => call.name));
    expect(first.calls.length).toBeGreaterThan(10);
  });

  it('文字记入清单时带与绘制一致的字号与文本', () => {
    const {frame} = drawOnce();
    const subject = frame.marks.find(mark => mark.role === 'subject')!;
    expect(subject.text).toBe('夜空为什么是黑的');
    expect(subject.fontSize).toBe(76);
    expect(subject.state).toBe('revealed');
    expect(subject.width).toBe(80);
  });

  it('没有角色的绘制不进量测清单', () => {
    const {ctx} = stubContext();
    const frame = new Painter(ctx, 1920, 1080, 1);
    frame.circle(100, 100, 10, {color: '#FFF'});
    frame.text('装饰', 500, 500, {});
    expect(frame.marks).toEqual([]);
  });

  it('measurable 为 false 的文字不进清单', () => {
    const {ctx} = stubContext();
    const frame = new Painter(ctx, 1920, 1080, 1);
    frame.text('不量测', 100, 100, {role: 'noise', measurable: false});
    expect(frame.marks).toEqual([]);
  });

  it('折线生长进度只画前一段', () => {
    const {ctx, calls} = stubContext();
    const frame = new Painter(ctx, 1920, 1080, 1);
    frame.poly([[0, 0], [10, 10], [20, 20], [30, 30]], {color: '#FFF', k: .5});
    // k=0.5 时在第二段中间停下：起点 + 两段完整 + 一次插值。
    expect(calls.filter(call => call.name === 'lineTo')).toHaveLength(2);
  });

  it('along 返回插值坐标与切向', () => {
    const {ctx} = stubContext();
    const frame = new Painter(ctx, 1920, 1080, 1);
    const [x, y, angle] = frame.along([[0, 0], [100, 0]], .5);
    expect([x, y]).toEqual([50, 0]);
    expect(angle).toBeCloseTo(0);
  });

  it('拒绝非正像素密度', () => {
    const {ctx} = stubContext();
    expect(() => new Painter(ctx, 100, 100, 0)).toThrow(/像素密度/);
    expect(() => new Painter(ctx, 100, 100, -1)).toThrow(/像素密度/);
  });
});

describe('量测代理状态', () => {
  const mark = (role: string, state = ''): Mark => ({
    role, state, x: 0, y: 0, width: 10, height: 10,
  });

  it('按角色聚合成角色与数量', () => {
    const state = reviewState([mark('subject'), mark('subject'), mark('label', 'visible')]);
    expect(state).toEqual([
      {role: 'subject', count: 2},
      {role: 'label', count: 1, state: 'visible'},
    ]);
  });

  it('同一角色状态冲突时不猜一个', () => {
    const state = reviewState([mark('subject', 'a'), mark('subject', 'b')]);
    expect(state).toEqual([{role: 'subject', count: 2, state: ''}]);
  });

  it('空清单得到空列表', () => {
    expect(reviewState([])).toEqual([]);
  });
});
