# 图表、图示、公式、图标与转场

> **独立工程口径**：新作品不解析 `m2v/*`。下文出现的 `m2v/code-scene...` 表示主项目参考源码中的模块；采用时把所需源码复制到作品 `src/code-scene/`，并改为作品内相对导入（例如 `../src/code-scene/context`、`../src/code-scene/painter`）。作品在自己的 `package.json` 与锁文件中声明第三方依赖，不读取主项目依赖登记。

代码场景在普通 React 页面录制，合成转场在 Remotion 层执行。按需选择下面入口，保留画幅、字体就绪、逐帧与来源边界；现有实现满足目标时优先复用；需要更合适的组件时允许扩展、组合或改造，按[实现手段开放](design-samples.md#实现手段开放)调研、登记并实际验证。此处列出的组件不是许可上限。

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

从 `m2v/code-scene` 导入 `chartLinePath(points, curve)`、`chartAreaPath(points, baseline, curve)`；点是 `[x,y]`，支持 `linear`、`monotone`、`step`、`catmull-rom`。无效数值切断路径。`catmull-rom` 使用均匀参数与端点重复，保留暗场风格的切线语义；金融使用 D3 单调曲线，维持不过冲语义，精确控制点不承诺与旧算法相同。

## ELK 图示

从 `m2v/code-scene/diagram` 导入 `layoutDiagram`、`Diagram` 与 `DiagramLayout`。异步布局只在资源准备期执行一次，得到结果后再 `ready()`；帧内只改变 `progress`。结果可保存为作品的 JSON，再作为普通本地数据导入，避免重复布局。

```tsx
import {useEffect, useState} from 'react';
import {useSceneContext} from 'm2v/code-scene';
import {layoutDiagram, Diagram, type DiagramLayout} from 'm2v/code-scene/diagram';

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

先在仓库 `web/` 执行 `pnpm install`，再从仓库根执行 `uv run python fonts/fetch.py`。公式字体的源包文件和恢复目标都登记在 `fonts/registry.json`；恢复时核对版本、字节数与摘要，二进制不入库。独立场景打包器在引用公式入口时验证目标，缺失或漂移明确失败。

```tsx
import {MathFormula, ensureMathReady} from 'm2v/code-scene/math';
// 在组件 effect 中等待；字体与排版样式全部就绪后才调用场景的 ready()。
useEffect(() => {void ensureMathReady().then(ready);}, [ready]);
// 公式进度由作者控制，不使用 KaTeX 自走动画。
<MathFormula tex={String.raw`\frac{P(1+r)^n}{P}`} fontSize={96} color="#f4e9d8"/>
```

`MathFormula` 支持 tex、display、fontSize、color、style。采用 HTML+MathML 排版，关闭 trust，非法命令/公式明确抛错，不开放任意 HTML/外部链接扩展。排版 CSS 随固定依赖读取，font-face 从包中剥离，20 个登记 WOFF2 由就绪函数加载；每页只初始化一次。规范示例 dark-proof 的指数排版已使用该入口。

## 按需图标

```tsx
import {Atom, Factory, ArrowRight} from 'm2v/code-scene/icons';
<Atom size={96} color="#f4cf67" strokeWidth={1.5}/>
```

该入口静态导出常用对象、方向、设备、人物、科学与财经图标以及 LucideProps/LucideIcon 类型。支持清单见 `web/src/code-scene/icons.ts`；未列名称编译报错，新增时只补静态导出。不提供 `icons[name]`、整库命名空间或联网图标检索，作品/风格不能直接 import lucide-react。图标内的颜色与尺寸可按帧计算；图标本身不是受控素材署名替代品。

## 通用转场

每个进入幕声明转场，首幕必须 cut：

```json
{"id":"result","transition":"wipe-left","transitionFrames":16}
```

这是一段幕字段示意，完整幕仍须提供 code 入口、内容与旁白数组。`slide-left/right` 表示新画面从右/左进入并推出旧画面；`wipe-left/right` 表示向左/右揭开新画面；`iris` 为中心圆形揭示，`clock-wipe` 为时钟式揭示。cut、fade、crossfade 继续有效。名称、展示类型和方向由 `web/src/transitions.json` 统一登记，Python 与 Web 同读。

非 cut 使用两幕重叠窗口，总长减去 transitionFrames；默认值、范围与首幕规则见[分镜契约](storyboard-schema.md)。1 帧直接完成，N>1 时 0 帧为起始态、N−1 为完成态。字幕保持全局时间和最上层；局部预演、lookdev 静帧、适用评审 播放器与正式成片共用合成组件。转场只在已有无声片段之间处理，不给作品代码引入 Remotion hooks，不自动添加转场音效。
