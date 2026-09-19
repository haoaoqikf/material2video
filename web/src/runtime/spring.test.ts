/**
 * 闭式解弹簧求解器的可信度（TS 版，逐条对应 `tests/test_vendor_spring.py`）。
 *
 * 引入外部实现的前提是**它真的对**。这里对着阻尼谐振子的理论值核对——
 * 不是核对「我记得的数值」，而是核对闭式解自己的性质：
 *
 *   - ζ=1 时不过冲，且单调；
 *   - ζ<1 时峰值过冲等于 e^(-πζ/√(1-ζ²))（教科书结论，独立于实现）；
 *   - 曲线只有两个端点固定（0 与 1），与 ω₀ 无关——换 response 只改变快慢，不改变形状；
 *   - 纯函数：同一入参永远同一结果（没有 Math.random、没有时间源）；
 *   - 出处与许可证留在文件里，不是「从网上抄来的一段」。
 *
 * 少了这一层，一个符号写错（x₀ = -1 而不是 +1）的解析解看起来也「像弹簧」。
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { position, restSeconds, SPRING_LICENSE, SPRING_SOURCE } from '@/runtime/spring';

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, '..', '..');
const solverSource = path.resolve(webRoot, 'src', 'runtime', 'spring.ts');
const licenseFile = path.resolve(webRoot, 'LICENSES', 'wobble-LICENSE');

function curve(response: number, zeta: number, count: number): number[] {
  const out: number[] = [];
  for (let i = 0; i <= count; i += 1) {
    out.push(position((i / count) * 2.0, response, zeta));
  }
  return out;
}

describe('出处与许可证', () => {
  it('在代码里声明来源与许可证', () => {
    // 「从哪儿来的」必须写在文件里，否则没人能判断它能不能用、该不该改
    expect(SPRING_SOURCE).toBe('wobble@1.5.1');
    expect(SPRING_LICENSE).toBe('MIT');
  });

  it('许可证全文随仓库分发', () => {
    const text = readFileSync(licenseFile, 'utf8');
    expect(text).toContain('Adam Miskiewicz');
    expect(text.split('\n')[0]).not.toContain('MIT');
  });

  it('文件头写明相对上游的改动', () => {
    const header = readFileSync(solverSource, 'utf8');
    expect(header).toContain('wobble');
    expect(header).toContain('MIT');
    expect(header).toContain('改动');
  });
});

describe('闭式解的性质', () => {
  it('从 0 开始，且负时间夹到 0', () => {
    expect(position(0, 0.44, 0.9)).toBe(0);
    // 负时间要夹到 0，否则会先往回弹一下
    expect(position(-1, 0.44, 0.9)).toBe(0);
  });

  it('临界阻尼不过冲且单调', () => {
    const critical = curve(0.44, 1, 800);
    expect(Math.max(...critical)).toBeLessThanOrEqual(1 + 1e-9);
    expect(critical).toEqual([...critical].sort((a, b) => a - b));
  });

  it('峰值过冲等于教科书结论 e^(-πζ/√(1-ζ²))', () => {
    const zeta = 0.62;
    const expected = Math.exp((-Math.PI * zeta) / Math.sqrt(1 - zeta ** 2));
    const measured = Math.max(...curve(0.4, zeta, 800)) - 1;
    expect(measured).toBeCloseTo(expected, 2);
  });

  it('response 只缩放时间，不改变曲线形状', () => {
    // 两条曲线的采样网格都是 0..2 秒、400 段，所以快的那条第 i 点
    // 正好对应慢的那条第 4i 点
    const fast = curve(0.2, 0.9, 400);
    const slow = curve(0.8, 0.9, 400);
    for (const i of [25, 50, 75, 100]) {
      expect(fast[i]).toBeCloseTo(slow[4 * i], 2);
    }
  });

  it('过阻尼不振荡', () => {
    const overdamped = curve(0.44, 1.6, 400);
    expect(Math.max(...overdamped)).toBeLessThanOrEqual(1 + 1e-9);
    expect(overdamped).toEqual([...overdamped].sort((a, b) => a - b));
  });

  it('是纯函数', () => {
    expect(position(0.123, 0.44, 0.9)).toBe(position(0.123, 0.44, 0.9));
  });

  it('非法参数不抛错，退回安全值', () => {
    // 组件里常有人手写参数；抛错会让整帧渲不出来，而画面坏掉比参数难看严重得多
    expect(position(0.2, 0, 0.9)).toBeGreaterThan(0);
    expect(Number.isFinite(position(0.2, 0.44, -1))).toBe(true);
  });
});

describe('收敛时刻', () => {
  it('按预测时间进入 ±band 带内', () => {
    // 包络界 e^(-ζω₀t) ≤ band ⇒ 到点后剩余偏差不超过 0.1%
    const t = restSeconds(0.4, 0.62);
    expect(Math.abs(position(t, 0.4, 0.62) - 1)).toBeLessThanOrEqual(0.001);
  });

  it('ζ=0 时永不收敛', () => {
    expect(restSeconds(0.4, 0)).toBe(Infinity);
  });
});
