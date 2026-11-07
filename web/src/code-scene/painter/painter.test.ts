/**
 * 二维绘制层：确定性调用、合成层序与离屏缓冲复用。
 *
 * 绘制原语本身不碰 DOM；这里用最小的 2D 上下文替身验证「同一帧两次求值相同」
 * 与实际绘制结果的合成顺序。
 */
import {describe, expect, it} from 'vitest';
import {Painter} from './frame';

/** 最小 2D 上下文替身：记录调用，不产生像素。 */
function stubContext() {
  const calls: {name: string; args: unknown[]}[] = [];
  const record = (name: string) => (...args: unknown[]) => { calls.push({name, args}); };
  let matrix = {a: 1, b: 0, c: 0, d: 1, e: 0, f: 0};
  const stack: {matrix: typeof matrix; alpha: number}[] = [];
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
    getTransform: () => ({...matrix}),
    setTransform: (a: number, b: number, c: number, d: number, e: number, f: number) => { matrix = {a,b,c,d,e,f}; },
    save: () => { stack.push({matrix: {...matrix}, alpha: ctx.globalAlpha}); },
    restore: () => { const state = stack.pop()!; matrix = state.matrix; ctx.globalAlpha = state.alpha; },
    translate: (x: number, y: number) => { matrix.e += matrix.a*x + matrix.c*y; matrix.f += matrix.b*x + matrix.d*y; },
    rotate: (r: number) => { const m = matrix, c = Math.cos(r), s = Math.sin(r); matrix = {...m,
      a:m.a*c+m.c*s, b:m.b*c+m.d*s, c:m.c*c-m.a*s, d:m.d*c-m.b*s}; },
    scale: (x: number, y: number) => { matrix.a *= x; matrix.b *= x; matrix.c *= y; matrix.d *= y; },
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
    drawImage: record('drawImage'),
    fillText: record('fillText'),
    setLineDash: record('setLineDash'),
    clip: record('clip'),
    measureText: (text: string) => ({width: text.length * 10, actualBoundingBoxLeft: 0,
      actualBoundingBoxRight: text.length * 10, actualBoundingBoxAscent: 30, actualBoundingBoxDescent: 10}),
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
  frame.text('夜空为什么是黑的', 960, 838, {size: 76});
  frame.group({alpha: .5, at: [10, 20]}, () => frame.circle(200, 200, 40, {color: '#FFF'}));
  return {frame, calls};
}

