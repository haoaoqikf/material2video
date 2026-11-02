## ADDED Requirements

### Requirement: 代码场景 SDK 导出纯动效与字幕模块

`m2v/code-scene` SHALL 导出 `random.ts`、`dynamics.ts` 与 `subtitles.ts` 的公开符号，使作品与风格组件在不直接依赖第三方包的情况下使用固定种子、路径采样、光轨、爆散、扩散环、互补溶解、逐字错峰与字幕窗口工具。

第三方纯函数库（`svg-path-properties`、`perfect-freehand`）MAY 以显式命名导出。SDK MUST NOT 以 `export *` 暴露整个第三方包，以免重名与无意扩大 API。新增模块 MUST 进入 `implementation_inputs()` 的实现指纹，使其变化使引用作品的准备与片段缓存失效。

#### Scenario: 作品使用动效原语

- **WHEN** 场景从 `m2v/code-scene` 导入 `sampleTrail` 或 `staggerReveal`
- **THEN** 导入成功且不要求作品在 `package.json` 中声明第三方依赖

#### Scenario: 模块变化使缓存失效

- **WHEN** 修改 `dynamics.ts` 或 `subtitles.ts`
- **THEN** 引用作品的准备指纹与片段缓存失效，必须重新准备并复查

#### Scenario: 直接导入第三方包

- **WHEN** 风格组件或作品源码直接 `import` `svg-path-properties`、`perfect-freehand` 或其他新增第三方动效库
- **THEN** 组件导入闸门或审查明确失败，须改为从 `m2v/code-scene` 导入
