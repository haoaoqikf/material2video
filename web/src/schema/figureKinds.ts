/* eslint-disable */
/**
 * 分镜 `figure.kind` 的取值枚举——**生成物，不要手改**。
 *
 * 由 `scripts/sync_catalog.py` 从 `web/src/registry/registry.json` 生成；
 * 消费方是 `web/src/schema/storyboard.ts` 的 `figureSchema`：kind 写了
 * 但不在这份清单里时，解析报错并列出已知组件。重新生成：
 *
 *     uv run python .agents/skills/article2video/scripts/sync_catalog.py
 *
 * 手改后运行同一命令加 `--check` 会被判为落后并指名本文件。
 */
export const FIGURE_KINDS = [
  'balance',
  'chart',
  'exchange',
  'flow',
  'gap',
  'iceberg',
  'loop',
  'number',
  'stairs',
  'versus',
] as const;

export type FigureKind = (typeof FIGURE_KINDS)[number];
