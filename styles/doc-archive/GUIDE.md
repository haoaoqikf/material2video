# 档案纪录片风格包（doc-archive）

## 可用范围与表现验证

- 适用类型：`general`；画幅：1920×1080；旁白：`none`（无旁白作品）。
- 本包只提供表现层：色板、章节文字、档案媒体框与轻量机制叠加。选择风格不会自动换肤，场景必须显式导入组件。
- 包内不含档案素材、题材文案、分镜或声音；真实素材必须由作品导入并留证。
- 注册成功、组件构建通过不等于成片表达通过；成片仍按现有独立评审与视觉复核验收。

## 1. 什么时候用

适合以**真实档案、实物或历史影像**为主要证据的题材：科技史、人物、事件、机构、考古、新闻回顾。真实素材本身是观看理由，代码只解释照片里看不见的机制。

不适合：没有可留证素材、纯抽象关系、以数据曲线或空间尺度为主的题材；这类题材优先考虑其他风格。

## 2. 选择与加载

```json
{"style": {"id": "doc-archive"}}
```

场景显式导入：

```tsx
import {useArchiveFrame, archiveGradient} from 'm2v/style/components/kit';
import ArchiveFrame from 'm2v/style/components/archive-frame';
import ChapterText from 'm2v/style/components/chapter-text';
import SignalLine from 'm2v/style/components/signal-line';
import Waveform from 'm2v/style/components/waveform';
import NodeLink from 'm2v/style/components/node-link';
import FlashRings from 'm2v/style/components/flash-rings';
import SequenceLinks from 'm2v/style/components/sequence-links';
import CreditBlock from 'm2v/style/components/credit-block';
import SchematicBadge from 'm2v/style/components/schematic-badge';
```

## 3. 色板与语义

| 颜色 | 语义 |
|---|---|
| `text` `#F5F1E8` | 主题、对象名称与结论 |
| `copper` `#DCC49C` | 章节年份、强调与信息线 |
| `coldCyan` `#9FB6CF` | 机制说明、示意标注与次要结构线 |
| `muted` `#C3CDCF` | 别名、单位与辅助识别 |
| `credit` `#E1E7E6` | 片尾署名与许可 |

档案素材保留原生色调，不用高亮装饰覆盖主体。代码机制层必须比档案暗、细、退后，且明确标注示意。

## 4. 版式

- 档案主体占主要画面区域；文字稳定落在左下、左上、右侧或竖排等少数位置，不逐场换模板。
- 中文名称与一句贡献为主信息；陌生英文缩写只在首次出现时作小字辅助。
- 章节文字 `title` 82–116px、`caption` 46px、`year` 31px；手机横屏 393 宽复核。
- 字幕安全区只从场景上下文 `subtitleSafeArea` 取得，不在 tokens 复制。

## 5. 组件

| 组件 | 用途 |
|---|---|
| `archive-frame` | 图片/视频档案铺底：轻微缩放、漂移、去饱和与对比；不覆盖主体 |
| `chapter-text` | 年份、标题、别名、贡献句；五种位置变体 |
| `signal-line` | 沿路径传播的脉冲；表示信号、传播或连接 |
| `waveform` | 轻量波形；表示声音、电信号或连续变化 |
| `node-link` | 节点与连线；表示网络、地图或因果关系 |
| `flash-rings` | 扩散环；克制表示闪光、冲击或事件 |
| `sequence-links` | 成对序列连接；表示编码、配对或序列关系 |
| `credit-block` | 片尾署名与许可；只在片尾集中出现一次 |
| `schematic-badge` | “示意”小标；标出代码解释与真实档案的边界 |

组件只接收媒体、文字、进度、强调色等 props，不内置作品 slug、年份、机构名或章节数据。

## 6. 制作规则

- 不确定性动画一律由帧号或秒数换算，不使用挂钟、`Math.random`、CSS 动画或组件计时器。
- 介质加载完成前不开始绘制；作品在资源就绪后调用 `ready()`。
- 机制叠加必须标注示意，不得伪装成历史实录或真实数据。
- 不用同构标题卡替代档案差异；每段至少改变一种可见变化（主体、构图、尺度、明暗或连接）。
- 片尾署名只出现一次；观众可见文案不出现仓库路径或材料查阅提示。

## 7. 验收

- 场景显式导入组件，未导入时画面与无风格一致。
- 同帧两次录制字节一致。
- 包指纹变化使准备失效；修改示例不改变包指纹。
- 示例作品 `styles/examples/doc-archive/american-science-milestones/` 通过 v8 校验、prepare 与代表性 QA。

## 8. 边界

- 不提供档案素材、许可文本、题材文案或分镜。
- 不提供人物造型、3D 场景或数据图表；这些属于作品或其他风格。
- 不自动换肤，不改变业务计算、制作门或评审职责。
