# 太阳系之旅：两分钟连续旅程

1920×1080、60 fps，当前编排为7200帧／120秒，单幕连续经过十五站。保留地月、土星和奥尔特云三个重点：地月关系、固定环带的视角揭示、外层结构与回望太阳。较174.55秒基线缩短54.55秒（31.25%），通过精简旁白和差异化行程预算完成。

当前成片及四个原生样品已通过适用的技术QA、独立盲看和原目标对照，十四项必改已闭合。制作同时修复素材探测、母版溯源和辉光前数值边界，并优化只读证据校验；当前证据、观察范围和保留限制见[VERIFICATION.md](VERIFICATION.md)。

源文见[article.md](article.md)，可编辑材料见[storyboard.json](storyboard.json)，研究见[RESEARCH.md](RESEARCH.md)，全片与场景设计见[DESIGN.md](DESIGN.md)，来源及发布署名见[SOURCES.md](SOURCES.md)。大小和距离分别压缩，位置并非实时，奥尔特云为推测性结构；声音为艺术设计。

## 独立重建

在本作品目录执行，作品拥有自己的运行时、依赖锁、字体和资源恢复入口：

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
uv run --frozen python assets/fetch.py
pnpm run validate
pnpm run build
pnpm run video:prepare
pnpm run render
pnpm run qa
```

媒体和字体二进制不入库。`assets/fetch.py`按[贴图配方](assets/recipe.json)恢复媒体，并调用声音生成器`--restore`按[固定声音配方](assets/sound/recipe.json)补全缺失项；声音恢复遇到已有摘要漂移时明确失败，不覆盖声音文件或接受新摘要；贴图仍按固定配方及摘要恢复，不接受新摘要。声音只检查可执行`uv run --frozen python assets/sound/generate.py --check`。字体按`fonts/registry.json`恢复，缺失时明确失败；环境细节见[独立基础模板](../../../templates/standalone/README.md)。

## 修改行程与声音

[journey-plan.json](scenes/journey-plan.json)是十五站旁白、实测帧数、目标时点和各段预算的单一编排来源。修改旁白时，先核定完整新文本并按配音契约重新判断音色，更新`project.json`的选择摘要；将新文本同步到`storyboard.json`同ID的`narrationSegments[].text`，同时复核该段claims，不改其他扩展字段。分镜文本是需要显式同步的执行副本：生成器不会自动覆盖旧文本，漏同步会明确失败。随后在作品目录执行：

```powershell
uv run --frozen python scripts/measure-narration.py
node scripts/generate-paths.mjs --merge
node scripts/check-motion.mjs
uv run --frozen python assets/sound/generate.py
pnpm run video:prepare
```

普通声音生成命令属于作者重新登记，会写出音轨及新配方；固定版本恢复必须使用`--restore`或`assets/fetch.py`。量测脚本实际合成并记录十五段旁白，不代写音色选择理由。生成器校验文本、音色、语速与语音参数，过期或超预算时失败；`--merge`保留claims和扩展材料，文本不一致时拒绝静默替换。无`--merge`时只在outputs写提案。

真实相机按绝对帧无状态求值；逐帧诊断检查有限数值、穿模余量、转向、加速度和主体尺度，`observation=not-evaluated`表示技术量测，不代表审美通过。原生试制通过`m2v sample capture`采集，读取正式分镜及完整动作窗口；设计与评审范围见场景文档。本轮不使用存量`render-rough.py`或`render-risk.py`作为制作入口。

## 管理入口与验收

在仓库根也可委托同一作品运行时：

```powershell
uv run m2v prepare --project examples/spatial-3d/solar-system-journey
uv run m2v render --project examples/spatial-3d/solar-system-journey
uv run m2v qa --project examples/spatial-3d/solar-system-journey
uv run m2v status --project examples/spatial-3d/solar-system-journey --history --json
```

文中独立终审为历史证据。重新验收按[现行审核策略](../../../.agents/skills/material2video/references/review-contract.md)执行。生成媒体、网页采集和评审包位于本作品outputs，不入库。旧版清单及38项原字节材料保留在`outputs/remake-baseline-20261110/`；旧MP4及原溯源旁车曾被误删，已在受保护基线目录重建并正式登记，原字节与重建材料明确区分，详见验证记录，不覆盖历史结论。

## 站点与实现

太阳、水星、金星、地球、月球、火星、谷神星、木星、土星、天王星、海王星、冥王星、柯伊伯带、日球层顶、奥尔特云。各站旁白ID为`<body>-line`，身份与顺序保留在行程和分镜中。

画面由本作品`scenes/`中的Three.js／React Three Fiber／Drei场景绘制。名称与核心结论保留，重复信息板及整排列站导航已精简；`BODIES`中的`kind`与`distance`保留对象资料，当前不渲染。配乐与少量音效为原创合成CC0，音乐重点窗口由当前分镜派生。

本例启用的PostFX没有ToneMapping效果；`look.exposure`及镜头`exposure`虽连接renderer属性，当前不渲染为曝光变化。现用明暗由光照、材质和实际后期调色控制，不能只修改EV就宣称画面已改变。

## 许可证

本示例的原创代码、文档和文稿采用 [MIT 许可证](LICENSE)。第三方纹理、档案及另行许可的原创图像和声音见[第三方声明](THIRD_PARTY_NOTICES.md)。
