# 第三方视觉组件接入（已废止）

v3 场景树架构不允许第三方组件参与画面：分镜只能使用
[视觉原语目录](primitive-catalog.md) 登记的受控原语，
`web/src/third-party/` 目录与分类接入机制（catalog.json、`FrameSyncedCssAnimation` 等）
已随整页组件路径一并移除。

需要新的视觉能力时，按原语注册表契约登记并实现通用原语：
`web/src/registry/registry.json` + `web/src/primitives/SceneTree.tsx` 实现 +
`scripts/sync_catalog.py` 重新生成 + 机检，再沉淀回原语目录。
