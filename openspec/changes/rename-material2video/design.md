## Context

参见 proposal.md。旧前缀同时用于 Python 导入、前端场景 API、CSS/DOM、浏览器桥接与渲染缓存。必须配对变更生产者与消费者。

## Goals / Non-Goals

**Goals:** 统一活动接口及新产物命名，三类视频制作保持可运行。

**Non-Goals:** 不改业务材料格式，不增加兼容别名，不迁移用户作品，不移动本地仓库。

## Decisions

- Python 目录改为 src/m2v，Skill 改为 .agents/skills/material2video；内部缩写统一 m2v/M2V。相比保留旧别名，完整替换符合用户选择。
- 对受版本控制的文本进行命名替换并逐项审查契约；历史归档保留，主规格通过完整 MODIFIED requirement 合并，避免历史和当前事实混淆。
- README 使用 Material2Video（材料成片）展示名，提供旧接口迁移表。依赖版本保持不变，仅更新包身份及锁文件。
- 验证使用临时作品和新产物，不依据旧缓存或旧评审判定成功。
- 统一入口的产物路径从文章归属推导（`ArticlePaths.output_dir`），不再写死 `<作品根>/outputs`。
  仓库自带示例的作品根是 `examples/<slug>/`，而它的产物属于 `videos/examples/<slug>/outputs/`；
  写死会让示例的媒体与预演落进受版本控制的示例目录，也让 `prepare` 的媒体归属守卫直接拒绝。
  统一入口登记完整预演时同样不能假定预演在作品根内：预演记录改为按作品根相对化并允许 `..`，
  读回仍用 `作品根 / path` 解析，普通作品的记录内容逐字不变。
  这是改名之前就存在的缺陷（上一次模块化重构引入），本次一并修复并补回归测试。
  仍不一致的是统一入口自身的记录（`prepared.json`、`preview-record.json`、`review.json`）：
  它们由共享 `core/project` 与 `cli.py` 按 `<作品根>/outputs/` 读写，示例下会落在
  `examples/<slug>/outputs/`（已被 `.gitignore` 忽略，写入与读回一致，功能可用）。
  改成跟随产物归属要动三种类型共用的底座，留作独立变更，此处如实记录。

## Risks / Trade-offs

- [外部脚本失效] → 明确列出新命令、变量、导入及 Skill 路径，不自动改用户材料。
- [浏览器桥接不一致] → 同步 DOM dataset、CSS、查询参数、挂载路径和全局契约，运行浏览器及短片渲染集成测试。
- [旧环境安装残留] → 重新同步依赖并检查安装后的命令与模块身份。

## Migration Plan

先记录变更，再替换源码和路径，更新文档与示例，运行全套测试和构建。验证后提交实施结果，同步全部 delta 并归档提交。回滚通过撤销本次提交并重新同步依赖完成；作品内容不被写入。
