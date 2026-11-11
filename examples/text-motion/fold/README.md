# 折叠：一颗珠子改掉一个细胞

33 秒无旁白短片，1920×1080、30 fps，使用本地夜曲画面组件。
选题与九幕结构按外部参考项目已登记的 `fold_C` 分镜表重写；珠子、红细胞与镰刀都由本文件的
绘制原语自行构造，不复制上游 `film.js`、GIF/JPG 或画面。

本示例属于已登记自有样片的教学重写；普通作品的方法借鉴与素材使用边界见[参考分析与素材边界](../../../.agents/skills/material2video/references/reference-video-analysis.md#素材使用边界)。示例实现和练习可复用，不据此声称新作品的实际表达已通过独立评审。

## 外部方法来源

本示例的方法参考 [HeyChengC/vibe-knowledge-film](https://github.com/HeyChengC/vibe-knowledge-film)，既有登记固定在提交 `62d51508aad00003dc6209afa80c4b5dc540de59`（2026-10-13），原登记最近来源核对为 2026-10-27；本次文档归并未重新核验上游。方法与代码按原登记 MIT 范围参考，媒体、贴图、字体及第三方资产分别核验；不复制受限媒体，也不据此授权其他作品。采用源码与递归依赖归本工程，普通作品的来源、版本和许可仍自行记录。

## 它讲什么

血红蛋白 β 链第 6 位氨基酸从谷氨酸换成缬氨酸，会让一组血红蛋白在脱氧时互相粘成长杆，
从里面把红细胞顶成镰刀形。

- 观众看完应能说出：**错一颗珠子，能改掉一个细胞的形状。**
- 最难讲清的关系：一颗氨基酸的改变，如何经由「折叠 → 表面黏点 → 长杆」变成宏观形状改变。
  它被放进第 5–8 幕当作连续的一段来验证。

## 一个世界，一台摄影机

这是本片的结构核心，不是修辞。

世界坐标分两层：**珠层**（珠距 31.5、单珠半径 14、折后一团半径约 197）与
**细胞层**（红细胞半径 250 像素），用 `RHO = 66` 换算。全片只有一条相机时间轴
（`painter.cameraAt`），缩放跨度约 150 倍：

| 幕 | 大致尺度 | 观众看到什么 |
|---|---|---|
| 01 珠 | 细胞全景 → 珠层 | 一颗红细胞，推进去，里面是一串珠子 |
| 02 错 | 珠层，再推近 | 前十二颗珠子与它们的字母 |
| 03 形 | 珠层 → 细胞全景 | 一路拉远，珠子退成细胞里的一片点，同一轮廓弯成镰刀 |
| 04 问 | 细胞全景 | 镰刀停住 |
| 05 折 | 珠层 | 珠串折成一团，氧分子落进中间的小窝 |
| 06 黏 | 珠层 | 错的那颗露在表面，鼓成黏点 |
| 07 杆 | 珠层，拉远 | 九团依次接上，连成一根长杆 |
| 08 顶 | 细胞全景 | 拉回细胞，长杆从里面把细胞顶弯 |
| 09 结 | 细胞全景 | 镰刀停住，一行出处 |

**幕与幕之间没有黑场**：黑场只在全片开头与结尾各一次。每幕都暗一下会变成九张插图的翻页感。

## 时间线

| 场景 ID | 帧 | 内容 | 画法 | 画面文字 |
|---|---:|---|---|---|
| `chain` | 0–132 | 你的血里，有一条血红蛋白链 | 红细胞显形 → 推进 → 珠串逐颗亮起 | 血红蛋白 β 链 |
| `mutation` | 132–252 | 第 6 颗，E 换成了 V | 十二颗珠子与字母，第 6 颗翻面变红 | 第 6 颗 |
| `sickle` | 252–378 | 整颗细胞跟着弯了下去 | 拉远，同一轮廓连续弯成镰刀 | 红细胞 → 镰状细胞 |
| `question` | 378–450 | 一颗珠子，怎么能做到？ | 设问：镰刀静止漂浮 | — |
| `fold` | 450–576 | 它先折起来，才抓得住氧气 | 珠串卷成密团，氧分子落进小窝 | O₂ |
| `sticky` | 576–684 | 脱氧后，错的那颗露在外面，会粘住下一个 | 表面那颗玫红珠子鼓出并脉动 | 黏点 |
| `rod` | 684–780 | 脱氧状态下，一个接一个连成长杆 | 九团从主团向两端依次接上，每个落位发声 | — |
| `push` | 780–876 | 2.7 亿个血红蛋白，把细胞撑弯 | 回场：同一轮廓再弯一次，内部排开长杆 | 2.7 亿个血红蛋白 |
| `closing` | 876–990 | 一颗珠子，改掉了一个细胞的形状 | 只上字：镰刀停住 | L. Pauling 1949 · V. Ingram 1957 |

九幕里两幕基本不画新东西（`question`、`closing`），约五分之一的时间留给观察。
画面大标题只写短概念（「一串珠子」「第 6 颗」「弯下去」），完整句子交给屏幕字幕承担，
两者不重复。

## 声音

参考片是声画一体的。本片用既有的 `soundtrack.effects`（`assets/sound-sources.json`
登记的是确定性合成音效，不是第三方素材），音效帧号直接对准画面动作：

| 事件 | 幕 | 帧 | 音效 |
|---|---|---:|---|
| 数珠子 | `chain` | 6 起，每 5 帧 | `tick` ×12 |
| 第 6 颗翻面 | `mutation` | 40 / 44 | `flip` + `thud` |
| 细胞弯下 | `sickle` | 70 | `thud` |
| 折成一团 / 氧分子落点 | `fold` | 60 / 100 | `shimmer` + `thud` |
| 黏点鼓出 | `sticky` | 30 | `tick` |
| 分子接上 | `rod` | 28 起，间隔 6 帧 | `thud` ×8，主团保持在原位，其余团落位时发声 |
| 细胞被顶弯 | `push` | 60 | `thud` |
| 收尾 | `closing` | 10 | `chord` |

## 事实与示意

- 146 = β 珠蛋白成熟链的氨基酸数。
- 第 6 位谷氨酸（E）→ 缬氨酸（V）= 镰状细胞突变，即 HbS。
- 2.7 亿 = 一个红细胞里血红蛋白分子的大致数目（数量级）。
- 来源：L. Pauling 等 1949 年指出镰状细胞贫血与血红蛋白异常有关；V. Ingram 1957 年确定
  第 6 位氨基酸替换。这一行作为片尾出处出现在画面上；完整引用与来源保留在本文件。

**示意的地方**：真实的血红蛋白由 4 条链组成，本片只画了一条；折叠用的是六角格上一条
走遍 146 个格点的路径（相邻两颗始终挨着），不是真实三级结构；镰刀由单位圆盘连续
映射成形，是二维近似；分子与细胞的大小比例经过压缩（`RHO = 66`）。完整来源与上述边界
保留在本文件。

折叠布局不是手摆的，而是由 `tools/gen_layout.py` 生成并先断言关系：第 6 颗落在右侧
凸点（knob），左侧留凹口（notch），中间两个相邻空腔（cavity）放氧分子；两团接合时
`pitch < 2R`，前一团的凸点卡进后一团的凹口，格点集合不重合。生成结果 `scenes/layout.json`
随仓库提供，场景加载时还会再检查一次长度、邻接、knob 与接合间距。

## 制作与校验

相机与几何布局的临时副本练习见[修改练习](HOWTO.md)。

```powershell
uv run python fonts/fetch.py
uv run python examples/text-motion/fold/tools/gen_layout.py
uv run m2v validate --project examples/text-motion/fold
uv run m2v prepare --project examples/text-motion/fold
uv run m2v lookdev --project examples/text-motion/fold --sheet 9
uv run python tests/tools/style_reference.py fold
uv run m2v render --project examples/text-motion/fold
```

产物写在作品目录下的 `outputs/`，该目录已被 `.gitignore` 忽略，不入库。
`outputs/style-reference.md` 保留本例历史制作的指标对照与并排基准；后续参考借鉴见[参考分析](../../../.agents/skills/material2video/references/reference-video-analysis.md)，不要求重新填写该报告。

## 已知限制

- 这是风格示例，不是完整评审过的交付作品：没有核心样片、全片粗片与最终终审记录。
- 折叠与长杆的分子排布是示意；不声称还原真实三级结构。镰刀是二维参数域近似。
- 画布文字使用包内登记的宋体族（`Vibe Night Serif`）；`prepare` 会对屏幕字幕与源码字面量
  做严格缺字检查，字体缺失时明确失败。
- 屏幕字幕为单行 28 字以内的短句；长于画面标题的句子已拆成两幕。
- **没有英文斜体字幕行**：参考片在中文下方有一行斜体英文，本项目「画面注释从紧」倾向不加。
  这是有意的偏离，不是遗漏。

## 原生试制入口

本例可用现有场景入口验证最小网页采集（教学检查不等于本例已经完成新独立评审）：

先把现有 storyboard.json 第一幕的 content.props 保存为作品内 sample-props.json，再运行：

```powershell
uv run m2v sample capture --project examples/text-motion/fold --entry scenes/fold.tsx --props sample-props.json --duration-seconds 1 --frame 15
uv run m2v sample serve --project examples/text-motion/fold --id <采集ID>
```

参数决定当前局部效果；正式选案仍须提供实际目标、独立盲看与同轮对照，再通过 `sample deliver`。完整操作见[网页原生样品](../../../.agents/skills/material2video/references/design-samples.md)。已有全片分镜、声音及正式渲染保持原有入口，生成媒体不入库。

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
