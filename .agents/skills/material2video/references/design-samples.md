# 网页原生设计样品

本页维护实现、采集和交付操作。研究见[研究与试制](stage-research.md)，品质和审核职责分别见[视觉复核](visual-review-rubric.md)与[审核政策](review-contract.md)，机器字段见[工具协议](review-protocol.md)。

## 完成条件与持续打磨

原生样品 v2 使用作品自身的构建、字体资源、宿主和受控时钟，不需要完整分镜、旁白或全片准备。主工具只复核来源、实际配置和媒体绑定，不分发第二套采集实现；本地也可运行 pnpm run sample。

static 只生成网页和选定关键帧，不编码视频；motion 另生成完整局部视频。关键帧必须独立盲审及同轮实际目标对照通过，动态用途还须完整过程独立对照通过，适用必改关闭后才能交付。静态通过只授权静态范围；技术成功、候选最好、截图完成和投入时间不替代实际品质。

fail、insufficient、缺失、失效或降级自审均不可交付。持续研究、实现、查看、比较与修复，不设主动工作时长、候选数或总轮次上限；两轮无改善换实质方案或修复机制，保留原失败，按[唯一循环](production-workflow.md)继续。阻塞或中断保留未完成，不能以探索稿结束。

用户只要求先看图片时，交付通过的原生静帧及参考与覆盖范围；纯静态无需视频，不擅自制作整片。AI 图片边界见下节。

## 实现手段开放

以所选视觉目标决定实现，优先检索并采用、组合或改造成熟的外部组件、开源项目、代码示例、模型、材质、Shader、WebGL/WebGPU、Canvas/SVG、建模工具、离线计算及自研方案。已有 SDK、当前依赖名单、熟悉程度和手写方便程度不能成为品质上限。只自研成熟方案无法满足的必要缺口，记录具体原因；不要求穷举候选。先评估成熟外部方案，已有内部实现满足目标时优先复用；需要扩展就扩展，不因预设技术栈降低目标。

研究记录说明实际来源、版本、许可、维护情况、安装及最终包体、适配成本、资源加载、时间控制、网页与正式采集兼容性。自主时钟、随机状态、物理模拟和异步布局可在适配后受控推进，或预计算为本地数据；不能未经验证宣称逐帧确定。可以用顺序采集，不强迫所有组件达到 pure-time。仅本片使用的组件和视觉参数留在作品内，跨作品能力才考虑进入主项目参考源码；不为“允许一切手段”盲目安装全部候选。

直接 npm 导入登记在作品自己的 `package.json` 与锁文件中：每包使用精确版本，并在作品材料中记录 HTTPS source、license 与实际采用依据；构建器只从作品安装目录解析，未声明、缺失或版本不符会明确失败。新包不需要修改共享白名单。场景打包显式使用脚本内 tsconfigRaw，不隐式发现作品或父目录 tsconfig；作品内相对导入与已声明包名为运行时解析入口，编辑器自定义别名不会自动进入视频构建。加载器 `loaders` 可按扩展名登记 file/binary/text/json/dataurl，不可覆盖 JS/TS 编译器；默认支持本地模型、二进制、WASM 和 Shader 文件，具体第三方运行时仍须实际验证。CSS 导入随场景构建与采集。

外部资源必须本地可恢复、许可可用，进入来源台账和输入摘要；不以远程脚本、CDN 或实时 API 作为正式采集前提。必要的工具、环境、字体和资源在资源准备期就绪后才 `ready()`。保持作品路径边界和既有素材/字体恢复规则。

## AI 图片的边界

AI 图片可以辅助构思、风格讨论和参考研究，须明确标识来源；不能直接作为交付图片、正式样品或视觉基线，也不能把整图贴进网页后加缩放、推拉、视差或粒子就声称核心设计已经实现。核心主体、构图、数据关系及承诺的运动须由网页场景实际构建；记录采用的真实素材、模型、纹理及其用途。必要外观素材不得取代要验证的主体与过程。

