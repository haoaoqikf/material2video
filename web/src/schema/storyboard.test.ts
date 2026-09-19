/**
 * 分镜 schema 的契约：**新旧两条路径必须对同一份分镜给出同一个结论**。
 *
 * 最要紧的一条是最后一组：仓库里每一个示例分镜都要能被解析。
 * 这个工程里 schema 比 Python 校验器更严过一次——图节点只允许 `{id}`，
 * 而既有示例用的是 `{id, label}`（画面上显示 `label`）。后果不是报错，
 * 而是那一整份分镜在契约页上**画不出来**：Python 说它合法，React 说它非法。
 */

import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  diagramNodeSchema,
  KNOWN_SCENE_DATA,
  parseSceneData,
  parseStoryboard,
  storyboardSchema,
} from '@/schema/storyboard';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const examplesDir = path.join(repoRoot, 'examples');

function minimal(scene: Record<string, unknown>) {
  return {
    version: 1,
    fps: 30,
    scenes: [{ id: 'one', type: 'diagram', durationInFrames: 60, data: {}, ...scene }],
  };
}

function exampleStoryboards(): Array<[string, unknown]> {
  return readdirSync(examplesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const file = path.join(examplesDir, entry.name, 'storyboard.json');
      return [entry.name, JSON.parse(readFileSync(file, 'utf8'))] as [string, unknown];
    });
}

describe('分镜骨架', () => {
  it('接受合法分镜并补上尺寸默认值', () => {
    const parsed = storyboardSchema.parse(minimal({ data: { nodes: ['甲', '乙'] } }));
    expect(parsed.width).toBe(1080);
    expect(parsed.height).toBe(1920);
    // 整份 `visual` 缺席时保持缺席：主题兜底在组件里（`storyboard.visual?.theme ?? 'dark'`），
    // 这里再塞一个默认对象会让「有没有声明过视觉配置」变得不可判定
    expect(parsed.visual).toBeUndefined();
  });

  it('声明了 visual 但没写主题时补 dark', () => {
    const parsed = storyboardSchema.parse({ ...minimal({ data: {} }), visual: {} });
    expect(parsed.visual?.theme).toBe('dark');
  });

  it('拒绝未知的顶层字段，而不是默默忽略', () => {
    const result = storyboardSchema.safeParse({ ...minimal({ data: {} }), tempo: 'fast' });
    expect(result.success).toBe(false);
  });
});

describe('图节点', () => {
  it('字符串形式当作 id', () => {
    const data = parseSceneData(
      storyboardSchema.parse(minimal({ data: { nodes: ['甲'], edges: [] } })).scenes[0],
    );
    expect(data.nodes).toEqual(['甲']);
  });

  it('对象形式带 label——示例分镜用的就是这一种', () => {
    const scene = storyboardSchema.parse(
      minimal({
        data: {
          nodes: [
            { id: 'open', label: '打开选项' },
            { id: 'later' },
          ],
          edges: [{ from: 'open', to: 'later' }],
        },
      }),
    ).scenes[0];
    const data = parseSceneData(scene) as { nodes: Array<Record<string, unknown>> };
    expect(data.nodes[0]).toEqual({ id: 'open', label: '打开选项' });
  });

  it('节点缺少 id 时报错', () => {
    const scene = storyboardSchema.parse(minimal({ data: { nodes: [{ label: '甲' }] } })).scenes[0];
    expect(diagramNodeSchema.safeParse({ label: '甲' }).success).toBe(false);
    expect(KNOWN_SCENE_DATA.diagram.safeParse({ nodes: [{ label: '甲' }] }).success).toBe(false);
    expect(() => parseSceneData(scene)).toThrow(/data 校验失败/);
  });
});

describe('示例分镜', () => {
  const cases = exampleStoryboards();

  it('至少有一个示例（否则这组断言是空转的）', () => {
    expect(cases.length).toBeGreaterThan(0);
  });

  it.each(cases)('%s 能被新工程的 schema 解析，且每一幕的 data 也合法', (_name, raw) => {
    const storyboard = parseStoryboard(raw);
    expect(storyboard.scenes.length).toBeGreaterThan(0);
    for (const scene of storyboard.scenes) {
      // 未知类型原样返回，由渲染层报错；这里只要求已知类型真的合法
      expect(() => parseSceneData(scene), `场景 ${scene.id}`).not.toThrow();
    }
  });
});
