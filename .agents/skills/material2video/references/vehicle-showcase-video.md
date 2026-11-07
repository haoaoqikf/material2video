# 汽车展示视频专题

本文定义三维空间作品可选的 `vehicle-model` 结构化来源及 `VehicleScene` 场景。作品仍使用 project v2、分镜 v9 和统一制作链路；当前行为以[统一分镜的结构化来源](storyboard-schema.md#结构化来源v9)为准。

在分镜 `sources` 中声明 `{"showcase":"showcase.json","assets":"manifest.json"}` 两个文件角色，幕的 `content.sourceIds` 引用来源 ID；场景从 `m2v/code-scene/sources` 导入 `VehicleScene`。分镜幕时长须与来源一致。模型与贴图留在作品目录，准备时纳入指纹。

## 材料

- `showcase.json`（v2）：固定 1920×1080、30 fps、时长、模型相对路径、车轮节点名、镜头与疾驰效果时间。
- `studio`：必填的影棚资产登记，包含 HDR 环境图、车漆 AO、地面法线与地面粗糙度四张本地贴图的相对路径。
- `manifest.json`（v1）：本地 glTF、二进制、模型贴图与影棚贴图的清单，逐项记录来源、上游提交、许可依据、路径与 SHA-256。
- 模型及其依赖、影棚贴图只放在作品忽略内容目录；准备时把 glTF 的 buffer/image 与影棚贴图内嵌为 data URI，渲染离线运行。
- v1 材料明确拒绝，不提供兼容分支；升级时补齐 `studio` 并重新准备。

## 命令

```powershell
uv run m2v init --type spatial-3d --project <slug>
uv run m2v validate --project videos/spatial-3d/<slug>
uv run m2v prepare --project videos/spatial-3d/<slug>
uv run m2v preview --project videos/spatial-3d/<slug> --start-seconds 0 --end-seconds 4
uv run m2v render --project videos/spatial-3d/<slug>
```

## 画面与边界

- 30 秒、1920×1080、30 fps、无声；暗色影棚、亮灯显现、完整环绕、启动与视觉疾驰。
- **影棚**：HDR 环境图经 PMREM 后驱动车漆、玻璃与金属反射；顶部圆形白色柔光板（中心亮、边缘渐隐）提供画面光源与辉光；HDR 下半球偏暗时用微弱半球光补车下沿。
- **地面**：暗色圆盘与平面反射。每帧用镜像相机渲染低分辨率反射目标，地面着色器按法线贴图扰动、按粗糙度贴图模糊反射，并按菲涅耳与距离衰减混合；不出现网格、灰色测试地面或可见地面边缘。
- **接地**：车底椭圆接触阴影压暗轮下区域；车影与反射是视觉接地的主要依据。
- **镜头**：开场从远处推近，随后完成一圈环绕；侧视角看到车长、前后视角只看到车宽，镜头按视角收放距离以保持主体占比。收束最后 4 秒淡出。
- **车轮**：按 glTF 原始节点名或 three.js 清洗后的名称解析（清洗会移除 `[ ] . : /` 并把空白换成下划线）。环绕阶段车轮静止；启动段（疾驰开始前 3 秒）加速到约 4.5 rad/s，疾驰段升到约 13.5 rad/s，收束段减速。30 fps 下最大约 0.45 rad/帧，低于五辐轮毂的对称周期，不出现频闪或倒转错觉。
- **确定性**：镜头、车轮角度、环境强度、灯板亮度、地面反射与辉光全部是 `frame / fps` 的纯函数；反射目标每帧重渲染，不跨帧累积，乱序取帧应一致。
- 视觉疾驰不是真实道路驾驶；不宣称车辆性能或真实运动。
- 首例 SU7 资产必须来自已核实授权的 `alphardex/su7-replica` 固定提交；授权未落实时不得导入或发布。

## 视觉与运动

- 按[实际画面复核](visual-review-rubric.md)核对车辆识别、车漆反射、必要文字与用户关键目标；影棚参数不能代替实际呈现，构图与风格自主选择。
- 环绕镜头、车辆启动、车轮加速与疾驰的时长、缓动与编排按[运动设计](../../motion-design/SKILL.md) 与[视频适配](../../motion-design/ADAPTATION.md)：环绕是匀速跟踪的合法 `linear` 例外，启动与收束用减速落定，车轮加减速按帧换算而不是按毫秒照搬。
- 本页只保留模型、影棚与确定性契约，不复述通用视觉或运动理论。
