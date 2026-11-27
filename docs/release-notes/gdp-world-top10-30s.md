# 全球 GDP 前十 · 30 秒交付记录

## 媒体

成片为 MP4，30.000000 秒、900 帧、30 fps、1080×1920，H.264 High、yuv420p、BT.709，单视频流，无音轨。文件长 3,644,881 字节，SHA-256 为 `82ba57f69c4c312dbea73c4f5220b9a05e9a969895d6146070e81f1f8734cf94`。仓库标准输出与命名副本的摘要一致。[30 秒成片](../../outputs/gdp-world-top10-30s-1080x1920.mp4) · [仓库标准成片](../../videos/data-evolution/gdp-world-top10-60s/outputs/video.mp4)

作品覆盖 1980–2024 年全球名义 GDP 前十，以中日第二名交接为中段。分镜三个区间分别为 `[0,420)`、`[420,630)` 和 `[630,900)`。帧号从零起，时间为帧号除以 30。[作品设计与完整状态表](../../videos/data-evolution/gdp-world-top10-60s/DESIGN.md)

## 顶部与榜位

| 帧 | 年份 | 顶部与榜位 | 进度线与切法 |
| --- | --- | --- | --- |
| 419 | 2007 | 美国第一，14.75 万亿美元 | 满格 |
| 420 | 2008 | 日本第二，5.11 万亿美元 | 归零，顶部硬切，0 过渡帧 |
| 462 | 2009 | 左日本 02／5.29，右中国 03／5.19 | 2009 归零，双卡站定 |
| 533 | 2009 | 左日本 02／5.377、右中国 03／5.376，榜上日本第二 | 满格，蓝色信号 |
| 534 | 2010 | 左日本 03／5.385、右中国 02／5.394，榜上中国第二，差额约 0.01 万亿美元 | 归零，卡上名次、领先色和两条榜行同帧硬切，0 过渡帧 |
| 558 | 2010 | 中国 6.19，日本 5.76 | 首次到达 2010 年确值 |
| 629 | 2011 | 中国第二，8.65 万亿美元 | 满格 |
| 630 | 2012 | 美国第一，16.25 万亿美元 | 归零，顶部硬切，0 过渡帧 |
| 870–899 | 2024 | 美国第一，29.30 万亿美元。末年十行使用确值 | 30 帧内由空至满，末帧满格 |

卡片内部在 2008 年尾展开，在 2011 年尾收束，使用短程平移、尺寸和透明度变化。差额针随数值跨零。其余时段顶部使用当帧第一名，并从榜首行读取名称和金额。常规读数保留两位小数，第 530–537 帧的中日金额至少显示三位。相邻榜位和同屏差额需要更多精度时，相关读数同步增加小数位。交接段单卡的单位位于主金额下方。

## 数据与源文件

以联合国 SNAAMA 现价美元为主序列，留档含世行指标 NY.GDP.MKTP.CD 的交叉核对。2024 年第十名按联合国为巴西。世行交叉核对的第十名为俄罗斯。现有 720 个观测原值全部保留。全量对照发现第 36–42 帧在 1982 年内应由尼日利亚占第十槽，补入已留档的 45 个尼日利亚观测。更新后序列共 765 个观测，SHA-256 为 `0cb9d9e4d230919f185101a1f5abd99a2106de7218657e4dd21284db9b461a37`。[数据口径与来源](../../videos/data-evolution/gdp-world-top10-60s/RESEARCH.md)

