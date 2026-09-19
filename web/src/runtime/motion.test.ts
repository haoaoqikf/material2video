/**
 * 配方层与旧实现的逐值对照。
 *
 * 「逐值照搬」不能靠人记得两边一样：这里把 `assets/timeline.js`（连同它依赖的
 * `assets/vendor/spring.js`）在 `node:vm` 里跑起来当作**对照实现**，
 * 再对同一批输入逐个比较输出。任何一处数字被改动，对照立刻失败并指出是哪一项。
 *
 * 另外验证「随机访问任意帧的结果与顺序无关」：帧号是唯一输入，
 * 打乱顺序逐个求值必须与顺序求值完全一致。这条挡的是「累积状态」——
 * 旧运行时把当前帧藏在模块级变量里，拖动进度条时就会算出不一样的结果。
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  EASE,
  EASING,
  breath,
  clamp,
  drawPathStyle,
  enterRecipe,
  lerp,
  motionBeat,
  motionRecipes,
  motionSprings,
  progress,
  range,
  revealCharOpacities,
  since,
  spring,
  stagger,
  TEMPO_SPEED,
  DRIFT_PERIOD,
  type MotionState,
} from '@/runtime/motion';

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, '..', '..');
const assets = path.resolve(webRoot, '..', '.agents', 'skills', 'article2video', 'assets');

interface LegacyRuntime {
  progress: (...args: unknown[]) => number;
  stagger: (...args: unknown[]) => number;
  since: (...args: unknown[]) => number;
  spring: (...args: unknown[]) => number;
  range: (...args: unknown[]) => number;
  breath: (...args: unknown[]) => number;
  clamp: (value: number, min: number, max: number) => number;
  lerp: (from: number, to: number, t: number) => number;
  easing: Record<string, (t: number) => number>;
  revealChars: (el: unknown, text: string, p: number, options?: unknown) => void;
  drawPath: (node: unknown, p: number, options?: unknown) => void;
  motion: {
    recipes: () => Record<string, Record<string, number>>;
    springs: () => Record<string, Record<string, number>>;
    beat: (state: unknown, fraction: number) => number;
    enter: (state: unknown, el: unknown, seconds: number, options?: unknown) => void;
    tempo: (name?: string) => number;
    idle: (localFrame: number, options?: unknown) => number;
  };
}

/** 一个够 `revealChars` / `drawPath` 用的小 DOM 替身。 */
function fakeNode(attributes: Record<string, string> = {}) {
  const node: Record<string, unknown> = {
    children: [] as Array<Record<string, unknown>>,
    text: '',
    style: {} as Record<string, string>,
    attributes: { ...attributes },
    getAttribute(name: string) {
      return name in (node.attributes as Record<string, string>)
        ? (node.attributes as Record<string, string>)[name]
        : null;
    },
    hasAttribute(name: string) {
      return name in (node.attributes as Record<string, string>);
    },
    setAttribute(name: string, value: unknown) {
      (node.attributes as Record<string, string>)[name] = String(value);
    },
    appendChild(child: Record<string, unknown>) {
      const children = node.children as Array<Record<string, unknown>>;
      // 真实 DOM 在 appendChild 时就把片段的孩子摊平进元素，所以这里也必须即时摊平：
      // 延后到调用返回后再摊平，revealChars 读到的 el.children 就是错的
      if (child.isFragment) {
        children.push(...((child.children as Array<Record<string, unknown>>) ?? []));
      } else {
        children.push(child);
      }
      return child;
    },
  };
  Object.defineProperty(node, 'textContent', {
    get: () => {
      const children = node.children as Array<{ textContent?: string }>;
      return children.length ? children.map((child) => child.textContent ?? '').join('') : (node.text as string);
    },
    set: (value: string) => {
      // 赋文本会清空既有子节点（真实 DOM 语义）
      node.children = [];
      node.text = String(value);
    },
  });
  return node;
}

