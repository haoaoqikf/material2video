# B 寓言风格包

> 状态：正式风格包 `vibe-fable` 1.0.0。只适用于 `general` 横屏 1920×1080。
> 来源、固定提交与不借清单见[外部参考项目登记](../../.agents/skills/material2video/references/external-reference-projects.md)
> 与[vibe-knowledge-film 制作指引](../../.agents/skills/material2video/references/external-reference-projects.md#vibe-knowledge-film-项目使用指引)。

本包把参考项目的 B 寓言外观转成仓库自己的 TSX 组件与参数。它只提供表现层：不改变视频类型、
材料格式、制作门、审核职责或成片验收条件。选择风格不会自动换肤，场景必须显式导入
组件与资产；不导入时画面与没有风格时相同。

### 可用范围与表现验证

注册与清单说明包可被选择；组件构建与确定性检查说明技术可用；两者均不代表成片表现或同族
验证完成。讲解方法见[讲解设计](../../.agents/skills/material2video/references/explainer-design.md#四种讲解机制的执行方法)，
对象追踪、相机与尺度、过程结果联动及回场仍由作品按需组织，本包不自动生成。示例
`styles/vibe-fable/examples/pigeon/` 是第一份实际应用，它的表达结论只对该示例成立。
事件与取景的可执行示范见[示例练习](examples/pigeon/HOWTO.md)。
技术结果与理解观察分别绑定当前候选和窗口记录；跨例子使用仪表前须核对单位、依据与统一口径，没有依据的精确数值不得呈现为实测。

## 1. 什么时候用

- 讲一个心理或行为机制：起点是动物实验或生活场景，终点是「你该怎么办」。
- 需要角色、场景与有来源的共同尺度，把抽象逻辑演成故事。
- 不适合：抽象概念（数学、逻辑、信息、物理）的当场演示——那更适合 C 夜曲
  （`vibe-night`）；需要大量实拍素材、竖屏或非 `general` 类型。类型或画幅不匹配时
  校验会明确失败，不回退到无风格。
- 旁白要求：清单声明 `requires.narration = "none"`；任一幕含旁白的作品选择本包时
  `validate` 与 `prepare` 明确失败。无旁白作品使用屏幕字幕约定。

## 2. 选择与加载

在作品 `project.json` 声明：

```json
{"style": {"id": "vibe-fable"}}
```

```tsx
import {identity, tokens} from 'm2v/style';
import FableStage from 'm2v/style/components/fable-stage';
import InstinctGauge from 'm2v/style/components/instinct-gauge';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';
```

`identity` 是只读的 `{id, version, fingerprint}`；`tokens` 是只读参数。组件与资产的导入只在
本包、`m2v/code-scene` 与既有批准依赖范围内解析；包外、越界与未登记资产在构建时失败。

本包**不带字体资产**：B 寓言用无衬线，直接使用宿主已注册的 `M2V Sans` 与 `M2V Inter`。
字体仍由场景在 `ready()` 前等 `document.fonts.ready`（宿主已代为等待，直接调用 `ready()`
即可），不存在额外的字体恢复步骤与缺字检查分支。

## 3. 色板与语义

颜色语义全片一致，每种颜色只表达一个含义：

| Token | 取值 | 语义 |
|---|---|---|
| `colors.ink` | `#FFFAEB` | 字幕与主要文字；全片暖白，不随场景漂移 |
| `colors.gold` | `#EEC672` | 规则句与结论；只在需要落点的地方出现 |
| `colors.red` | `#FC593F` | 「超常」的一切：过量的刺激、关键词、仪表红区与计数 |
| `colors.paper` | `#D4CABA` | 卡片与规则卡底色 |
| `colors.paperInk` | `#3A2A22` | 卡片内的深棕文字 |
| `colors.dim` | `#D8CFBF` | 场景说明、年份与地点 |
| `colors.mute` | `#A89F90` | 次要刻度与分隔线；不承载结论 |
| `colors.panel` | `#2B2420` | 仪表面板底；不参与场景配色 |

`scenePalette` 提供五个地点配色（`beach`、`desert`、`desk`、`reeds`、`night`），
各含 `sky` 双色渐变、`ground` 与 `accent`。场景名必须是已登记的键，未登记时组件明确抛错，
不静默退回同一种天空。

## 4. 版式

| 元素 | 位置 | 字号与样式 |
|---|---|---|
| 本能读数仪表 | 左上 `45, 35`，`345×205` | 半圆表盘 0–150，刻度 50/100/150，过 100 进红区并标「超常」；中间读数 78；面板下一行「对象：×××」28 |
| 场景说明 | 左上 `45, 268` | 年份金色 36 + 地点灰色 28 |
| 顶部结论行 | 居中 `y=65` | 34，字距 `0.12em` |
| 对照计数 | 居中 `y=185` | 标签 34 + 数字 90；真实的用暖白，夸张的用红 |
| 引线标注 | 贴对象 | 32，一根细线指向被标注处 |
| 规则卡 | 居中，倾斜 `−1°` | 宽 980，米色纸；标题 46，正文 34 |
| 字幕 | 安全区内居中 | 48，字距 `0.07em`，逐字亮起 |

重要文字与主体避让 `subtitleSafeArea`（由 `useSceneContext()` 提供）。不要把结论塞进字幕区。

## 5. 组件

全部组件由帧号与固定种子驱动，不使用挂钟、`Math.random`、CSS 动画或组件计时器；
同一帧两次独立录制应一致。组件只绘制自己那一层，不自动修改作品画面。

| 组件 | 导入名 | 作用 | 主要参数 |
|---|---|---|---|
| 舞台 | `fable-stage` | 天空渐变、地面与暖色暗角 | `scene`、`width`、`height`、`horizon`、`vignette` |
| 三层视差 | `parallax-band` | 远景、角色层、前景按不同系数平移缩放 | `frame`、`startFrame`、`durationFrames`、`shift`、`zoom`、`far`、`character`、`near` |
| 本能读数 | `instinct-gauge` | 左上仪表，0–150，过 100 红区 | `value`、`startValue`、`object`、`frame`、`startFrame`、`durationFrames` |
| 场景说明 | `scene-note` | 年份 + 地点小字 | `year`、`place`、`x`、`y` |
| 顶部结论行 | `top-line` | 居中一行短句 | `text`、`frame`、`startFrame`、`fadeFrames`、可选 `size`（覆盖默认 34，手机可读性需要时使用） |
| 对照计数 | `counter-row` | 左右两组标签 + 大数字 | `items`（恰好两组）、`frame`、`startFrame`、`durationFrames` |
| 引线标注 | `callout` | 细线指向被标注对象 | `text`、`at`、`label`、`align` |
| 规则卡 | `rule-card` | 米色纸卡，承载结论 | `title`、`body`、`latin`、`frame`、`startFrame` |
| 片名卡 | `title-fable` | 暗场金字与放射线，可带母题 | `text`、`subtitle`、`frame`、`startFrame`、`motif` |
| 屏幕字幕 | `screen-subtitle` | 安全区内单行、逐字亮起 | `items`、`frame`、`safeArea`、`fps` |

```tsx
import FableStage from 'm2v/style/components/fable-stage';
import InstinctGauge from 'm2v/style/components/instinct-gauge';
import SceneNote from 'm2v/style/components/scene-note';
import TopLine from 'm2v/style/components/top-line';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';

const frame = Math.round(elapsedSeconds * fps);
return (
  <div style={{position: 'absolute', inset: 0, width, height}}>
    <FableStage scene="beach" width={width} height={height}/>
    <SceneNote year="1948" place="实验室"/>
    <InstinctGauge value={120} startValue={40} object="鸽子" frame={frame}
      startFrame={30} durationFrames={45}/>
    <TopLine text="食物按时间来，它却碰巧在转圈"/>
    <ScreenSubtitle items={screenSubtitles} frame={frame} safeArea={subtitleSafeArea}/>
  </div>
);
```

- 组件接受可选 `role`/`state`，输出 `data-m2v-role`/`data-m2v-state` 供检查点量测。
  屏幕字幕默认 `role="subtitle"`、`state="visible"`，可直接进 `textPlan` 与 `subtitleRoles` 量测。
  不要把装饰元素全部标成同一角色后期待自动审美判断。
- 本包按 30fps 设计；字幕逐字亮起按传入或上下文里的 `fps` 换算，60fps 作品无需手改帧数。
  其余 `*Frames` 参数按作品实际帧率解释。
- 辉光很克制（`canvas.glow = 0.12`），实心物体不应发白；不提供泛光组件，
  质感来自大色块与柔和渐变的层次，而不是后期特效。

## 6. 角色画法

本包不提供角色组件：每部作品的主角不同，把角色做成通用组件只会得到没有辨识度的剪影。
作品按参考片的做法自行绘制，并遵守以下约束：

- 形体用四五个色块拼成，不描边、不写实；动作只做必要的（走、低头、扑翅、卧下）。
- 主角在开场出现、在片尾回来；中间的例子可以有别的角色，但画法一致。
- 角色动作由帧号驱动，不使用 CSS 动画或计时器；同一帧两次录制一致。

## 7. 无旁白屏幕字幕约定

无旁白作品在 `content.props.screenSubtitles` 声明屏幕文字，由作品场景在字幕安全区内自绘。
安全区必须从场景上下文取得，不要在作品或 tokens 里复制一份几何：

```tsx
const {subtitleSafeArea} = useSceneContext();
<ScreenSubtitle items={screenSubtitles} frame={frame} safeArea={subtitleSafeArea}/>
```

```json
{
  "screenSubtitles": [
    {"startFrame": 12, "endFrame": 108, "text": "1948 年，一只饿着的鸽子被关进箱子"},
    {"startFrame": 129, "endFrame": 258, "text": "墙上的食槽，每 15 秒打开一次"}
  ]
}
```

约定：

- 每项含 `startFrame`、`endFrame` 与非空 `text`；窗口落在本幕时长内，帧号按作品 fps 解释。
- 单行、不换行、无底板、水平居中；超出可用宽度时拆句，不靠缩字号硬塞。
- 必须落在 `subtitleSafeArea` 内；共享字幕层在无旁白时为空，两者不重叠。
- 有旁白作品**不得读取**该字段，字幕继续由共享字幕层从旁白派生；`validate` 会拒绝同幕既有
  旁白又声明 `screenSubtitles`。
- 它不进入 `subtitleCues`，但会进入检查点证据链：组件默认输出 `data-m2v-role="subtitle"`，
  合同可用 `textPlan` 断言文本与时间窗，并用 `measurement.subtitleRoles` 检查安全区、单行与
  溢出。未声明这些断言的检查点仍需帧序列与独立评审补足。

## 8. 制作规则

1. 一句话对应一个当场可演的动作；遮住文字仍能读出讲解。
2. 每场一幅插画，不套统一标题框；视觉差异来自场景本身，而不是换版式。
3. 一把有依据的尺子贯穿全片：只在口径一致、能够比较时显示读数；没有测量依据就改用定性状态或有来源的时间、次数。
4. 色块与柔和渐变出质感；不描边、不写实、不加装饰性特效。
5. 推拉只做慢速单方向移动，三层视差量不同；同一幕内不硬切。
6. 约五分之一的时间不画字，留给动作与观察；这是创作参考比例，不是验收阈值。
7. 数字必须可复算：屏上出现的数值、单位与基准在作品材料中可追溯。
8. 画面注释按[项目约定](../../AGENTS.md#修改规则)：从紧、小字、次要位置，不遮挡主体、数据与屏幕字幕。
9. 声音走现有音轨编排；本包不渲染音频资产，不新增音效库。

## 9. 验收

- 注册：`uv run m2v styles --json` 返回 `vibe-fable` 的 id、version、description、types 与 frames。
- 准备：`prepare` 记录风格身份与全包内容指纹；包内容变化使旧准备失效，需重新 `prepare`。
- 示例：`styles/vibe-fable/examples/pigeon/` 用本包完成 33 秒示例，`validate` 通过并可完整渲染。
- 确定性：同一帧两次独立录制一致；不因运行时刻或随机数变化。
- 回归：各风格 `examples/` 中的六个固定示例、金融类型、共享字幕层与既有无风格作品不受影响。

## 10. 边界

- 不复制参考项目的 `engine/`、`film.js`、GIF/JPG、角色、画面或文案；示例按已登记样片的
  选题与分镜重写，实现与媒体自绘。
- 不提供 A 鎏金暗场（上游已不将其作为可选外观）；不新增视频类型或 CLI 命令。
- 不改变分镜 schema、共享字幕层、制作门、审核轮次与导出门禁。
- 版本升级按不兼容处理：只维护升级后的当前契约，不保留旧版兼容分支或迁移工具。

### 教学重写与普通作品借鉴

本包关联的教学示例按已登记自有样片的选题与机制重写，不直接复制外部媒体或整段源码。普通作品仍须针对自身内容设计，不照搬教学示例或上游样片的整套分镜与文案；边界见[外部参考项目与转译指南](../../.agents/skills/material2video/references/external-reference-projects.md#视频参考)。技术可用、制作证据闭环与实际表现验证分别记录，组件通过不等于成片通过。

## 运动人格

- **Playful**：落定用 `backOut`，入场用 `easeOutCubic` 带少量回弹，画面内移动用 `easeInOutCubic`；回弹只在落点收住，不让整体持续抖动。
- 签名动作是角色的弹跳与形变：挤压拉伸服务动作，错峰按镜头节拍确定，装饰性弹跳不替代信息推进。
- 时长按帧换算后写进作品 `DESIGN.md` 的运动计划；通用时长、缓动与编排方法见[运动设计](../../.agents/skills/motion-design/SKILL.md)。
