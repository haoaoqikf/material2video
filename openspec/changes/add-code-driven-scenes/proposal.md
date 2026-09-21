## Why

现有场景树只能组合固定原语，能够保证确定性与可校验性，但难以表达独特的构图、定制 SVG、复杂图表和关系布局。项目需要在不开放任意依赖、网络资源或非确定性动画的前提下，允许作品使用受控的 React/Remotion 源码提升视觉多样性。

## What Changes

- 新增作品级代码场景：场景可以选择自由 TypeScript/React 模块，使用 JSX、CSS、Tailwind、原生 SVG 与允许的 TypeScript 表达式绘制画面。
- 保留现有 `sceneTree` 路径，并允许一支作品混用声明式场景与代码场景；`storyboard.json` 继续作为内容、场景顺序和时长的单一真源。
- 建立固定依赖白名单：React、React DOM、Remotion、Tailwind、ECharts、Dagre、Lucide 与项目内部模块；作品不得声明、安装或加载其他 npm 包。
- 新增代码场景模块契约、构建期场景清单、Tailwind 内容扫描、源码指纹与预览/评审/渲染同源要求。
- 新增源码静态闸门与运行期隔离，拒绝网络访问、动态代码执行、Node 能力、非白名单依赖以及破坏帧确定性的时间、随机和动画入口。
- 为 ECharts、Dagre、Lucide 和原生 SVG 规定确定性接入方式，并要求自由场景继续暴露可供现有契约探针和 K/M 闸门量测的 DOM 标记。
- 将 `lucide-react` 作为本次唯一新增的共享前端依赖锁定入库；不允许作品自行扩充依赖集合。

## Capabilities

### New Capabilities

- `code-driven-scenes`: 定义作品级 React/TypeScript 场景、模块接口、依赖白名单、安全与确定性边界、构建和验收行为。

### Modified Capabilities

- `declarative-video-scenes`: 将“所有作品不得维护专属画面源码”调整为声明式场景与受控代码场景双轨共存，同时保持分镜为内容与时长真源。
- `remotion-renderer`: 扩展 composition 的源码发现、静态检查、指纹与离线渲染范围，使作品级代码场景进入同一预览、评审和渲染路径。
- `deterministic-third-party-adapters`: 明确白名单视觉库的接入规则，并把 ECharts、Dagre 与 Lucide 纳入确定性适配和依赖锁定要求。

## Impact

- 分镜 schema、TypeScript 类型与 Python 校验器需要支持场景渲染模式和模块引用。
- `web` 工程需要作品源码桥接、场景注册清单、Tailwind 扫描入口、代码场景运行时与静态检查。
- 预览、评审、渲染和成片溯源需要纳入作品级 TSX/CSS/SVG 及本地素材。
- `web/package.json` 与锁文件新增并锁定 `lucide-react`；ECharts 与 Dagre 复用现有依赖。
- README、项目规划、article2video Skill 的分镜结构、渲染契约、视觉规范、生成规范和示例需要同步更新。
