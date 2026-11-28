## Why

共享音效命令生成的身份与三类独立工程要求的本地生成器不一致。现行主规格也混入了三部旧身份作品的单片要求，容易让制作者误用入口。

## What Changes

- **BREAKING** 移除 `m2v author sounds`。三类工程通过作品自己的 `assets/sound-recipe.json` 和 `setup` 生成或导入音效，并用本地校验、准备和技术检查核验。
- 删除主项目无实际调用的合成、导入和混音副本。主项目创作辅助仍可读取并复核现行音效登记。
- 从主规格撤下《地球夜灯》《劳动权益十件事》《美股市值前十》单片要求，将其完整主规格快照收进本次归档。继续维护随附示例和通用制作契约。
- 将金融、建筑、车辆结构化来源及素材库高级工作流明确为按需工具。维持其独立调用路径。

## Capabilities

### New Capabilities

### Modified Capabilities

- `modular-video-production` 移除共享音效 CLI，保留创作辅助与本地委托。
- `sound-effect-library` 明确音效配方在作品内恢复及复核。
- `earth-night-lights-video` 撤出旧单片主规格。
- `labor-rights-ten-events-video` 撤出旧单片主规格。
- `us-top10-market-cap-silent-video` 撤出旧单片主规格。

## Impact

影响主项目 CLI、声音记录复核、独立工程模板中的回收代码、测试和按需说明。已生成作品和随附示例保留独立运行时快照与原证据。主项目无需读取历史作品材料来维持旧命令。
