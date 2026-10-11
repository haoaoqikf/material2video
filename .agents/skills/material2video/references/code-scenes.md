# 全片代码场景（v4）

当受控原语无法表达持续视觉世界所需的几何、关系或状态变化时，可选择作品级 code renderer。`world.renderer` 只声明一次；模块贯穿整条视频，阶段只改变上下文，不得切换为互不相关的页面。能由原语清楚表达时优先使用 tree renderer。

本文记录模块契约、确定性纪律和探针要求。完整示例见[飞镖试错示例](../../../../examples/darts-trial-and-error/storyboard.json)，是一个 world、多阶段叙事。

## 分镜声明

以下是关键 world 字段形状（阶段口播与完整导演简报略去，不能单独作为可运行分镜）：

```json
{
  "world": {
    "id": "system-world",
    "claim": "整体结果受当前瓶颈限制",
    "metaphor": "一条持续的工序面板",
    "objects": [{ "id": "pipeline", "role": "primary", "description": "持续工序流程" }],
    "renderer": { "kind": "code", "module": "system-panel" },
    "data": { "objects": { "pipeline": { "state": "rest" } } },
    "stateTracks": [],
    "motions": [],
    "camera": { "shot": "medium", "composition": "center", "depth": "flat", "focus": "pipeline", "segments": [{ "id": "hold", "kind": "hold", "binding": { "stageId": "opening", "phase": "establish" }, "focus": "pipeline", "intensity": 0 }] }
  },
  "stages": [{ "id": "opening", "durationInFrames": 1080, "data": {}, "visualIntent": {}, "narrationSegments": [], "beats": [] }]
}
```

- `world.renderer.kind` 固定为 `code`，`module` 指向作品目录下 `scenes/<module>.tsx` 的稳定模块名。
- `world.objects` 声明全片稳定身份；每个对象须由模块探针暴露，供状态、镜头与连续性评审引用。
- 全片只能选 tree 或 code 一种 renderer；`stages[]` 不得声明 renderer、sceneTree、camera 或 transition。
- 对象数据、状态轨道、camera 段和 beat 时间轴统一放在 world 与阶段声明中。模块不私自累计状态，也不创建阶段专属完整页面。
- 在作品目录的 `motion-design.md` 中说明持续场景、对象初态、各 beat 触发的变化及结果停留，不复制口播全文。

## 模块接口

模块默认导出 `M2VCodeScene<Data>`（`React.FC<M2VCodeSceneProps<Data>>`），唯一项目内导入别名为 `@m2v/scene`：

```tsx
import { probe, type M2VCodeScene } from '@m2v/scene';

const World: M2VCodeScene = ({ world, stage, objectStates, frame, fps, canvas, theme, beats, motion }) => (
  <div {...probe({ node: 'pipeline', role: 'hero', geometry: { x: 0.1, y: 0.3, width: 0.8, height: 0.4 } })}>
    {world.claim} · {stage.id} · {objectStates.pipeline?.state} · {frame}/{fps}
  </div>
);

export default World;
```

共享层注入全片 world、当前 stage、当前全局 `frame`、媒体派生 beats、对象状态、camera/motion 上下文、主题、画布及稳定种子 `random(node)`。`stage.progress` 是阶段内进度，`progress` 与 `localFrame` 在 v4 兼容接口中按全片语义提供。模块不能决定阶段次序、总时长、字幕边界或第二套时钟；禁止挂钟、随机非确定输入、网络、文件系统和 Node 访问。

作品代码从同一纯函数取得状态：`beatActionProgress(plan, id, finishAt)` 按全局 beat 计算动作进度；`compilePath(points)` 预编译路径；`compileReservoir(capacity, initial, intervals)` 计算有界流量及守恒状态；`decomposeObjects(objects, progress, reverse)` 插值稳定 ID 的对象布局。昂贵的路径和流量计算在模块初始化或 `useMemo` 完成，不在每帧重建。

## 探针与几何

模块通过 `probe()` 给持续对象输出稳定节点 ID、语义 role、可选容器关系、示意标记和画布归一化几何。被 `world.objects`、camera focus 或连续性审查引用的对象必须可观察；缺失探针会让评审失败，不能降级为猜测 DOM 或按换场处理。

```tsx
<section {...probe({ node: 'target', role: 'hero', geometry: { x: 0.55, y: 0.24, width: 0.34, height: 0.46 } })}>
  <span {...probe({ node: 'hit-count', role: 'label', inside: 'target', schematic: true })}>3 次·示意</span>
</section>
```

`geometry` 中的 x/y/width/height 为画布 0～1 归一化值；它用于跨阶段对象位置比较。文字需登记 node 与 role 才能进入内容和排版评审；示意数值须明确标出 `schematic`。被评审规则引用的容器应使用 `inside` 表明归属。

tree v4 的字体后布局预检不改变 code world 的公开探针契约；代码场景仍由作者通过 `geometry` 与 `inside` 明确提供稳定对象边界和包含关系，运行时不读取作品模块私有 DOM。

## 验证与安全边界

- 使用 `uv run m2v validate --project <目录>` 验证 v4 分镜字段、全局对象与阶段；缺失或不可解析的 code module 在浏览器启动前报错。
- `uv run m2v article keyframes --storyboard <分镜> --check-determinism` 对全片抽帧并读取 `window.__M2V__` v4 探针，检查随机寻帧和同帧重绘，PSNR 至少 60 dB。
- 代码模块通过导入白名单、静态源码规则、可达文件指纹和渲染期离线请求阻断。此边界是项目代码评审措施，不是操作系统沙箱；只执行项目内受控代码。
- 全片动态与连续性评审应播放有声评审版，核对对象身份、状态承接、camera 和结果停留。缺证据为 pending，不能以静态评审代替。

命令顺序、渲染门禁和错误处理以 [制作 Skill](../SKILL.md)、[分镜脚本结构](storyboard-schema.md)、[视觉评审量表](visual-review-rubric.md) 和[渲染契约](render-contract.md)为准。
