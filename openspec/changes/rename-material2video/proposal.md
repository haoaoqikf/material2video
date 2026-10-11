## Why

项目已覆盖文章、金融时间序列和通用多场景制作，旧名不能准确反映材料到成片的定位。统一品牌与技术命名，避免新旧接口混用。

## What Changes

- 展示名改为 Material2Video（材料成片），包名改为 material2video。
- **BREAKING**：命令、Python 模块与场景接口统一为 m2v、@m2v/scene；环境变量和浏览器契约使用 M2V/m2v 前缀，不提供旧接口别名。
- 制作 Skill 改为 material2video，同步参考文档、示例及迁移说明。
- 顺带修复统一入口对仓库自带示例的产物归属：`examples/<slug>/` 下的作品经 `m2v prepare/preview/render`
  产出的媒体、预演与成片统一落在 `videos/examples/<slug>/outputs/`，与文章辅助流程的既有约定一致，
  不再写进受版本控制的示例目录。
- 保持材料格式和业务流程，旧作品需更新代码引用并重新准备、预演、评审。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-workspace`：将现有制作接口和契约名称统一为新名称，保留全部业务约束。
- `financial-timeseries-video`：将现有制作接口和契约名称统一为新名称，保留全部业务约束。
- `keynote-design-system`：将现有制作接口和契约名称统一为新名称，保留全部业务约束。
- `modular-video-production`：将现有制作接口和契约名称统一为新名称，保留全部业务约束。
- `remotion-renderer`：将现有制作接口和契约名称统一为新名称，保留全部业务约束。
- `render-provenance`：将现有制作接口和契约名称统一为新名称，保留全部业务约束。
- `video-production-workflow`：将现有制作接口和契约名称统一为新名称，保留全部业务约束。

## Impact

影响 Python 和前端源码、构建配置、包元数据、锁文件、测试、Skill 及当前文档。不修改历史归档、作品内容、本地仓库目录或远程仓库。
