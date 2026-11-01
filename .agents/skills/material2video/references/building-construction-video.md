# 建筑建造视频专题

本文定义 `building-construction` 类型的材料与画面契约；行为以 [OpenSpec 规格](../../../../openspec/specs/building-construction-video/spec.md) 为准。

## 材料

- `building.json`（v1）：固定 1920×1080 画布与两层框架住宅参数（开间、层高、屋顶、墙厚、基础、场地、门窗洞口）。洞口按所属墙面和层号定义，必须落在墙内。
- `construction.json`（v1）：40 秒级时长、30 fps、连续无重叠阶段和镜头方位。所有阶段首尾相接并覆盖全片。
- `manifest.json`（v1）：外部资产清单；纯程序材质时为空数组。登记资产时必须保存来源、许可、路径与 SHA-256。

## 制作命令

```powershell
uv run m2v init --type building-construction --project <slug>
uv run m2v validate --project videos/building-construction/<slug>
uv run m2v prepare --project videos/building-construction/<slug>
uv run m2v preview --project videos/building-construction/<slug> --start-seconds 10 --end-seconds 16
uv run m2v render --project videos/building-construction/<slug>
```

## 画面与边界

- 16:9 横屏、30 fps、无音轨；程序化等轴测住宅，阶段标签为小字，右下“建造过程示意”为示意边界。
- 构件、墙体洞口、阶段与镜头均按帧确定；同一材料重复准备保持相同构件 ID 与最终几何。
- 不得把组装动画宣称为完整施工工序、结构计算或工程适用性结论；首例为表达示意。
- 作品、媒体与生成候选留在忽略的内容目录，不入库。

## 视觉与运动

- 构图、层级、色彩与字阶判断按 [Frontend Design](../../frontend-design/SKILL.md) 与[视频适配](../../frontend-design/ADAPTATION.md)：等轴测构图的主体占比、阶段标签的小字层级、示意边界标注的次要位置都在其观察方法内判断。
- 阶段推进、构件生长、镜头方位切换的时长、缓动与编排按[运动设计](../../motion-design/SKILL.md) 与[视频适配](../../motion-design/ADAPTATION.md)：构件出现用减速落定，镜头方位切换用两端平滑，匀速升降只在表达需要时显式声明。
- 本页只保留建造特有的材料、阶段与确定性要求，不复述通用视觉或运动理论。