function loadLegacy(): LegacyRuntime {
  const document = {
    createElement: () => fakeNode(),
    createDocumentFragment: () => {
      const fragment = { children: [] as Array<Record<string, unknown>>, isFragment: true };
      return Object.assign(fragment, {
        appendChild(child: Record<string, unknown>) {
          fragment.children.push(child);
          return child;
        },
      });
    },
  };

  const sandbox: Record<string, unknown> = { console, document };
  sandbox.window = sandbox;
  const context = vm.createContext(sandbox);
  // 与页面同一套加载顺序：先求解器，再运行时。少了求解器，spring() 会直接抛错
  for (const file of ['vendor/spring.js', 'timeline.js']) {
    vm.runInContext(readFileSync(path.join(assets, file), 'utf8'), context, { filename: file });
  }

  const element = sandbox.A2V as LegacyRuntime;
  return element;
}

const legacy = loadLegacy();

const EASING_NAMES = ['linear', 'outCubic', 'inOutCubic', 'outQuint', 'outBack'] as const;

describe('缓动曲线逐值一致', () => {
  it.each(EASING_NAMES)('%s', (name) => {
    for (let i = 0; i <= 100; i += 1) {
      const t = i / 100;
      expect(EASING[name](t), `${name}(${t})`).toBeCloseTo(legacy.easing[name](t), 12);
    }
  });

  it('只走三条常量曲线', () => {
    expect(EASE).toEqual({ enter: 'outQuint', gate: 'outCubic', both: 'inOutCubic' });
  });
});

describe('配方函数与旧实现逐值一致', () => {
  it('progress', () => {
    for (const easing of [...EASING_NAMES, undefined]) {
      for (const localFrame of [0, 1, 7, 18, 41, 100, 900]) {
        for (const [start, duration] of [
          [0, 18],
          [7, 11],
          [0, 0],
          [12, -3],
          [30, 17],
        ]) {
          expect(
            progress(localFrame, start, duration, easing as never),
            `progress(${localFrame}, ${start}, ${duration}, ${String(easing)})`,
          ).toBeCloseTo(legacy.progress(localFrame, start, duration, easing), 12);
        }
      }
    }
  });

  it('stagger / clamp / lerp', () => {
    expect(stagger(3, 4, 2)).toBe(legacy.stagger(3, 4, 2));
    expect(stagger(1, 0)).toBe(legacy.stagger(1, 0));
    expect(clamp(7, 0, 5)).toBe(legacy.clamp(7, 0, 5));
    expect(lerp(2, 10, 0.25)).toBe(legacy.lerp(2, 10, 0.25));
  });

  it('since', () => {
    for (const frame of [0, 1, 30, 45, 900]) {
      for (const [start, fps] of [
        [0, 30],
        [12, 30],
        [0, 0],
        [5, 60],
      ]) {
        expect(since(frame, start, fps)).toBeCloseTo(legacy.since(frame, start, fps), 12);
      }
    }
  });

  it('range 的钳制开关', () => {
    for (const t of [-0.5, 0, 0.5, 1, 1.4]) {
      for (const clampOption of [undefined, true, false]) {
        const options = clampOption === undefined ? undefined : { clamp: clampOption };
        expect(range(t, 3, 9, options)).toBeCloseTo(legacy.range(t, 3, 9, options), 12);
      }
    }
  });

  it('breath', () => {
    for (const frame of [0, 1, 30, 75, 150, 301]) {
      for (const options of [
        undefined,
        { periodFrames: 120, amplitude: 4 },
        { periodFrames: 150, amplitude: 3, phase: 40 },
        { periodFrames: 0, amplitude: 5 },
      ]) {
        expect(breath(frame, options)).toBeCloseTo(legacy.breath(frame, options), 12);
      }
    }
  });

  it('spring（含到位后钉在 1）', () => {
    for (const seconds of [0, 0.01, 0.1, 0.25, 0.44, 1, 3]) {
      for (const options of [
        undefined,
        { response: 0.44, dampingFraction: 0.9 },
        { response: 0.4, dampingFraction: 0.62 },
        { response: 0.5, dampingFraction: 1 },
        { response: 0.28, dampingFraction: 0.8 },
      ]) {
        expect(spring(seconds, options)).toBeCloseTo(legacy.spring(seconds, options), 12);
      }
    }
  });

  it('配方表与弹性预设表', () => {
    expect(motionRecipes()).toEqual(legacy.motion.recipes());
    expect(motionSprings()).toEqual(legacy.motion.springs());
  });

  it('节奏倍率与幕内常驻微动', () => {
    for (const name of ['calm', 'normal', 'impact', 'unknown', undefined]) {
      expect(TEMPO_SPEED[name as string] ?? 1).toBe(legacy.motion.tempo(name));
    }
    for (const frame of [0, 40, 151]) {
      expect(legacy.motion.idle(frame, { phase: 20 })).toBeCloseTo(
        breath(frame, { periodFrames: DRIFT_PERIOD, amplitude: 3, phase: 20 }),
        12,
      );
    }
  });

  it('motionBeat 按幕长与节奏换算', () => {
    const state = { localFrame: 10, sceneDurationFrames: 240, motion: 'impact' };
    expect(motionBeat(state, 0.24)).toBeCloseTo(
      legacy.motion.beat({ localFrame: 10, sceneDurationFrames: 240, scene: { data: { figure: { motion: 'impact' } } } }, 0.24),
      12,
    );
  });
});

