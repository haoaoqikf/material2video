# 代码场景（幕级 `renderer`）

通用视频（`general` 类型）的幕可以把自己的画面交给作品目录下的一个 TSX 模块。
受控的图文幕（`graphic`）能表达清楚的，优先用图文幕；代码场景是给需要自由几何、
图表或关系图的幕留的出口。

本文记录模块契约、注入范围、确定性纪律与安全边界。通用视频的分镜结构见
`general-plan.json`（`project.json` 的 `materials.plan` 指向它，见
[目录约定与输出路径](paths-and-outputs.md)）；文章 v5 分镜与本文无关，见
[文章分镜 v5](storyboard-schema.md)。渲染与编码规则见[渲染契约](render-contract.md)。

## 声明

在需要代码画面的那一幕上写 `renderer`：

```json
{
  "schemaVersion": 1,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "scenes": [
    {
      "id": "pipeline",
      "type": "code",
      "durationInFrames": 240,
      "data": { "claim": "整体结果受当前瓶颈限制", "stages": ["取料", "加工", "质检"] },
      "renderer": { "kind": "code", "module": "system-panel" }
    }
  ]
}
```

- `renderer.kind` 固定为 `code`；`module` 是 `scenes/<module>.tsx` 的稳定模块标识，
  匹配 `^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*$`：允许字母、数字、下划线与短横线，
  也允许用 `/` 分子目录（例如 `charts/gauge`），但拒绝 `..`、绝对路径与盘符。
- 模块必须落在当前作品的 `scenes/` 目录内（符号链接逃出该目录会被拒绝），
  并且默认导出 `M2VCodeScene` 组件。
- 一幕要么声明 `renderer`，要么用该幕类型自带的内联图文内容，不能两者都要。
- 只有声明了 `renderer` 的幕才需要模块；同一支作品可以有多个代码幕，也可以混用
  图文幕与嵌入类型幕。模块不参与幕顺序与总时长的决定——那是分镜的真源。

## 模块接口

作品唯一可以导入的项目内部 API 是别名 `@m2v/scene`：

```tsx
import { useCurrentFrame } from 'remotion';
import { type M2VCodeScene } from '@m2v/scene';

const SystemPanel: M2VCodeScene<{ claim: string; stages: string[] }> = ({ scene, progress }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ padding: 'var(--m2v-space-6)', color: 'var(--m2v-text-1)', fontFamily: 'var(--m2v-font)' }}>
      <h1 style={{ fontSize: 'var(--m2v-size-title)' }}>{scene.data.claim}</h1>
      <p style={{ opacity: Math.min(1, progress * 2) }}>{scene.data.stages.join(' → ')} · 第 {frame} 帧</p>
    </div>
  );
};

export default SystemPanel;
```

注入的 props：

| 字段 | 含义 |
| --- | --- |
| `scene` | `{ id, type, data, durationInFrames, kicker? }`；`data` 是本幕 `data` 字段的原样传入 |
| `frame` / `localFrame` | 幕内帧号（相对本幕起点），两者相同 |
| `progress` | 幕内进度 `0..1` |
| `fps` / `canvas` | 输出帧率与 `{ width, height }` 画布尺寸 |
| `theme` | `{ theme: 'dark' }`；当前只有深色一套令牌 |
| `random(node?)` | 按幕标识与节点标识派生的稳定种子随机 |
| `world` / `stage` / `objectStates` / `beats` / `motion` | **当前无内容**：通用视频不提供全片世界、阶段、跨幕对象状态、语义节拍与镜头运动，一律传空值（`beats.current` 为 `null`、`motion.camera.kind` 为 `"none"`、`motion.continuity` 为 `null`、`objectStates` 为 `{}`）。作品不得假设它们被填充 |

组件拿到的帧号是本幕的，不是全片的；没有相邻幕、没有总帧数、没有音频时钟。
这样分镜始终是顺序与时长的单一真源，模块无法形成第二套时间轴。

