# 代码场景（renderer.code）

受控原语表达不了的图表面板、关系图与定制 SVG 图形，可以在**个别幕**上把画面交给
工作级 TSX 模块。这是场景树之上的逃生口，不是替代品：默认每幕仍走场景树，
代码场景只用于原语确实画不出的画面。

本文记录分镜声明、模块契约、确定性纪律与工具链行为。可运行的完整示例见
[`examples/code-scenes/`](../../../../examples/code-scenes/storyboard.json)
（1 幕场景树 + 4 幕代码场景）。

## 1. 分镜声明

```json
{
  "id": "quarter-chart",
  "type": "chart",
  "durationInFrames": 60,
  "data": { "labels": ["Q1", "Q2"], "values": [32, 48] },
  "visualIntent": { "relation": "sequence", "focus": "chart", "composition": "full", "density": "balanced", "tone": "neutral" },
  "renderer": { "kind": "code", "module": "progress-chart" },
  "motions": []
}
```

- `renderer.kind` 省略时是 `"tree"`，该幕走 `sceneTree`；
- `renderer.kind = "code"` 时 `module` 必填：稳定模块标识，指向
  **作品目录下** `scenes/<module>.tsx`（`scenes/` 与分镜同目录，归属规则见
  [目录约定与输出路径](paths-and-outputs.md)）；
- `data` 仍是画面内容的唯一真源，模块拿到的只是它的引用；
- `sceneTree` 与代码场景互斥：声明了 `renderer.code` 的幕不需要（也不读）`sceneTree`；
- `motions` 对代码场景不可用——动效由模块按 `progress` 自行驱动。

## 2. 模块契约

模块放在 `<文章目录>/scenes/<module>.tsx`，默认导出必须是
`A2VCodeScene<Data>`（`React.FC<A2VCodeSceneProps<Data>>`）：

```tsx
import { probe, type A2VCodeScene } from '@a2v/scene';

const ProgressChart: A2VCodeScene<{ labels: string[]; values: number[] }> = ({
  scene, frame, localFrame, progress, fps, canvas, theme, random, beats,
}) => {
  return <div {...probe({ node: 'canvas', schematic: true })}>{/* … */}</div>;
};

export default ProgressChart;
```

props 字段集合是**封闭**的：

| 字段 | 含义 |
| --- | --- |
| `scene.data` | 本幕 `data` 字段原样传入（内容真源在分镜） |
| `scene.id` / `scene.type` / `scene.kicker` | 幕标识与类型（只读参考） |
| `scene.durationInFrames` | 本幕帧数（只读参考：进度已由共享层算好） |
| `frame` | 全局帧号（整片时间轴） |
| `localFrame` | 幕内帧号（本幕从 0 重新计数） |
| `progress` | 幕内进度 `localFrame / (durationInFrames - 1)`，夹在 [0, 1] |
| `fps` | 帧率 |
| `canvas` | `{ width, height }`，与分镜输出尺寸一致 |
| `theme` | `{ theme: 'dark' \| 'light', preset? }`，与设计令牌同源 |
| `random` | 稳定种子随机函数（见 §4） |
| `beats` | 语义节拍状态 `{ current, progress, completed, estimated, active, plan }`；声明分段口播的幕才有内容，其余幕为空时间轴（`current: null`、`completed: []`） |

`beats` 只读：`current` 是当前 beat id（区间外为 `null`），`progress` 是它的局部进度，
`completed` 是已完成的 beat id 列表，`estimated` 表示这是无声估算时间轴，
`active` 是当前 beat 的声明（没有则为 `null`），`plan` 是本幕的完整解析时间轴。
模块**不自己解析字幕、不读音频时钟、不读挂钟**——同一帧永远得到同一份状态。
需要画面变化跟着口播走时用它，而不是拿 `progress` 自己切分幕内时间。

没有相邻幕、没有总帧数、没有第二套时间 API：顺序与时长只由分镜决定。

## 3. 探针协议（体检必需）

代码场景必须暴露最小 DOM 标记，共享契约探针才能读文本、查安全区与溢出、
扫动效；**协议缺失在严格评审里计为错误**：

- 根节点由共享包装器自动打 `data-a2v-scene` / `data-a2v-code-scene`，组件不必重复；
- 需要体检的节点用 `probe({ node, role?, inside?, schematic? })`：

| 标记 | 用途 |
| --- | --- |
| `node` | 稳定节点 id（幕内唯一）；文字要被内容探针读到时**必须**带 `node` |
| `role` | 语义角色，枚举与场景树 `role` 同源：`hero` / `headline` / `title` / `body` / `label` / `caption` |
| `inside` | 容器归属：值是**节点 id**（如 `probe({ node: 'note', inside: 'panel' })`），K8 溢出量测按它解析选择器 |
| `schematic` | 图形/图表容器标记；K 闸门与 M 扫描对它放宽装饰性检查 |

