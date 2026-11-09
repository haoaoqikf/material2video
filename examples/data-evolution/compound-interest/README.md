# 复利

## 当前采用与候选

继续用户持续目标“按照方案c 以完成开发”。C明确为7da3eccd17b94728a5427e1cb17988d8第7帧薄荷绿手写方向；后续暖纸/钴蓝/赤陶三图仍保留为未选候选，记录见[图片设计](design/editorial-samples.md)，不将第三张赤陶图当作当前C。正式入口为compound.tsx，typography-directions.tsx只保留静态候选比较。

当前按用户选定的方案C完成开发：薄荷绿现场、深绿手写中文、柔和衬线数字和Three.js实体圆片，29秒／1920×1080／30fps／870帧。六段依次建立同样一万、首年收益、去年的收益再生收益、同步分流、按年度余额增长及全白归队；正式源码、29秒完整视频与当前独立验收已完成，状态见[验证](VERIFICATION.md)。

固定10%只作数学演示，无追加投入，不计税费及通胀，非实际回报。1整枚=1,000元，分数按面积开方缩放且保留年度尾数；米白为资本、金色为当年收益、暗金为已取留存。第30年取走组40单位，再投入组约174.5单位（158.631白+15.863金）；结果不加总额、差额或单位图例。结尾16金对象变白、保持175个绘制对象和174.494单位，不称175,000元。

无旁白、无旋律。原创环境床8秒进入，64个触感事件声从分镜事件定位，声音配方可本地恢复，不覆盖旧资产。背景和反射为真实三维材质，文字为本地字体，没有整图贴面。源码、分镜、字体登记、许可及恢复配方入Git；媒体与字体二进制不入库。

## 当前原生试制

当前沿用户明确选定的薄荷绿方案C完成全片，实际目标为样品7da3eccd17b94728a5427e1cb17988d8第7帧。代表性试制和无字检查直接调用同一正式MintFilmView，前5秒对应8–13秒核心，后段对应18.4–24.8秒增长与结果；接缝不是正式转场。

```powershell
uv run m2v sample capture --project examples/data-evolution/compound-interest --entry scenes/capital-motion-trial.tsx --props design/motion-trial-props.json --duration-seconds 11.4 --frame 6 --frame 45 --frame 96 --frame 140 --frame 165 --frame 210 --frame 254 --frame 341
```

此前新增的暖白/深蓝/朱红字体候选保留为未采用探索，原媒体和Git 223f0300保留，当前typography-directions.tsx保留后续未选的三方向静态比较；相关通过与失败按原范围保留，不代表已将C改为朱红或其他方向。新源码须以当前采集和完整候选验收，历史通过不能外推。

## 重建

全部接触、生长、归队与年度节拍声明在storyboard.json的events，场景与声音共用事件ID。改分镜后重新prepare，验证当前受影响窗口与最终完整候选，不沿用旧视频通过。

后续重制按[素材选择规范](../../../.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)判断：本片的数量、收益归队与再投入过程适合代码精确合成，无需为视频优先额外寻找外部素材；如新增真实外部画面，再执行视频优先、图片补位。本说明不改变现有作品与评审状态。

```powershell
uv run python examples/data-evolution/compound-interest/assets/fetch.py
uv run m2v validate --project examples/data-evolution/compound-interest
uv run m2v prepare --project examples/data-evolution/compound-interest
uv run m2v preview --project examples/data-evolution/compound-interest --start-seconds 8 --end-seconds 13
uv run m2v render --project examples/data-evolution/compound-interest
uv run m2v qa --project examples/data-evolution/compound-interest
```

成片位于 `examples/data-evolution/compound-interest/outputs/video.mp4`。目录与项目 ID 为 `compound-interest`；不提供旧五选择兼容入口。

- [制作设计与参考迁移](DESIGN.md)
- [数学口径、素材与声音来源](SOURCES.md)
- [验证与制作状态](VERIFICATION.md)

环境床与事件音按 [固定配方](assets/recipe.json) 恢复，已有摘要不符文件拒绝覆盖。视频、声音和评审图片为派生产物，不入库。最终制作结论以VERIFICATION绑定的文件版本为准。

本示例的画面组件与参数保存在本作品 `scenes/`，可独立重建。

## 本地运行

本示例是独立工程，可以直接在作品目录运行，也可以由 `m2v` 委托同一入口：

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
pnpm run validate
pnpm run build
pnpm run render
```

字体缺失时把文件放入 `M2V_FONT_CACHE` 或 `fonts/.cache/`，再执行 `uv run python fonts/fetch.py`；摘要不符会拒绝覆盖。媒体与音效按 `assets/` 配方恢复。环境与恢复细节见[独立基础模板说明](../../../templates/standalone/README.md)。
