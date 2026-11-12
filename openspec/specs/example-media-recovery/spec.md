# example-media-recovery Specification

## Purpose
为仓库固定示例提供可验证的媒体恢复方式，在保留来源、许可与确定性渲染输入的同时避免将可恢复媒体持续存入普通 Git，并明确恢复失败和缓存命中的行为。

## Requirements

### Requirement: 五类示例素材恢复

每例恢复入口 MUST 可在主项目不可访问时独立执行，媒体、声音和字体恢复所需代码、配方与许可 MUST 在本例内；MUST NOT 调用主项目author命令或共享资源目录。恢复过程不得接受摘要漂移。

五个示例 MUST 位于 `examples/<type>/<slug>/`；每个示例的恢复入口 MUST 按配方校验 SHA-256、尺寸与时长，不改写来源登记、许可或预期摘要。媒体及生成声音 MUST 被 Git 忽略，配方、分镜与场景源码 MUST 入库。

#### Scenario: 恢复与运行
- **WHEN** 示例输入缺失后按配方恢复
- **THEN** 全部素材校验后示例可准备和短预演；失败不覆盖正确素材
