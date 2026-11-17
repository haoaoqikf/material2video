# 图表、图示、公式、图标与转场

> **独立工程**：下面的相对导入以作品 `scenes/*.tsx` 为起点。先把所需 `web/src/code-scene/` 参考源码及递归依赖、样式和资源复制到作品对应目录，再在作品 `package.json` 与锁文件声明实际依赖。模板不预装所有组件；不能只改 import，也不解析 `m2v/*` 或读取主项目依赖。

代码场景在普通 React 页面录制，合成转场在 Remotion 层执行。以下内部入口提供可在实际作品中评估的实现。

## 成熟组件调研

1. **明确要做的效果。** 从案例的本片转化与验证预期出发，写清要控制的对象、关键状态、时间输入、相邻镜头及效果成立的条件。
2. **先查内部。** 查本页、[共享动效组件](code-scene-runtime.md#共享动效组件)、`web/src/code-scene/` 的组件与原语、`web/src/scene-film/` 的合成参考、`examples/` 及可用作品中的实际用例。内部已有实现可达到目标时，记录源码或用例及复用范围，直接试用。只满足部分时，列出仍缺的能力。
3. **按缺口查外部。** 合成时序与转场先查 Remotion 官方文档、示例或源码，场景内布局、图形和交互查 React 生态，特定运动机制查可查看实现的开源动画案例。按效果、维护状态、许可、依赖与实际包体、适配工作、本地恢复和时间可控性筛选。优先复用、组合或适配，必要时预计算。仅为成熟方案无法满足的部分自研，并记下原因。
4. **用本片小试。** 用实际文案、数据、画幅和时间输入，在拟用场景与采集或合成链路验证。核对代表状态、完整动作、重复取帧以及适用的乱序取帧或顺序推进，检查资源就绪、实际开销与前后衔接。按问题回到案例目标、实现或选型继续迭代。

在 RESEARCH.md 记录查找范围、采用模块、选择依据、试制覆盖与缺口。采用外部实现时记录来源、固定版本与许可，按[实现手段开放](design-samples.md#实现手段开放)登记依赖与本地资源。DESIGN.md 引用通过试制的方案。

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
