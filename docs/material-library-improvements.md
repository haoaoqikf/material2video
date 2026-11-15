# 素材收集整理改进记录（2026-11-15）

本轮按“覆盖 → 检索 → 组织 → 速度与来源”顺序实施。模型环境准备见[推理环境恢复记录](material-runtime-readiness.md)；完整操作契约见[素材手册](../.agents/skills/material2video/references/material-sourcing.md)。本页报告已实现行为和实际验证，不代表正式作品视觉终审。

## 已实现行为

| 范围 | 当前行为 | 边界 |
|---|---|---|
| 长素材覆盖 | 帧预算分布到完整时间轴；OCR/视觉缩减预算时也分布选择，采样策略进入索引身份 | 稀疏采样仍可能错过短动作，实际范围与预算警告可见 |
| 增量收集 | 流式遍历；成功项按原字节摘要及有效库对象复用，不消耗新的获取预算；单件失败隔离 | 重复扫描仍需遍历并读摘要；未变化坏件须显式重试，遍历不可达区域报告部分覆盖 |
| 检索 | 来源标题/描述可作为原文语义输入；分数与背景对照共同筛选；同图多通道合并 | 来源文字不证明画面出现，动作/身份保持 unknown；可以零命中 |
| 组织 | 标签、收藏、主题集合、移除与过滤，进程重启后保留 | 独立组织表，不改来源许可或媒体身份 |
| 相似建议 | 按完整向量空间分组，组员直接满足与代表的相似度 | 只读建议，不合并来源或删除文件；条目与比较内存有预算 |
| 统一浏览 | 显式多库本地页面，缩略图、来源、文字/标签/收藏/集合筛选 | 每库默认显示 200 件、最多 2000；页面仅筛选已显示数据，非联邦语义检索 |
| 查询速度 | 单次请求中查询与背景向量按通道复用，先排除不兼容索引 | 缓存不跨请求；首次模型加载仍有成本 |

未改变 project v3、storyboard v9、正式媒体 schema、作品运行时与既有网络边界，没有新增依赖或模型权重。

## 覆盖与准确性实测

- 819.766667 秒真实 NASA 素材，6 帧预算选到 0.5、160.016667、330.166667、490.433333、658.166667、819.266667 秒，13.412 秒完成，后段不再因前缀截断漏掉。
- 502 件实际 PNG 文件：首轮获取 500、第二轮获取 2 并复用 500、第三轮全部复用；获取总次数 502。另测损坏项、不可读区域、失败项预算推进、同大小/同修改时间的内容变化，以及库对象缺失后的重采。
- 固定 12 条中英查询，分为 6 条 calibration 和 6 条 validation，查询与正例在本轮分数查看前登记。按 calibration 的实际分数选择文本最低余弦 0.78/背景差值 -0.015，视觉最低余弦 0.035/背景差值 0，统一记录策略版本。
- 在分数筛选层，calibration 两通道指定正例均保留 4/4；无对象负例文本 1/2 全空、视觉 2/2 全空。validation 两通道指定正例均保留 5/5、负例 1/1 全空，12 条查询均未保留彩条。这里不是 Top-K 整体精确率，也不将其他相似图片一概判错。
- 实际工作库建立来源文本索引后，中文厨房查询通过英文原文召回厨房图，text+visual 联查排除彩条。同一图片的文本和视觉证据合成一项，保留各自依据，不重复占用 Top-K。
- 原版与 JPEG quality 50 重编码厨房照片具有不同字节摘要，实际视觉索引将两者放入同一相似建议组；原件和两条来源关系均保留。
- 两库 20 件素材的真实 Chromium 浏览检查通过：搜索、标签、收藏、集合筛选，无页面异常、无远端请求，可见缩略图正常解码，无横向溢出。

小样本与模型背景对照无法保证所有题材准确；文本校准负例仍存在弱候选，动作近邻与身份需要继续实际核对。原有较大题材评测保留在[素材工作层评测](material-acquisition-evaluation.md)，不被本轮较小验证替换。

## 查询性能

同进程预热两种模型后，对同一工作库 5 件媒体执行相同查询。对照使用提交 `3bbc2c4d` 的检索实现，并在两侧采用相同的最终无时间证据合并，以单独观察查询编码复用；最终候选逐字段一致。RSS 每 0.05 秒采样，为进程内存近似，不含系统缓存，也不是独占机器的统计基准。