尼日利亚旗帜由 Flagcdn 提供，该站下载页列为公共领域。场景使用本地 PNG，SHA-256 为 `6076be1144054cb5cecb1fe958b5f0bbfd23d6a1894146300c60fc54a09b15ca`。[旗帜 PNG](https://flagcdn.com/w80/ng.png) · [许可声明](https://flagpedia.net/download)

渲染只读取本地打包数据、国旗和字体，三场共用年度时钟、未舍入排序、榜尺与固定十槽。用 `Math.round(elapsedSeconds*fps)` 取幕内帧，再加场景起帧取得全片帧号。每年首末帧的细线分别为 0 和 1。资产就绪检查每场只执行一次，逐帧工作量为固定候选数的一次排序和十行绘制。

基线试制采集与交付 MP4 的 SHA-256 均为 `db7899f54fc7056b81cca97a5137323d62b27f525c72ea6b7077f12ab5986c81`。[试制采集](../../videos/data-evolution/gdp-world-top10-60s/outputs/samples/3ab164c483c3446eae59b68ffff5032c/sample.mp4) · [试制交付](../../videos/data-evolution/gdp-world-top10-60s/outputs/sample-deliveries/3ab164c483c3446eae59b68ffff5032c/delivery.json)

## 实测

- 联合国全量留档逐帧核对 900 帧前十榜序、未舍入金额、单位换算、45 年行程及共用榜尺。作品类型检查、`m2v validate`、`m2v prepare` 及场景打包通过。相对链接和 JSON 解析检查通过。
- 最终 MP4 完整解码通过。检查 9,000 个榜槽，每帧有十个旗、名次、国家和读数区域。相邻帧差中无重复，画面信号无黑场。45 年进度线均由空至满，420 像素宽的最大线性量测偏差为 1.20 像素。盘心旗帜信号定位美国第一名仅在 0–419 与 630–899 帧展示。[解码及量测输出](../../outputs/gdp-top10-30s-validation/encoded-accepted.log) · [仓库技术 QA](../../videos/data-evolution/gdp-world-top10-60s/outputs/qa.json)
- 整片复核范围包括开榜、第 35–43 帧历史末位、第 164/165 帧历史实体交替、419/420 顶部接入、451/462 展开、530–537 中日换位、558 与 588 年度确值、610–631 收束及回切、834/835 德日换位、869–899 收束至 2024。第 614–622 帧逐帧观察，金额和单位与盘面保持分离。2024 榜值从第 870 帧留到第 899 帧，末帧细线满格结束。[整片复核登记](../../outputs/gdp-top10-30s-validation/whole-film-accepted.json)

代码复核 94/100。时间、榜位、显示精度、条长和尺标由相同的逐帧状态派生，静态国旗解码在场景挂载时完成。排序和显示精度检查使用固定观测集，每帧绘制十个榜槽。扣分来自额外随机定位的截图一致性限制，实际顺序复测、类型检查、编译与成片信号记录均提供证据。

## 独立评审与返工

首次关键帧盲审与同轮目标对照均为 `fail/reject`。18 个窗口中第 534 帧两国各显示 5.39，无法直接印证「中国领先 0.01」；第 615 帧圆弧经过金额单位，影响 393 与 1080 宽度下的分辨。两份原报告均已封存。修复后用顺序受控时钟抽取原生第 420、533、534、615、629 帧复查，核对过零数差和单位位置。[初次盲审导入](../../outputs/gdp-top10-30s-validation/first-blind-import.log) · [初次对照导入](../../outputs/gdp-top10-30s-validation/first-compare-import.log) · [返工静帧采集](../../outputs/gdp-top10-30s-validation/repair-sequential.log)

第二轮盲审和对照确认前两处修正，另指出第 610 帧两位小数金额相减和差额不一致，第 835 帧德日换位后都显示 4.25，均为 `fail/reject`。统一显示规则后，第 610 帧为中国 8.197、日本 6.254、领先约 1.94，第 835 帧为德国第三 4.254、日本第四 4.250。全片 9,000 个读数的顺序都可直接核对，210 帧交接中的同屏金额与显示差额均匹配。最多用到五位小数，最长读数七个字符。[第二轮盲审导入](../../outputs/gdp-top10-30s-validation/second-blind-import.log) · [第二轮对照导入](../../outputs/gdp-top10-30s-validation/second-compare-import.log) · [显示精度校验](../../outputs/gdp-top10-30s-validation/amount-proof.log)

第三轮盲审与对照确认上述数字，并指出第 615 帧 8.32 的末位仍贴着差额弧亮边，两份报告均为 `fail/reject`。把金额放大推迟到盘面收向右侧后，单位跟随金额下移。原生预检查看第 610 帧及第 614–622 帧，第 615 帧的数字、单位和差额弧之间出现连续暗面。[第三轮盲审导入](../../outputs/gdp-top10-30s-validation/third-blind-import.log) · [第三轮对照导入](../../outputs/gdp-top10-30s-validation/third-compare-import.log) · [收束预检前半](../../outputs/gdp-top10-30s-validation/spacing-1.png) · [收束预检后半](../../outputs/gdp-top10-30s-validation/spacing-2.png)

最终正式关键帧盲审和同轮目标对照均为 `pass/adopt`。两次均实看 393 与 1080 宽度的 18 个帧窗，第 0、36、165、419、420、451、462、533、534、558、588、610、615、629、630、835、870、899 帧。对照另查看四个登记参考。两处顶部边界和中日换位在相邻帧同步更新；第 610、615、835 帧分别核对差额、图文留距及精确排名。保留意见包括 451/610 的过渡淡影、615 的上区留白，以及 588–615 的部分半弧画面中，右侧指针端点难辨。亮卡、差额文字和榜单可读。[最终盲审报告](../../videos/data-evolution/gdp-world-top10-60s/outputs/production/f483812337234d458a575b06cc587961/reports/904b42935ebf82f1cb2d8d5e1fba2fc12f47f5f76e90450d5ace89e91451056a.json) · [最终目标对照报告](../../videos/data-evolution/gdp-world-top10-60s/outputs/production/f483812337234d458a575b06cc587961/reports/49add10f5c271315cba44ab466048fa0bb57d5880ad19b752b3224df8ade664f.json)

`pure-time` 随机定位附加验证仍未通过，第 615 帧正、倒序截图为 53.98 dB，低于该模式的 60 dB 阈值。当前源码两次独立顺序采集的第 610 帧和第 614–622 帧共十张 PNG 摘要均相同。900 帧显示读数在正序、倒序计算下也逐项相同。正式分镜采用顺序受控采集。[随机定位复测](../../outputs/gdp-top10-30s-validation/spacing-pure-time.log) · [顺序重复采集摘要](../../outputs/gdp-top10-30s-validation/spacing-sequential-hashes.log)

## 仓库状态

本轮前三对报告登记的六条必改已用最终独立双评关闭。60 秒版原有的两条必改仍开放，包含第 1175–1176 帧及第 1320 帧等旧版窗口，所绑定的旧媒体已经缺失。它们使当前周期继续显示「制作未完成」。30 秒版本身的关键帧、技术 QA 和整片复核均通过，正式关键样片按 30 秒门槛豁免。[仓库最终状态](../../outputs/gdp-top10-30s-validation/final-status.json) · [作品问题记录](../../videos/data-evolution/gdp-world-top10-60s/outputs/visual-notes.md)

作品源码、分镜、媒体和机器证据位于 Git 忽略的本地工作目录。版本库跟踪本交付记录。

## 执行记录

```powershell
uv run m2v validate --project videos/data-evolution/gdp-world-top10-60s
材料校验通过

uv run m2v prepare --project videos/data-evolution/gdp-world-top10-60s
已生成准备产物：C:\D_Merged_From_D\project\first-party\material2video\videos\data-evolution\gdp-world-top10-60s\outputs\prepared.json

uv run m2v render --project videos/data-evolution/gdp-world-top10-60s --jobs 2
视频输出：C:\D_Merged_From_D\project\first-party\material2video\videos\data-evolution\gdp-world-top10-60s\outputs\video.mp4
[warning] 旧产物清理未完成：无法确认评审媒体或问题证据引用，未执行清理：正式评审旁车摘要失配，未执行清理
```

```text
ffmpeg full decode PASS: 900 frames, 9,000 occupied ranking slots, 0 black or duplicate frames
year rail PASS: 45 starts <=1 px, 45 ends >=73 px, 900 monotone per-year readings; max linear deviation=1.20 px at 420-wide
419/420: rail=74/0 px, mean absolute pixel difference=5.105, hero=19.964
533/534: rail=74/0 px, mean absolute pixel difference=3.380, hero=8.960
629/630: rail=74/0 px, mean absolute pixel difference=5.237, hero=20.844
533/534: flag difference cross-slot=1.34, same-slot=97.43 (hard cut)
```

```text
keyframes=pass technicalQA=pass wholeFilmReview=pass keySamples=exempt openIssues=2 complete=False
候选已生成，制作未完成
```

最终命令留档包括 [渲染](../../outputs/gdp-top10-30s-validation/render-accepted.log)、[技术 QA](../../outputs/gdp-top10-30s-validation/qa-accepted.log)、[盲审导入](../../outputs/gdp-top10-30s-validation/accepted-blind-import.log)、[目标对照导入](../../outputs/gdp-top10-30s-validation/accepted-compare-import.log)和[交付副本摘要](../../outputs/gdp-top10-30s-validation/deliver-copy.log)。
