/**
 * 动效配方文档 ↔ TS 常量的逐值机检（任务 10.4）。
 *
 * `references/visual-spec.md` 的「动效配方层」两张表（入场配方、具名弹性）
 * 必须与 `web/src/runtime/motion.ts` 的常量逐值一致：改了常量而没改文档、
 * 或改了文档而没改常量，这里都会失败并指出哪一个值。表里还有描述性列
 * （过冲、收敛、感觉），它们是常量的**派生量**——过冲由 ζ 算出、收敛由
 * response 与 ζ 算出，这里按同一公式核对，公式漂移也会被拦下。
 *
 * 文档是给人看的，机检是给文档兜底的：这比「两份手抄 + 人记」可靠。
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { RECIPES, SPRINGS, TEMPO_SPEED } from './motion';

const DOC_PATH = join(
  import.meta.dirname,
  '..',
  '..',
  '..',
  '.agents',
  'skills',
  'article2video',
  'references',
  'visual-spec.md',
);

function docTable(header: string): string[] {
  const doc = readFileSync(DOC_PATH, 'utf-8');
  const lines = doc.split('\n');
  const start = lines.findIndex((line) => line.includes(header));
  expect(start, `visual-spec.md 里找不到含「${header}」的表头`).toBeGreaterThanOrEqual(0);
  const rows: string[] = [];
  for (let i = start + 2; i < lines.length; i += 1) {
    const line = lines[i]!;
    if (!line.startsWith('|')) break;
    rows.push(line);
  }
  expect(rows.length, `「${header}」表没有数据行`).toBeGreaterThan(0);
  return rows;
}

function cells(row: string): string[] {
  return row
    .split('|')
    .map((cell) => cell.trim())
    .slice(1, -1);
}

/** 过冲峰值 ≈ e^(-πζ/√(1-ζ²))，临界阻尼（ζ=1）为 0。 */
function overshootPercent(dampingFraction: number): number {
  if (dampingFraction >= 1) return 0;
  return (
    Math.exp((-Math.PI * dampingFraction) / Math.sqrt(1 - dampingFraction ** 2)) * 100
  );
}

/** 收敛时间（进 2% 带内）：欠阻尼取包络 ≈ 3.91/(ζω₀)；临界阻尼解 x=(1+x)e^(-x)=0.02。 */
function settleSeconds(response: number, dampingFraction: number): number {
  if (dampingFraction >= 1) {
    return (5.836 * response) / (2 * Math.PI);
  }
  return (3.91 * response) / (2 * Math.PI * dampingFraction);
}

describe('visual-spec.md 的动效配方表与 TS 常量逐值一致', () => {
  it('入场配方表（surface / figure）', () => {
    for (const row of docTable('| 配方 | 用于 | 默认位移 | 呼吸周期 | 呼吸振幅 |')) {
      const [rawName, , distance, period, amplitude] = cells(row);
      const name = rawName!.replace(/`/g, '') as keyof typeof RECIPES;
      const recipe = RECIPES[name];
      expect(recipe, `文档表里的配方 ${name} 在 RECIPES 里不存在`).toBeDefined();
      expect(distance, `${name}.distance`).toBe(`${recipe.distance}px`);
      expect(period, `${name}.periodFrames`).toBe(`${recipe.periodFrames} 帧`);
      expect(amplitude, `${name}.amplitude`).toBe(`${recipe.amplitude}px`);
    }
  });

  it('具名弹性表（enter / firm / lively / snap）', () => {
    for (const row of docTable('| 预设 | response | ζ | 过冲 | 收敛 | 感觉 |')) {
      const [rawName, response, zeta, overshoot, settle] = cells(row);
      const name = rawName!.replace(/`/g, '');
      const spring = SPRINGS[name];
      expect(spring, `文档表里的弹性 ${name} 在 SPRINGS 里不存在`).toBeDefined();
      expect(response, `${name}.response`).toBe(`${spring.response}s`);
      expect(Number(zeta), `${name}.dampingFraction`).toBe(spring.dampingFraction);
      expect(
        Math.abs(
          overshootPercent(spring.dampingFraction) -
            Number(overshoot.replace(/[^\d.]/g, '')),
        ),
        `${name} 的过冲列应与 ζ 的解析解一致`,
      ).toBeLessThan(0.15);
      expect(
        Math.abs(settleSeconds(spring.response, spring.dampingFraction) - Number(settle.replace(/[^\d.]/g, ''))),
        `${name} 的收敛列应与解析解一致`,
      ).toBeLessThan(0.02);
    }
  });

  it('节奏倍率（calm / normal / impact）写在配方层说明里', () => {
    expect(TEMPO_SPEED['calm']).toBe(0.82);
    expect(TEMPO_SPEED['normal']).toBe(1);
    expect(TEMPO_SPEED['impact']).toBe(1.24);
    const doc = readFileSync(DOC_PATH, 'utf-8');
    expect(doc).toContain('`calm` 0.82 / `normal` 1 / `impact` 1.24');
  });
});