describe('逐字揭示与描边', () => {
  const text = '反馈，让下一次更有方向';

  it('进度模式逐字不透明度一致', () => {
    for (const p of [0, 0.2, 0.5, 0.8, 1]) {
      const target = fakeNode();
      legacy.revealChars(target, text, p);
      const expected = (target.children as Array<{ style: Record<string, string> }>).map((child) =>
        Number(child.style.opacity),
      );
      expect(revealCharOpacities(text, p)).toEqual(expected);
    }
  });

  it('帧号模式逐字不透明度一致', () => {
    for (const frame of [0, 3, 9, 30]) {
      const target = fakeNode();
      legacy.revealChars(target, text, 0, { frame, staggerFrames: 3 });
      const expected = (target.children as Array<{ style: Record<string, string> }>).map((child) =>
        Number(child.style.opacity),
      );
      expect(revealCharOpacities(text, 0, { frame, staggerFrames: 3 })).toEqual(expected);
    }
  });

  it('空文案返回空数组，不产生节点', () => {
    const target = fakeNode();
    legacy.revealChars(target, '', 0.5);
    expect(revealCharOpacities('', 0.5)).toEqual([]);
    expect((target.children as unknown[]).length).toBe(0);
  });

  it('描边属性一致（含缺省长度）', () => {
    for (const p of [0, 0.3, 1, 1.4, -1]) {
      const node = fakeNode({ 'data-a2v-length': '420.5' });
      legacy.drawPath(node, p);
      const attributes = node.attributes as Record<string, string>;
      const style = node.style as Record<string, string>;
      const declared = Number(attributes['data-a2v-length']);
      expect(drawPathStyle(p, declared)).toEqual({
        strokeDasharray: attributes['stroke-dasharray'],
        strokeDashoffset: attributes['stroke-dashoffset'],
        opacity: style.opacity,
      });
    }
  });
});

describe('随机访问与顺序无关', () => {
  const state: MotionState = { localFrame: 0, sceneDurationFrames: 480, motion: 'normal' };
  const frames = [0, 1, 7, 40, 119, 240, 479];

  const sample = (frame: number) => {
    const local: MotionState = { ...state, localFrame: frame };
    const entrance = enterRecipe(local, 'surface', since(frame, 0, 30));
    return [
      entrance.from,
      entrance.shift,
      entrance.drift,
      entrance.scale,
      motionBeat(local, 0.24),
      breath(frame, { periodFrames: 130, amplitude: 3 }),
      spring(since(frame, 6, 30), { response: 0.44, dampingFraction: 0.9 }),
    ];
  };

  it('打乱顺序逐个求值与顺序求值完全一致', () => {
    const sequential = frames.map(sample);
    const shuffled = [...frames].reverse().map((frame) => [frame, sample(frame)] as const);
    for (const [frame, values] of shuffled) {
      expect(values).toEqual(sequential[frames.indexOf(frame)]);
    }
  });

  it('同一帧反复求值完全一致', () => {
    for (const frame of frames) {
      expect(sample(frame)).toEqual(sample(frame));
    }
  });
});
