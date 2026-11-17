# 图表、图示、公式、图标与转场

> **独立工程**：下面的相对导入以作品 `scenes/*.tsx` 为起点。先把所需 `web/src/code-scene/` 参考源码及递归依赖、样式和资源复制到作品对应目录，再在作品 `package.json` 与锁文件声明实际依赖。模板不预装所有组件；不能只改 import，也不解析 `m2v/*` 或读取主项目依赖。

代码场景在普通 React 页面录制，合成转场在 Remotion 层执行。以下内部入口提供可在实际作品中评估的实现。

## 成熟组件调研

1. **从镜头方案提取需求。** 按动作与关键状态写清对象、实际内容、时间输入、保持不变的关系和可观察的成立条件。明确每项能力归场景绘制还是合成层，记录需要将哪些数据、坐标或进度交给同一组组件。
2. **先查内部。** 从本页和[共享动效组件](code-scene-runtime.md#共享动效组件)定位 `web/src/code-scene/` 的组件与原语，合成查 `web/src/scene-film/`。再看 `examples/` 及可用作品的实际调用。读源码、调用处和适用测试，核对输入代表什么、由谁控制时间、资源如何就绪。内部实现覆盖需求时记录模块和复用范围，直接小试。只覆盖部分时，写明具体缺口。
3. **按缺口查外部。** 用欠缺的能力和采集约束作检索词。合成时序与转场查 Remotion 官方文档、示例或源码，场景内布局、图形和交互查 React 生态，特定运动机制查可查看实现的开源案例。优先采用、组合或适配成熟实现，必要时预计算。只自研成熟方案仍无法满足的部分，并记录原因。
4. **比较候选。** 给候选同一组本片数据、画幅、时序和观察窗口。先核对效果、数据准确性、时间控制和采集兼容性，列出每个候选能覆盖的需求、待适配处及淘汰理由。对可行候选再比较效果差异、适配工作、维护、许可、实际包体、运行成本和本地恢复。内部组合能达到目标时即可收敛选型。
5. **用本片小试。** 用实际文案、数据、画幅、字体、帧率及拟用的场景采集或合成链路，核对代表帧和覆盖完整关键过程的有序帧与适用量测。重复采集关键帧，按所用模式核对顺序推进或纯时间乱序取帧，检查资源就绪及实际开销。失败时根据观察回到镜头方案、实现或选型。

在 `RESEARCH.md` 记录所查模块和来源、需求覆盖与缺口、候选取舍、试制结果和选型依据。采用外部实现时记录来源、固定版本与许可，按[实现手段开放](design-samples.md#实现手段开放)登记依赖与本地资源。`DESIGN.md` 引用通过试制的方案。

### 示例：30 年复利增长

接续[案例调研的镜头方案](reference-video-analysis.md#示例30-年复利增长)，先把「建立对比 → 揭示分离 → 展示规模」落实到可检验的组件需求。

| 镜头阶段 | 从镜头提取的需求 | 如何核对 |
|---|---|---|
| 建立对比 | 两组共用坐标映射和年份进度，颜色与名称绑定组别。揭示到第 10 年后留出阅读时间。 | 同一帧的两条线截止在同一年，停留时的两个读数都取自第 10 年。 |
| 揭示分离 | 两条线沿实际年份一起展开，在选定的分离区间停留。轴、线、标签和读数使用同一份数据和同一坐标映射。 | 按实际数据和画面确定分离区间，检查区间前、中、后的年份、曲线末端和读数是否同步。 |
| 展示规模 | 揭示完成后拉远到完整 30 年。每帧对曲线、坐标和关联标注使用同一映射。 | 拉远中两组身份可辨，终值和差额保持稳定，末帧刻度、终点和读数对应。 |

**内部检查。** 先查共享的 [`LinePlot` 和 `Axis`](../../../../web/src/code-scene/motion-components/charts.tsx)、[`chartLinePath`](../../../../web/src/code-scene/chart-geometry.ts) 和[遮罩原语](../../../../web/src/code-scene/motion-components/morph.tsx)，再看 [`compound-connect` 的曲线和刻度用例](../../../../examples/data-evolution/compound-connect/scenes/components/proof-chart.tsx)。`LinePlot` 的普通实线通过 `pathDrawProps` 按各自的 SVG 路径长度揭示。两条线的路径长度分布不同，共用 `progress` 也可能露到不同年份。[Remotion 路径揭示](https://www.remotion.dev/docs/paths/evolve-path)

| 候选 | 比较与决定 |
|---|---|
| 直接用 `LinePlot` 的实线揭示 | 接入简单，保留作对照。若同一帧两条线露到不同年份，就淘汰这个揭示方式。 |
| 复用内部曲线与坐标轴，组合共同裁剪 | 优先试制。用当前年份算出共享横坐标，让完整绘出的两条线在同一绘图区边界截止。坐标轴与标签单独绘制，读数按同一年份取值。拉远时检查裁剪边界、坐标、曲线和标注是否一起更新。 |
| 按缺口引入外部实现 | 若内部组合只剩刻度跳变或标签碰撞，就按该问题查可显式控制的刻度或标签布局。用相同时间输入和画幅比较，确认改善且通过既有数据和采集检查后，再判断是否值得新增依赖。 |

**本片数据与试制。** 沿用[复利示例的数据模型](../../../../examples/data-evolution/compound-interest/scenes/compoundMath.ts)，本金 10,000 元，年收益率 10%，对比收益再投入和取出后留存两组。在位置信息和差额计算里用原始精度，显示按本片口径舍入。下表保留两位小数供核对。

| 年份 | 再投入累计总额 | 取出后留存累计总额 | 差额 |
|---|---:|---:|---:|
| 第 0 年 | 10,000.00 元 | 10,000.00 元 | 0.00 元 |
| 第 10 年 | 25,937.42 元 | 20,000.00 元 | 5,937.42 元 |
| 第 30 年 | 174,494.02 元 | 40,000.00 元 | 134,494.02 元 |

用作品实际画幅、帧率、字体和采集链路，取第 0 年、第 10 年、实际分离区间、拉远中段及第 30 年的帧，再核对覆盖完整关键过程的有序帧与适用量测。重复采集同一关键帧，使用纯时间采集时再乱序取帧，核对年份、读数、裁剪边界和镜头位置一致性。比较标签在实际显示尺寸下能否读清，并记录资源就绪、画面问题和采集开销。共同裁剪是根据源码推导的优先候选，实际采用结论以试制结果回写。

## 来源与取舍

| 能力 | 来源/固定版本 | 许可与取舍 |
| --- | --- | --- |
| 点列曲线 | 已有 [D3 shape](https://d3js.org/d3-shape) 3.2.0 | ISC；复用既有依赖，替代共享/风格/金融重复几何；金融取样、轴和时序继续由类型负责 |
| 图示布局 | [ELK.js](https://github.com/kieler/elkjs) 0.12.1 | [EPL-2.0](../../../../docs/licenses/elkjs.txt)，npm 元数据亦列 GPL 备选；使用随包 EPL 文本。安装体积约 8.2 MB，不等于成片包体；只在图示入口需要布局时加载 |
| 数学排版 | [KaTeX](https://katex.org/) 0.19.1 | [MIT](../../../../fonts/licenses/MIT-KaTeX.txt)；20 个 WOFF2 共 259792 字节，全部本地恢复，不使用 CDN |
| 按需图标 | [Lucide React](https://lucide.dev/) 1.68.0 | [ISC](../../../../docs/licenses/lucide-react.txt)；安装目录约 38 MB，不等于场景产物，只使用静态命名导出 |
| 合成转场 | [Remotion transitions](https://www.remotion.dev/docs/transitions/) 4.0.526 | [Remotion License](../../../../docs/licenses/remotion.txt)，不是 MIT；与项目其他 Remotion 包完全同版本 |

继续复用已有成熟实现，没有引入第二套布局渲染框架、动画引擎或图标动态字典。相较重写全部样式，库只承担几何/布局/排版，作品与风格保留构图、颜色、文字与运动判断。未逐帧验证的第三方自走动画不自动获得 pure-time 资格。

## 统一曲线

从作品 `../src/code-scene/chart-geometry` 导入 `chartLinePath(points, curve)`、`chartAreaPath(points, baseline, curve)`；点是 `[x,y]`，支持 `linear`、`monotone`、`step`、`catmull-rom`。无效数值切断路径。`catmull-rom` 使用均匀参数与端点重复，保留暗场风格的切线语义；金融使用 D3 单调曲线，维持不过冲语义，精确控制点不承诺与旧算法相同。

## ELK 图示

从 `../src/code-scene/diagram` 导入 `layoutDiagram`、`Diagram` 与 `DiagramLayout`。异步布局只在资源准备期执行一次，得到结果后再 `ready()`；帧内只改变 `progress`。结果可保存为作品的 JSON，再作为普通本地数据导入，避免重复布局。

```tsx
import {useEffect, useState} from 'react';
import {useSceneContext} from '../src/code-scene/context';
import {layoutDiagram, Diagram, type DiagramLayout} from '../src/code-scene/diagram';

export default function Scene() {
  const {ready, elapsedSeconds} = useSceneContext();
  const [layout, setLayout] = useState<DiagramLayout | null>(null);
  useEffect(() => {
    layoutDiagram([{id: 'a', label: '原因'}, {id: 'b', label: '结果'}],
      [{id: 'ab', source: 'a', target: 'b'}], {direction: 'RIGHT', seed: 1}).then(setLayout);
  }, []);
  useEffect(() => {if (layout) ready();}, [layout, ready]);
  return <div style={{position: 'absolute', inset: 0, background: '#101724'}}>
    {layout && <Diagram layout={layout} progress={Math.min(1, elapsedSeconds)}/>}
  </div>;
}
```

最多 500 节点、2000 边，节点默认 220×96；四个方向 RIGHT/LEFT/DOWN/UP，默认间距 48、种子 1。必须为长文字预留尺寸；默认标签不自动换行/截断。`renderNode` 接收节点，可返回 SVG 自定义内容；自定义文字、避让字幕与风格仍由作者负责。不要在每帧或渲染函数内调用布局。

## 公式与字体

采用 `math.tsx` 时同时携带 `math-fonts.ts`、字体资源导入声明和本地 KaTeX 依赖；20 个字体的登记、许可与恢复配方落到作品 `fonts/registry.json`、许可目录和恢复脚本，目标保持 `src/assets/math/` 与源码引用一致。按作品 README 安装依赖并执行字体恢复；缺失、漂移或未声明的依赖须失败，字体二进制不入库，不能借主项目安装目录或 CDN。

```tsx
import {MathFormula, ensureMathReady} from '../src/code-scene/math';
// 在组件 effect 中等待；字体与排版样式全部就绪后才调用场景的 ready()。
useEffect(() => {void ensureMathReady().then(ready);}, [ready]);
// 公式进度由作者控制，不使用 KaTeX 自走动画。
<MathFormula tex={String.raw`\frac{P(1+r)^n}{P}`} fontSize={96} color="#f4e9d8"/>
```

`MathFormula` 支持 tex、display、fontSize、color、style。采用 HTML+MathML 排版，关闭 trust，非法命令/公式明确抛错，不开放任意 HTML/外部链接扩展。排版 CSS 随固定依赖读取，font-face 从包中剥离，20 个登记 WOFF2 由就绪函数加载；每页只初始化一次；资源就绪后才调用场景 ready，不把示例片名当作可用性证据。

## 按需图标

```tsx
import {Atom, Factory, ArrowRight} from '../src/code-scene/icons';
<Atom size={96} color="#f4cf67" strokeWidth={1.5}/>
```

该入口静态导出常用对象、方向、设备、人物、科学与财经图标以及 LucideProps/LucideIcon 类型。支持清单见 `web/src/code-scene/icons.ts`；未列名称编译报错，新增时只补静态导出。不提供 `icons[name]`、整库命名空间或联网图标检索，采用该封装时使用静态导出；如直接采用 lucide-react，须在作品声明固定版本、来源和许可并验证。图标内的颜色与尺寸可按帧计算；图标本身不是受控素材署名替代品。

## 通用转场

每个进入幕声明转场，首幕必须 cut：

```json
{"id":"result","transition":"wipe-left","transitionFrames":16}
```

这是一段幕字段示意，完整幕仍须提供 code 入口、内容与旁白数组。`slide-left/right` 表示新画面从右/左进入并推出旧画面；`wipe-left/right` 表示向左/右揭开新画面；`iris` 为中心圆形揭示，`clock-wipe` 为时钟式揭示。cut、fade、crossfade 继续有效。名称、展示类型和方向由 `web/src/transitions.json` 统一登记，独立工程的 Python 与 Web 同读本地副本。

非 cut 使用两幕重叠窗口，总长减去 transitionFrames；默认值、范围与首幕规则见[分镜契约](storyboard-schema.md)。1 帧直接完成，N>1 时 0 帧为起始态、N−1 为完成态。字幕保持全局时间和最上层；局部预演、lookdev 静帧、适用评审 播放器与正式成片共用合成组件。转场只在已有无声片段之间处理，不给作品代码引入 Remotion hooks，不自动添加转场音效。