作者在技术检查中实际查看源码和素材，排除整图包装与无来源资产；独立视觉评审继续隔离源码和设计理由。采集凭据验证实际构建、来源及产物绑定，不能自动鉴别一切 AI 图片，也不自动判断审美。不得声称通过采集命令就完成了这两项判断。

## 最小采集到交付

只需有效 project.json、作品 scenes/ 下的实际入口、可选参数和验证窗口。运行环境、资源及字体须就绪，详见[独立工程](../../../../templates/standalone/README.md)。

```powershell
uv run m2v sample capture --project <作品> --entry scenes/core.tsx --kind static --duration-seconds 3 --frame 30 --frame 75
uv run m2v sample serve --project <作品> --id <采集ID>
uv run m2v sample review --project <作品> --id <采集ID> --purpose keyframe --targets <目标.json>
```

目标文件只维护实际参考和中性条件；reference 路径相对 outputs：

```json
{"references":["refs/quality.png"],"conditions":["原始要求：整体采用选中画面的空间与形体语言。","整体品质参考：主体尺度、空间层次与表面完成度；不采用品牌字形。"]}
```

capture 默认 static，至少一帧；motion 至少两帧。选帧为幕内索引，省略取末帧。时长只限定验证窗口，无统一创作时长；顺序模式推进必要前序状态，只保存指定静帧，不为静态编码。serve 提供同一 bundle 的受控预览，控制条在画面外；子帧积分及 SSAA 的最终质感以同次采集媒体判断，不宣称实时预览逐像素相同。

capture 成功写 outputs/samples/<ID>/，包含网页、静帧、适用视频、capture.json、关键帧请求及适用过程请求。源码、参数、实际可达依赖、字体、资源、配置和产物均绑定，变动后重采；不得手改凭据。采集及交付在 Windows 发布后恢复继承权限并自检。

sample review 自动派生全部媒体窗口、来源和显示尺寸，生成只读隔离包及包外空白报告模板／任务。按[隔离执行](subagent-review.md)实际创建独立代理，导入真实盲报告后自动建同轮目标包：

```powershell
uv run m2v review import --project <作品> --file <真实盲报告.json>
uv run m2v review compare --project <作品> --blind-id <当前盲报告ID>
uv run m2v review import --project <作品> --file <真实对照报告.json>
uv run m2v sample deliver --project <作品> --id <静态采集ID> --blind-id <盲报告ID> --comparison-id <对照报告ID> --basis <具体选案依据>
```

需要动态时使用 --kind motion 采集，关键帧双评仍只包含同源图片，再审核完整过程：

```powershell
uv run m2v sample review --project <作品> --id <动态采集ID> --purpose process --targets <过程目标.json>
uv run m2v review import --project <作品> --file <真实过程对照报告.json>
uv run m2v sample deliver --project <作品> --id <动态采集ID> --blind-id <关键帧盲报告ID> --comparison-id <关键帧对照报告ID> --process-id <过程报告ID> --basis <具体选案依据>
```

过程默认直接独立对照；例外盲审按审核政策提供 --blind-reason，随后按同轮对照执行，deliver 使用过程对照报告ID。缺完整过程、目标、来源、显示范围或存在必改时拒绝交付。静态不得填写未采集的过程资格。

修复重采从原 capture.json 读取帧率、时长和选帧，保持需复查的原用途及范围；每次使用独立ID，不覆盖旧证据。独立失败按原目标关闭；用户明确换目标按 retarget 登记。完整字节与观察条件相同的关键帧可沿[视觉复用](review-contract.md#完整媒体相同的-trial-视觉复用)，当前来源仍复核，过程改变须另审。

deliver 只复制已评静帧与适用视频到 outputs/sample-deliveries/<ID>/，保存依据和报告，不重新渲染。总代理核对实际目标和选案后展示。作品内容、采集及媒体不入库；探索图片通用 pass 不能代替原生采集凭据。
