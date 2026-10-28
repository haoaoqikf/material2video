# C 夜曲风格包

> 状态：正式风格包 `vibe-night` 1.0.0。只适用于 `general` 横屏 1920×1080。
> 来源、固定提交与不借清单见[外部参考项目登记](../../.agents/skills/material2video/references/external-projects.md)
> 与[vibe-knowledge-film 制作指引](../../.agents/skills/material2video/references/vibe-knowledge-film.md)。
> B 寓言另见 [`styles/vibe-fable`](../vibe-fable/GUIDE.md)；两包单选，不可混用。

本包把 C 夜曲的外观转成仓库自己的 TSX 组件与参数。它只提供表现层：不改变视频类型、
材料格式、制作门、审核职责或成片验收条件。选择风格不会自动换肤，场景必须显式导入
组件与资产；不导入时画面与没有风格时相同。

### 可用范围与表现验证

注册与清单说明包可被选择；组件构建、字体和确定性检查说明技术可用；两者均不代表成片表现或同族
验证完成。讲解方法已写入[讲解设计](../../.agents/skills/material2video/references/explainer-design.md#四种讲解机制的执行方法)，
对象追踪、相机与尺度、过程结果联动及回场仍由作品按需组织，本包不自动生成。
当前试制已存在完整候选和阶段评审，但仍有主体关系、可见因果与参考表现差距；本包不据此声称
原仓库精华完整落地或风格同族通过。后续作品的实际表达按
[视觉复核](../../.agents/skills/material2video/references/visual-review-rubric.md#讲解关系的观察)验证，
不追溯改写已有作品记录。

## 1. 什么时候用

- 无旁白或「字幕即文案」的抽象知识短片：看不见的机制、时间与尺度、一个概念的当场演示。
- 需要近黑底、宋体主体大字、慢推慢移、少量语义色和光点母题的横屏作品。
- 不适合：需要大量实拍素材、角色表演、竖屏或非 `general` 类型。类型或画幅不匹配时
  校验会明确失败，不回退到无风格。
- 旁白要求：清单声明 `requires.narration = "none"`；任一幕含旁白的作品选择本包时
  `validate` 与 `prepare` 明确失败，不静默改用共享字幕层。无旁白作品使用屏幕字幕约定。

## 2. 选择与加载

在作品 `project.json` 声明：

```json
{"style": {"id": "vibe-night"}}
```

```tsx
import {identity, tokens} from 'm2v/style';
import NightBackdrop from 'm2v/style/components/night-backdrop';
import GlowText from 'm2v/style/components/glow-text';
import {loadNightSerif} from 'm2v/style/components/kit';
```

`identity` 是只读的 `{id, version, fingerprint}`；`tokens` 是只读参数。组件与资产的导入只在
本包、`m2v/code-scene` 与既有批准依赖范围内解析；包外、越界与未登记资产在构建时失败。

字体与资产就绪后，**场景**负责调用 `ready()`。组件不会代替场景发就绪信号：无旁白的
`title-night` 在宋体就绪后同步把文字采样成点；若场景在字体前调用 `ready()`，录制会先于
点阵生成开始。推荐写法：

```tsx
const {ready} = useSceneContext();
const [fontsReady, setFontsReady] = useState(false);
useEffect(() => { loadNightSerif().then(() => setFontsReady(true)); }, []);
useEffect(() => { if (fontsReady) ready(); }, [fontsReady, ready]);
```

字体加载失败时不要调用 `ready()`；录制会按超时失败，而不是用系统回退字体交付。

## 3. 色板与语义

颜色语义全片一致，每种颜色只表达一个含义：

| Token | 取值 | 语义 |
|---|---|---|
| `colors.text` | `#F8F9F8` | 主题、对象名称与结论；全片近白，不随情绪漂移 |
| `colors.gold` | `#F8D893` | 发现、调整与结论落点；只在需要落点的地方出现 |
| `colors.ice` | `#64E3F6` | 正常行动、冷光与信息；不做危险或错误提示 |
| `colors.rose` | `#E84B75` | 主观紧张、被注视与被压缩的视野 |
| `colors.violet` | `#8477D0` | 距离、回忆与尚未到达的信息 |
| `colors.coolWhite` | `#CFEAF4` | 普通照明与结构性物体 |
| `colors.muted` | `#8A97A5` | 次要结构标记与刻度；不承载结论 |
| `colors.blood` | `#C8384E` | 血的实体：红细胞本体与血管环境；只作组织，不作强调 |
| `colors.oxygen` | `#FF6A55` | 氧气与结合动作；与 blood 同屏时是唯一的暖红焦点 |

底色 `canvas.background = #010104`，中央光池 `canvas.poolColor = #0B1830`、透明度 `0.62`。
光池、星点与暗角只作环境，不代替讲解主体；不要用光点代替本应可辨认的实物、人物或数据。

## 4. 三区版式

`layout.zones` 给出纵向分区（1920×1080）：

| 区域 | 纵向范围 | 用途 |
|---|---|---|
| 主体区 `subject` | 180–820 | 讲解对象、动作、数轴与核心大字的主区 |
| 字幕区 `caption` | 888–1001 | 参考分区；实际安全区以场景上下文 `subtitleSafeArea` 为准 |
| 四角区 `corner` | 56–1024 | 章节标、必要的署名；小字、次要位置，不争夺焦点 |

重要文字与主体避让 `subtitleSafeArea`（由 `useSceneContext()` 提供，取值来自共享画幅契约）。
主体大字基线取 `type.baseline = 838`，落在安全区上方；不要把结论塞进字幕区。

字号与字距：标题 `type.title = 104`，主体大字 `type.hero = 76`，小标 `type.small = 40`，
屏幕字幕 `type.screenSubtitle = 52`，章节标 `15/22`；字距 `0.14em`，行高 `1.5`。数值来自
`tokens.json`，不在场景里另写一套。

## 5. 组件

全部组件由帧号与固定种子驱动，不使用挂钟、`Math.random`、CSS 动画或组件计时器；同一帧
两次独立录制应一致。组件只绘制自己那一层，不自动修改作品画面。

| 组件 | 导入名 | 作用 | 主要参数 |
|---|---|---|---|
| 星点底 | `night-backdrop` | 近黑底、光池、固定种子星点、暗角与细颗粒 | `width`、`height`、`frame`、`seed`、`stars`、`pool*`、`vignette`、`grain` |
| 光点 | `spark` | 小白核 + 两层色晕，可带十字射线 | `x`、`y`、`size`、`color`、`intensity`、`rays`、`frame`、`seed` |
| 彗尾 | `comet` | 运动方向上的彗核与渐隐尾迹 | `x`、`y`、`angle`、`length`、`width`、`color`、`curve`、`frame`、`seed` |
| 辉光文字 | `glow-text` | 宋体主体大字，字自身辉光 | `text`、`x`、`y`、`size`、`color`、`glow`、`opacity`、`align` |
| 章节标 | `chapter-mark` | 左上编号 + 单字 +（可选）西文 + 细线 | `index`、`character`、`latin`、`x`、`y`、`opacity`、`frame` |
| 点阵片名卡 | `title-night` | 点从散落聚成标题文字 | `text`、`width`、`height`、`frame`、`startFrame`、`durationFrames`、`size` |
| 闪 | `flash` | 短促白场 | `frame`、`startFrame`、`durationFrames`、`peak` |
| 暗一下 | `dip` | 章间黑场呼吸；`holdEnd` 可持续压黑 | `frame`、`startFrame`、`durationFrames`、`peak`、`holdEnd` |
| 数轴 | `number-line` | 带刻度与数值标记的水平轴 | `x`、`y`、`width`、`min`、`max`、`ticks`、`labels`、`marker` |
| 屏幕字幕 | `screen-subtitle` | 无旁白作品在安全区内自绘单行字幕 | `items`、`frame`、`safeArea`、`fps`、`size`、`color`、`role` |

```tsx
import NightBackdrop from 'm2v/style/components/night-backdrop';
import Spark from 'm2v/style/components/spark';
import GlowText from 'm2v/style/components/glow-text';
import ChapterMark from 'm2v/style/components/chapter-mark';
import NumberLine from 'm2v/style/components/number-line';

const frame = Math.round(elapsedSeconds * fps);
return (
  <div style={{position: 'absolute', inset: 0, width, height}}>
    <NightBackdrop width={width} height={height} frame={frame} seed="scene-1"/>
    <ChapterMark index={1} character="暗" frame={frame} startFrame={0}/>
    <GlowText text="夜空为什么是黑的" x={width / 2} y={838}/>
    <Spark x={1180} y={420} size={6} seed="evidence"/>
    <NumberLine x={360} y={700} width={1200} min={0} max={138} ticks={6}
      marker={138} markerLabel="138 亿年" frame={frame} revealFrames={24}/>
  </div>
);
```

- `number-line` 另外导出 `numberLineX(value, {x, width, min, max})`，供作品把同一数值映射到
  坐标；不要在场景里另写一套比例。
- `spark` 另外导出 `sparkCluster(seed, count, area, size)`，生成固定种子的光点参数。
- 组件接受可选 `role`/`state`，输出 `data-m2v-role`/`data-m2v-state` 供检查点量测。
  `title-night` 的 role 是标题包围盒；`comet` 的 role 是沿尾迹的细包围盒；屏幕字幕默认
  `role="subtitle"`、`state="visible"`，可直接进 `textPlan` 与 `subtitleRoles` 量测。
  不要把装饰星点全部标成同一角色后期待自动审美判断。
- 本包按 30fps 设计；`screen-subtitle` 的淡入按 `screenSubtitleFadeMs` 与传入或上下文里的
  `fps` 换算，60fps 作品无需手改帧数。其余 `*Frames` 参数按作品实际帧率解释。
- 辉光优先用文字阴影与径向渐变；不要为每帧新增多层 SVG 滤镜。粒子超过数百个时改用
  canvas 或减少数量，避免 1080p 逐帧录制变慢。

## 6. 字体资产与许可

包内 `assets/NotoSerifSC-subset.ttf` 是 Noto Serif SC 的 GB2312 子集（7542 个字符），
来源 Google Fonts，许可 SIL Open Font License 1.1，全文见 `assets/OFL-NotoSerifSC.txt`。
字体二进制不入库，由[字体仓](../../fonts/README.md)的 `fonts/fetch.py` 恢复；缺失时
`validate`、`prepare` 或 `m2v styles` 会明确失败并提示恢复命令。
清单 `assets.serif` 登记来源与许可；资产通过 `m2v/style/assets/serif` 取得内联 URL。

- 组件用 `loadNightSerif()`（或 `useNightSerif()`）显式加载；字体失败会阻断录制。
- 常用字必须在字体字符映射中齐全；`prepare` 会用包内字体的 cmap 对屏幕字幕与场景字面量做
  **严格缺字检查**（不与其他字体做并集），缺字即失败。试制另用 1920 原尺寸帧复核，不以系统
  回退字体交付。
- 本包不改变全局字体清单 `web/src/assets/fonts.json`，也不改变共享字幕层字体。

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
    {"startFrame": 30, "endFrame": 95, "text": "夜空看起来应该处处是星光"},
    {"startFrame": 100, "endFrame": 168, "text": "但宇宙的年龄是有限的"}
  ]
}
```

约定：

- 每项含 `startFrame`、`endFrame` 与非空 `text`；窗口落在本幕时长内，帧号按作品 fps 解释。
- 单行、不换行、无底板、水平居中；中文不超过 28 字（`type.screenSubtitleMaxChars`），
  超出拆句；字号与基线按 `tokens.type`，颜色用 `colors.text`。
- 必须落在 `subtitleSafeArea` 内；共享字幕层在无旁白时为空，两者不重叠。
- 有旁白作品**不得读取**该字段，字幕继续由共享字幕层从旁白派生；`validate` 会拒绝同幕既有
  旁白又声明 `screenSubtitles`。
- 它不进入 `subtitleCues`，但会进入检查点证据链：组件默认输出 `data-m2v-role="subtitle"`，
  合同可用 `textPlan` 断言文本与时间窗，并用 `measurement.subtitleRoles` 检查安全区、单行与
  溢出。未声明这些断言的检查点仍需帧序列与独立评审补足。

## 8. 制作规则

1. 一句话对应一个当场可演的变化；遮住文字仍能读出讲解。
2. 主体是认得出的东西：字、数轴、光点、可辨识的对象；光点与连线只作底和片名卡装饰。
3. 光只落在需要被看见的地方；辉光克制，大面积柔光用径向渐变。
4. 镜头只做慢推慢移；同一幕内不硬切。跨幕相机必然跳变，需要连续空间时写成单幕多镜。
5. 约五分之一的时间不画字，留给动作、尺度变化或观察；这是创作参考比例，不是验收阈值。
6. 数字必须可复算：屏上出现的数值、单位与基准在作品材料中可追溯。
7. 画面注释从紧：除外部素材署名、口径/方法解释与用户明确要求外，不加装饰文字。
   必要注释用小字，置于次要位置，不遮挡主体、数据与屏幕字幕。`chapter-mark` 的 `latin`
   只用于本来就有语义的英文名，不作气质装饰；年份、出处属于来源与解释，可作小字保留。
8. 声音走现有音轨编排；本包不渲染音频资产，不新增音效库。

## 9. 验收

- 注册：`uv run m2v styles --json` 返回 `vibe-night` 的 id、version、description、types 与 frames。
- 准备：`prepare` 记录风格身份与全包内容指纹；包内容变化使旧准备失效，需重新 `prepare`。
- 试制：一条 30–45 秒、不入库的原创作品，按[参考风格契约](../../.agents/skills/material2video/references/reference-style.md)
  记录八项指标、并排基准与独立冷审结论；`outputs/style-reference.md` 缺任一项视为未完成。
- 确定性：同一帧两次独立录制一致；不因运行时刻或随机数变化。
- 回归：三个固定示例、金融与住宅类型、共享字幕层与既有无风格作品不受影响。

## 10. 边界

- 不复制参考项目的 `engine/`、`film.js`、GIF/JPG、角色、画面与文案；样片只作并排基准，不入片、不入库。
- 不提供角色组件或视差场景（那是 B 寓言的职责）；不新增视频类型或 CLI 命令。
- 不改变分镜 schema、共享字幕层、制作门、审核轮次与导出门禁。
- 版本升级按不兼容处理：只维护升级后的当前契约，不保留旧版兼容分支或迁移工具。
