/**
 * 字号阶文档 ↔ 排版引擎 ↔ 样式令牌的三方逐值机检。
 *
 * `references/keynote-design-system.md` 的「字号阶」表、
 * `web/src/runtime/typography.ts` 的 `SCALE`、
 * `web/src/styles/tokens.css` 的 `--a2v-size-*` 三处必须逐值一致：
 * 引擎取档与样式表取值必须是同一个真源，改了任何一边而没改其余两边，
 * 这里都会失败并指出哪一档的哪个值。表格里的「用途」列是给人看的描述，
 * 不参与比对。
 *
 * 与 motionDoc.test.ts 同一模式：文档是给人看的，机检是给文档兜底的。
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { SCALE, MIN_BODY_PX } from './typography';

const DOC_PATH = join(
  import.meta.dirname,
  '..',
  '..',
  '..',
  '.agents',
  'skills',
  'article2video',
  'references',
  'keynote-design-system.md',
);
const TOKENS_PATH = join(import.meta.dirname, '..', 'styles', 'tokens.css');

function docTable(header: string): string[] {
  const doc = readFileSync(DOC_PATH, 'utf-8');
  const lines = doc.split('\n');
  const start = lines.findIndex((line) => line.includes(header));
  expect(start, `keynote-design-system.md 里找不到含「${header}」的表头`).toBeGreaterThanOrEqual(0);
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

describe('字号阶：文档、SCALE 与样式令牌三方一致', () => {
  const docRows = docTable('| 档位 | 令牌 | 字号 | 行高 | 字距 | 用途 |').map((row) => {
    const [level, token, size, leading, tracking] = cells(row);
    return {
      level: level!.replace(/`/g, ''),
      token: token!.replace(/`/g, ''),
      size,
      leading,
      tracking,
    };
  });

  it('文档表与 SCALE 逐档逐值一致', () => {
    expect(docRows.map((row) => row.level)).toEqual(SCALE.map((level) => level.name));
    for (const row of docRows) {
      const level = SCALE.find((entry) => entry.name === row.level);
      expect(level, `文档表里的档位 ${row.level} 在 SCALE 里不存在`).toBeDefined();
      expect(row.size, `${row.level}.size`).toBe(`${level!.size}px`);
      expect(Number(row.leading), `${row.level}.leading`).toBe(level!.leading);
      expect(
        Number(row.tracking!.replace('em', '')),
        `${row.level}.tracking`,
      ).toBe(level!.tracking);
      expect(row.token, `${row.level} 的令牌名`).toBe(`--a2v-size-${row.level}`);
    }
  });

  it('SCALE 每一档在 tokens.css 里都有同名令牌且数值相同', () => {
    const tokens = readFileSync(TOKENS_PATH, 'utf-8');
    for (const level of SCALE) {
      const token = `--a2v-size-${level.name}`;
      const match = tokens.match(new RegExp(`${token.replace(/-/g, '\\-')}:\\s*([\\d.]+)px`));
      expect(match, `tokens.css 里缺少 ${token}`).not.toBeNull();
      expect(Number(match![1]), `${token} 的字号`).toBe(level.size);
    }
  });

  it('正文下限与文档口径一致（36px，低于即拆场景）', () => {
    expect(MIN_BODY_PX).toBe(36);
    const doc = readFileSync(DOC_PATH, 'utf-8');
    expect(doc).toContain('**正文下限 36px**');
  });
});