## 4. 确定性纪律

可见状态必须是**分镜数据 + 当前帧号**的确定性函数。禁止：挂钟（`Date.now()`）、
`Math.random()`、计时器、`requestAnimationFrame`、CSS `animation` / `transition`
（值为「关闭」的写法如 `animation: false` 除外）、网络、动态 `import()` / `eval`。
伪随机用注入的 `random`（mulberry32，按场景与节点播种，同帧同序）：

```tsx
const offset = random('dot') * 24; // 同一帧重复求值结果一致
```

值必须是「关闭」形态的动效声明（如把第三方库动画关掉）不违规；真正的时间动效
（非零时长/延迟）静态扫描会报「未适配的 CSS 动画/过渡」。

## 5. 适配器（`@a2v/scene` 提供）

| API | 用途 |
| --- | --- |
| `freezeFrameOption(option)` | ECharts option 展开后强制 `animation: false`、时长 0；配合 `useFrameChart` 使用 |
| `useFrameChart(build, watch)` | SVG 渲染器实例；每帧同步 `setOption`（非 lazy），卸载时 `dispose` |
| `layoutGraph(nodes, edges, config)` | Dagre 稳定布局：输入按 id/边排序后计算，冻结结果；重复 id 或幽灵边直接抛错 |
| `FrameIcon` | Lucide 图标包装：不透明度由 `progress` 驱动，不用 `<use href>` |
| `frameStroke(progress, pathLength?)` | SVG 描边进度：返回 `{ dasharray, offset }` |
| `frameStyle(progress, { opacity, rise, scale })` | 受控入场样式（透明度/位移/缩放） |
| `probe(...)` | 探针标记（见 §3） |
| `createSceneRandom(sceneId)` | 稳定种子随机（Host 内部用它注入 `random`） |

ECharts 纪律：动画必须关（适配器已强制），当前数据由 `progress` 计算；
Dagre 纪律：布局只算一次（不随帧重排），动画只作用于可见状态；
Lucide 纪律：静态 SVG 组件，颜色/透明度由帧号驱动。

## 6. 依赖白名单与资产

- **可用包**（版本由共享工程锁定，不得自行安装或导入其他 npm 包）：
  `react` / `react-dom` / `react/jsx-runtime` / `remotion` / `@remotion/*` /
  `echarts` / `@dagrejs/dagre` / `lucide-react` / `@a2v/scene`（项目内部 API 别名）；
- 导入白名单之外的裸模块：构建前校验失败，报告导入者、包名与位置，且**不会**尝试安装；
- **本地资产**用打包器导入（不要写相对 URL 字符串——那会按页面地址解析成 404）：
  ```tsx
  import markUrl from '../assets/mark.png';
  // <img src={markUrl} />
  ```
  资产文件（`.png` / `.svg` 等）放在作品的 `assets/` 下；
- **Tailwind 类名纪律**：`className` 里的类名必须是完整字符串；按状态切换时写进
  映射对象（构建期静态可发现）。运行时拼接的类名不保证生成（构建不会报错，
  但样式缺失）。作品 `scenes/` 与 `assets/` 会自动加入 Tailwind 内容扫描。

## 7. 安全模型（如实声明）

静态安全门（导入白名单、动态求值、网络 API、Node/进程/文件系统访问、外部 URL）
+ 渲染期离线隔离（Playwright 路由层阻断所有非本地请求，命中即计为错误）+
确定性扫描共同构成**审查边界**。它不是操作系统级沙箱：代码场景模块是**作者自己
编写并入库审查**的代码，不要执行来路不明的模块。断网渲染（离线环境）因此成立。

## 8. 工具链行为

- **静态清单**：构建/预览/渲染前，`web/.gen/active-scenes.ts` 由当前作品重建
  （静态 import + 模块映射），切换作品不残留上一个作品的模块；
- **构建输入指纹**：当前作品可达 TS/TSX/CSS/SVG、本地资产、`.gen/scene-manifest.json`
  与 `package.json`/锁文件全部进入成片溯源；改了任一可达输入，旧成片判「落后」并指名文件；
- **评审**：代码场景与场景树走同一契约页、同一 C/K/M 量测；加 `--check-determinism`
  对每幕收尾帧做同帧重复截图与随机寻帧验收（PSNR ≥ 60 dB），失败计为错误；
- **模块缺失或导出错误**：校验在启动浏览器或打包前失败并指出场景字段与目标模块。