| 项目 | 优化前 | 优化后 |
|---|---:|---:|
| 文本 / 视觉编码批次 | 4 / 5 | 1 / 1 |
| 热态总耗时 | 11.221 s | 2.620 s |
| 采样进程峰值 RSS | 2783.7 MiB | 2783.8 MiB |
| 最终候选 | 2 | 2，内容一致 |

这次单样本热态约为 4.28 倍速度；不宣称内存下降或任意规模同等加速。独立冷 CLI 进程含导入、权重核验与加载为 15.687 秒、采样子进程树峰值 2792.4 MiB。修复同图证据合并之前另一次对照为 9.708/1.996 秒，原始记录也保留，不能混为同一状态。

## 来源逐站验证

沿现有受控 discover/fetch 入口执行，未更换网络策略、读取日常浏览器会话或配置新凭据。

| 来源 | 本轮实际结果 |
|---|---|
| Commons | `artemis` 图片搜索成功；首个发射照片下载在 8 MiB 预算下明确拒绝，显式增加至 32 MiB 的一次重试遇连接失败；本轮下载 limited，保留此前成功记录 |
| NASA | 图片搜索与下载通过，Artemis 标志 JPEG，194952 字节、1528×1424，实测探测有效 |
| Pexels 公开直链 | JPEG 下载通过，50094 字节、640×431；未启用 Pexels API，视频直链未在本轮重测 |
| Internet Archive | 公开图片搜索返回连接失败；下载未执行，不把失败写成零命中 |
| YouTube | 搜索被受控公开地址策略拒绝；下载未执行 |
| B站 | 固定 worker 未返回可用媒体条目，代码为 unsupported-source；具体平台端原因未确证，下载未执行 |
| Pixabay | 当前未配置 Key，not-tested |
| 抖音/小红书/微博/西瓜 | 本轮没有实际分享链接，not-tested，不宣称稳定下载 |

以上状态只代表本次有限尝试，不代表网站永久可用或不可用；搜索成功也不代表所需画面、身份或许可已核实。

## 使用入口

在已取得媒体的显式库里，先用 `list --json` 获取实际媒体 ID；下面的 `media-id` 须替换为实际值。需要语义/视觉索引时沿[模型恢复说明](material-runtime-readiness.md)准备依赖与权重。

```powershell
uv run --locked --extra index m2v author assets library list --workspace outputs/my-materials --json
uv run --locked --extra index m2v author assets library annotate --workspace outputs/my-materials --media media-id --tag 厨房 --collection 口播实拍 --favorite yes
uv run --locked --extra index m2v author assets library similar --workspace outputs/my-materials --similarity 0.96 --max-items 1000
uv run --locked --extra index m2v author assets library browse --workspace outputs/my-materials --out outputs/material-library-view
```

增量收集使用 `library scan --dir DIR --recursive --max-files 500`；`hasMore` 为真时重复同一命令。不同内容或对象失效会重采，未变化的失败项用 `--retry-failed` 显式重试。多库浏览重复添加 `--library OTHER_WORKSPACE`，只读取这些显式工作库；相似分组需要先建立视觉索引。

## 验证与剩余风险

针对性验证覆盖 collection、library CLI、indexing、source text、retrieval、query cache、organization、store，以及正式导入的直接调用节点；未运行全仓回归。真实长片、模型推理、冷热对照、来源逐站与浏览器筛选分别实际执行。现有一个 Windows symlink 创建权限节点跳过；没有用它代替 junction 或其他路径节点。

本机原始证据位于忽略的 `outputs/material-collection-dev/`：`long-video-coverage.json`、`retrieval-quality.json`、`similarity-real.json`、`browser-verification.json`、`query-performance.json`、`cold-performance.json`、`sources-smoke.json`；媒体、权重、截图和缓存不入库。浏览入口为该目录下 `library-view/index.html`。

主代理代码复核 **91/100，非独立审查**。逻辑上保持来源/媒体不可变、失败可见、向量空间隔离及观察未知；性能上扫描仍有摘要 I/O，相似比较最坏平方但分块且有上限，查询编码从按媒体重复改为按请求复用。未完成大规模并发、对抗性文件竞态、全题材准确率或 Intel 加速验证；平台受限项仍受限。上述均为明确边界，不作为已实现能力。