describe('二维绘制原语', () => {
  it('同一帧绘制调用确定且文字返回排版宽度', () => {
    expect(drawOnce().calls).toEqual(drawOnce().calls);
    const {ctx} = stubContext();
    const painter = new Painter(ctx, 640, 360);
    expect(painter.text('TEST', 100, 100)).toBe(40);
    expect(painter.chars('TEST', 100, 100)).toBe(40);
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

describe('出帧层序', () => {
  /** 记录 drawImage 顺序的最小画布替身。 */
  function composeTarget() {
    const order: string[] = [];
    const context = {
      setTransform: () => undefined, save: () => undefined, restore: () => undefined,
      fillRect: () => order.push('clear'),
      drawImage: (source: {id?: string}) => order.push(source?.id ?? '?'),
      createPattern: () => null, fillStyle: '', globalAlpha: 1,
      globalCompositeOperation: 'source-over', filter: 'none', imageSmoothingEnabled: true,
    };
    const target = {
      width: 100, height: 100,
      getContext: () => context as unknown as CanvasRenderingContext2D,
    } as unknown as HTMLCanvasElement;
    return {target, order};
  }

  const layer = (id: string) => ({id} as unknown as HTMLCanvasElement);

  /** 辉光要新建临时画布；测试环境没有 DOM，给一个最小替身。 */
  function stubDocument() {
    const original = (globalThis as {document?: unknown}).document;
    const canvas = () => ({
      width: 0, height: 0,
      getContext: () => ({
        setTransform: () => undefined, clearRect: () => undefined, fillRect: () => undefined,
        drawImage: () => undefined, createRadialGradient: () => ({addColorStop: () => undefined}),
        createImageData: (w: number, h: number) => ({data: new Uint8ClampedArray(w * h * 4)}),
        putImageData: () => undefined, save: () => undefined, restore: () => undefined,
        filter: 'none', globalAlpha: 1, globalCompositeOperation: 'source-over',
      }),
    });
    (globalThis as {document?: unknown}).document = {createElement: canvas};
    return () => { (globalThis as {document?: unknown}).document = original; };
  }

  it('锐利层画在辉光与全幅后期之后、颗粒之前', async () => {
    const {compose} = await import('./bloom');
    const restore = stubDocument();
    const {target, order} = composeTarget();
    try {
    compose(target, {
      width: 100, height: 100, scale: 1, frame: 0, bloom: 1, grain: 0,
      background: layer('background'), under: layer('under'),
      content: layer('content'), post: layer('post'), overlay: layer('overlay'),
    });
    } finally { restore(); }
    const at = (name: string) => order.indexOf(name);
    // 文字放最后可见层：既不吃辉光，也不被 post 染色。
    expect(at('content')).toBeGreaterThan(at('under'));
    expect(at('content')).toBeGreaterThan(at('background'));
    expect(at('overlay')).toBeGreaterThan(at('post'));
    expect(at('overlay')).toBe(order.length - 1);
  });

  it('关闭辉光时内容与锐利层仍然画上', async () => {
    const {compose} = await import('./bloom');
    const restore = stubDocument();
    const {target, order} = composeTarget();
    try {
    compose(target, {
      width: 100, height: 100, scale: 1, frame: 0, bloom: 0, grain: 0,
      content: layer('content'), overlay: layer('overlay'),
    });
    } finally { restore(); }
    expect(order).toContain('content');
    expect(order).toContain('overlay');
  });
});

describe('离屏复用', () => {

  it('离屏层把重叠对象合成后整体绘制，并在异常后可继续使用', () => {
    const {ctx, calls} = stubContext();
    const restore = (globalThis as {document?: unknown}).document;
    let allocations = 0;
    const offscreen = {width: 0, height: 0, getContext: () => ({
      setTransform: () => undefined, clearRect: () => undefined, save: () => undefined,
      restore: () => undefined, getTransform: () => ({a: 1, b: 0, c: 0, d: 1, e: 0, f: 0}),
      beginPath: () => undefined, rect: () => undefined, clip: () => undefined,
      drawImage: () => undefined, globalAlpha: 1, globalCompositeOperation: 'source-over',
      fillStyle: '', strokeStyle: '', lineWidth: 1, lineCap: 'round', lineJoin: 'round',
      shadowColor: '', shadowBlur: 0, filter: 'none', setLineDash: () => undefined,
      arc: () => undefined, ellipse: () => undefined, fill: () => undefined, stroke: () => undefined,
      moveTo: () => undefined, lineTo: () => undefined, closePath: () => undefined,
      fillText: () => undefined,
      measureText: () => ({width: 10, actualBoundingBoxLeft: 0, actualBoundingBoxRight: 10,
        actualBoundingBoxAscent: 8, actualBoundingBoxDescent: 2}),
      createRadialGradient: () => ({addColorStop: () => undefined}),
      createLinearGradient: () => ({addColorStop: () => undefined}),
    })};
    (globalThis as {document?: unknown}).document = {createElement: () => { allocations++; return offscreen; }};
    const p = new Painter(ctx, 640, 360, 1);
    try {
      p.layer({alpha: .5, at: [10, 20]}, layer => {
        layer.circle(100, 100, 20, {fill: '#FFF'});
        layer.circle(110, 100, 20, {fill: '#FFF'});
      });
      expect(() => p.layer({}, () => { throw Error('stop'); })).toThrow('stop');
      p.layer({alpha: 0}, layer => layer.text('hidden', 30, 30, {}));
      p.layer({scale: 2}, layer => layer.text('scaled', 30, 30, {size: 20}));
      p.text('ok', 50, 50, {});
      expect(calls.some(call => call.name === 'drawImage')).toBe(true);
      expect(allocations).toBe(1);
    } finally { (globalThis as {document?: unknown}).document = restore; }
  });
});
