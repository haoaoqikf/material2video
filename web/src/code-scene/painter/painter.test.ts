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


describe('绘制量测反例', () => {
  it('透明文字与全部未显影文字不计为可见对象', () => {
    const {ctx} = stubContext();
    const p = new Painter(ctx, 640, 360);
    p.text('TEST', 100, 100, {role: 'subject', alpha: 0});
    p.chars('TEST', 100, 100, {role: 'subject'}, () => ({alpha: 0}));
    expect(p.marks.every(m => m.visible === false)).toBe(true);
    expect(reviewState(p.marks)).toEqual([]);
  });
  it('部分显影只报告已画文字', () => {
    const {ctx} = stubContext();
    const p = new Painter(ctx, 640, 360);
    p.chars('TEST', 100, 100, {role: 'subject'}, i => ({alpha: i < 2 ? 1 : 0}));
    expect(p.marks).toHaveLength(1);
    expect(p.marks[0].text).toBe('TE');
    expect(p.marks[0].width).toBe(20);
  });
  it('嵌套变换按当前矩阵换算，采集倍数不改变逻辑几何', () => {
    for (const density of [1, 2]) {
      const {ctx} = stubContext();
      const p = new Painter(ctx, 640, 360, density);
      p.group({at: [100, 50], scale: 2}, () => p.group({at: [10, 10]}, () =>
        p.text('TEST', 0, 40, {role: 'subject', align: 'left', size: 20})));
      expect(p.marks[0]).toMatchObject({x: 120, y: 90, width: 80, height: 80, fontSize: 40});
    }
  });
  it('离屏、零透明度与完全裁剪分组不可见，裁剪退出后恢复', () => {
    const {ctx} = stubContext();
    const p = new Painter(ctx, 640, 360);
    const draw = () => p.text('TEST', 100, 100, {role: 'subject'});
    p.group({at: [1000, 0]}, draw);
    p.group({alpha: 0}, draw);
    p.group({clip: [0, 0, 1, 1]}, draw);
    draw();
    expect(p.marks.map(m => m.visible)).toEqual([false, false, false, true]);
  });
  it('旋转裁剪使用真实多边形，不用其外框放行', () => {
    const {ctx} = stubContext();
    const p = new Painter(ctx, 640, 360);
    p.group({at: [100,100], rotate: Math.PI/4, clip: [0,0,100,100]}, () => {
      // 返回世界坐标后，左上角处于裁剪外框内、真实菱形之外。
      p.group({rotate: -Math.PI/4}, () => p.text('T', -60, 35, {role:'subject', align:'left'}));
    });
    expect(p.marks[0].visible).toBe(false);
  });
  it('部分裁剪保留裁切标记，分组抛错仍恢复 context', () => {
    const {ctx} = stubContext();
    const p = new Painter(ctx, 640, 360);
    p.group({clip:[90,0,10,200]}, () => p.text('TEST',100,100,{role:'subject'}));
    expect(p.marks[0]).toMatchObject({visible:true,clipped:true});
    expect(() => p.group({alpha:0,at:[1000,0]}, () => {throw Error('stop');})).toThrow();
    p.text('TEST',100,100,{role:'subject'});
    expect(p.marks[1]).toMatchObject({visible:true,x:80});
  });
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
      expect(p.marks).toHaveLength(0);
      expect(() => p.layer({}, () => { throw Error('stop'); })).toThrow('stop');
      p.layer({alpha: 0}, layer => layer.text('hidden', 30, 30, {role: 'subject'}));
      expect(p.marks[0]?.visible).toBe(false);
      p.layer({scale: 2}, layer => layer.text('scaled', 30, 30, {role: 'scaled', size: 20}));
      expect(p.marks[1]?.fontSize).toBe(40);
      p.text('ok', 50, 50, {role: 'subject'});
      expect(p.marks[2]?.visible).toBe(true);
      expect(calls.some(call => call.name === 'drawImage')).toBe(true);
      expect(allocations).toBe(1);
    } finally { (globalThis as {document?: unknown}).document = restore; }
  });
});