`@m2v/scene` 还导出 `probe()`（输出稳定的 DOM 探针标记）与
`beatActionProgress`、`compilePath`、`compileReservoir`、`decomposeObjects` 等纯函数
工具。**探针当前没有消费者**：通用视频的代码场景不参与浏览器布局量测，只有
`article-narrative` 的 v5 讲解模板会被量测（它读取的是 `data-m2v-copy` 一类标记，
不是探针）。探针标记仍然可以写，但它现在不会让任何检查通过或不通过。

## 确定性纪律

代码场景的可见状态必须是「分镜 + 已锁定本地资产 + 当前帧号」的确定性函数：

- 禁止挂钟时间、`Date.now()`、`Math.random()`、`setTimeout` / `setInterval`、
  `requestAnimationFrame` 循环、CSS `animation` / `transition`；需要伪随机时用
  `random(node)`，它按节点标识播种，同一帧重复求值、随机寻帧、跨机器渲染都得到
  同一序列。
- 昂贵的路径与流量计算放在模块初始化或 `useMemo` 里，不要每帧重建。
- ECharts 关闭内置动画、由帧号算当前状态；Dagre 只以稳定排序的输入计算布局，
  不随帧重排；Lucide 当静态 SVG 用。

## 依赖与安全边界

依赖白名单（版本由共享前端工程 `web/package.json` 统一锁定，作品不得自行安装或
导入其他 npm 包）：`react`、`react-dom`、`remotion`、`@remotion/*`、`echarts`、
`@dagrejs/dagre`、`lucide-react`、`@m2v/scene`。

以下两条由静态检查在构建前执行，命中即失败并给出文件与位置：

- 源码闸门（`src/m2v/core/code_gate.py`）：白名单外的裸模块引用、指向项目内部的
  别名导入、动态求值/动态导入/Node 内置能力/网络与文件系统访问。
- 确定性策略（`src/m2v/core/source_policy.py`）：挂钟时间、系统随机数、计时器与
  CSS 时间动画。

渲染期还会阻断离线请求。这套边界是项目代码评审措施，不是操作系统沙箱——它只保证
被执行的是项目内受控代码。

## 构建与溯源

构建前由 `web/scripts/gen-active-scenes.mjs` 按当前作品整体重建两个生成物：

- `.gen/active-scenes.ts`：`Record<string, M2VCodeScene>` 静态清单，`GeneralVideo`
  按模块标识取组件，取不到直接抛错（不会静默渲染空白幕）；
- `.gen/active-tailwind.css`：只把**当前作品**的 `scenes/` 与 `assets/` 交给
  Tailwind 类名扫描，其他作品的文件不会被扫进来。

因此作品代码里的 Tailwind 类名必须是**完整字符串**：`className="rounded-xl p-4"`
会进构建 CSS，`const cls = { box: 'gap-6 border-2' }` 这种完整字符串映射也会进，
而运行时拼接的 `` className={`rounded-${size}`} `` 扫描器看不到，构建后可能没有
对应规则、画面静默缺样式。需要按状态切换时，把完整类名写进映射对象再取用。

本地资产（图片/SVG）用打包器导入：`import markUrl from '../assets/mark.png'`。
不要写相对 URL 字符串——那会按页面地址解析成 404。

作品的 TSX、CSS、SVG 与本地媒体都进入可达源码指纹，改动它们会让旧成片与旧准备记录
被判为落后。

## 验证

- `uv run m2v validate --project <目录>`：校验分镜字段，并解析每个代码幕的模块
  （存在性、是否逃出 `scenes/`、语法、默认导出），再跑源码闸门与确定性策略。
- `uv run m2v prepare|preview|render --project <目录>`：走统一入口；模块解析失败
  会在启动浏览器或渲染前报错，并指出幕字段与目标模块。
- 通用视频目前没有逐帧确定性抽帧命令；确定性靠上面的静态检查与源码指纹保证。
