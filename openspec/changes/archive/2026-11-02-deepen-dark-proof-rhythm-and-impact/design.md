## Context

上一轮已把光轨、爆散、扩散环、逐字字幕与锚点转场分层，但粒子的实际量级、事件密度与声音节奏仍远低于参考片。本变更不是继续加参数，而是把“整屏冲击”和“节拍”做成可复用能力，再重排《样本》的段内微拍。

## Goals / Non-Goals

**Goals:** 4 个关键转折出现覆盖 60–80% 画面、持续 2–3 秒的多层粒子冲击；明显变化达到约 3–5 次/10 秒；近静止秒数降到 20% 以下；用 112 BPM 原创配乐补上人声缺口；保持唯一硬切、数学口径与字幕/检查点窗口。

**Non-Goals:** 不加旁白；不改 v8、CLI、共享字幕层、跨幕转场、论证顺序；不使用参考素材或第三方音乐。

## 外部方案

| 候选 | 结论 |
|---|---|
| `three-nebula`（MIT） | 有 seed 与固定步进，但状态式模拟需从 0 重放，不能任意帧 seek；包体/three 版本维护有风险 |
| `three.quarks` | 无公开 seed/确定性重放 API |
| Remocn Confetti / remotion-ui Particle Field | 许可不明确、偏彩屑/背景尘，不满足全屏 bokeh |
| three.js Points + shader | 成熟核心；作为 Canvas 性能不足时的回退方案 |
| Canvas 2D + 预渲染 sprite | 采用。无需新依赖、可逐帧 seek、sprite 提供柔光/虚化/streak |

## 架构

### 通用原语

- `explosionField`：`reach` 表示最终最大位移，避免 drag 吃掉半径；粒子按 index 分 shell/ember/bokeh/dust 四层；每粒子有出生延迟、寿命、方向、深度、size、opacity、blur、streak；端点透明。
- `moteField`：固定种子、低速漂移的环境微尘，用于消除长静止。
- `impactEnvelope`：冲击闪光与环包络，端点归零。
- `beatPhase` / `beatPulse`：全片 progress + duration + BPM 映射为 0–1 相位与脉冲，不读帧号/挂钟。

### 透明 Canvas 层

`web/src/code-scene/effects/screen-burst.tsx`：

- 透明 `<canvas>`，内部缓冲按 `__M2V_CODE_CONFIG__.captureScale`；`useLayoutEffect` 在每帧同步重绘，不用 rAF/useFrame。
- 预渲染 core/soft/bokeh/streak 四类 sprite；`globalCompositeOperation='lighter'` + CSS `mixBlendMode:'screen'`。
- 每帧绘制 ambient dust → flash → rings → shell/ember/bokeh/dust；active burst 上限 1 个主冲击 + 1 个余波。
- 底部字幕安全区用 `destination-out` 渐变淡出粒子。
- 放在 SVG 主体之下、Stage 背景之上；字幕与方法说明不缩放。

### 风格层

`styles/dark-proof/components/impact.tsx` 把 `shatter/reveal/formula/finale` 映射为 `BurstSpec`；tokens 控制 count/reach/frames/rings/flash/bokeh。`burst.tsx` 的 `drag` 从 4 降为 1.2，局部爆散恢复实际可达位移。

### 视频层

八拍边界、13 条字幕与 10 个检查点不变；段内加入微拍：

- 4 个整屏冲击：738（线溶解）、1194（全象揭示）、1440（≈18×）、1580（结尾）。
- S3/S5/S6/S7/S8 加入落点 tick、标记脉冲、取样窗依次打开、括号脉冲与 finale 收拢。
- 全片视觉层 `scale(1 + 0.08 * easeInOutSine(frame/1739))`；字幕/方法说明不缩放。
- 金点与关键词按 112 BPM 脉冲；点阵缓慢漂移；ambient dust 常驻。
- 冲击期间点阵压暗到 20%–35%，让粒子成为唯一焦点；硬切 600 帧仍只播单环。

### 声音

- 58 秒、112 BPM 原创 score：低频 kick、反拍 tick、minor pad、8 分 hat、riser、impact；20.0 秒硬切留白 0.4 秒，57.2–58 秒收束。
- 保留 9 个资产 ID；新增 `line-shatter`、`elephant-reveal`、`formula-impact` 事件，复用 `impact` 源；`formula-impact`/`finale` 与视觉冲击对齐。
- 母版 −14 LUFS / ≤−1 dBTP；无第三方采样与音乐服务。

## 决策与取舍

- 选择 Canvas 2D 而非 three.js：可逐帧 seek、无 WebGL alpha/useFrame 约束、无新依赖；bokeh 由 sprite 提供。
- 不改八拍边界与字幕窗口：把节奏增量放在微事件、粒子、推近与配乐上，减少检查点与文案失效面。
- 全屏冲击只做 4 次：与参考片一样稀疏，避免疲劳并保住唯一硬切的区分度。
- 无旁白：用户明确选择；用 112 BPM 配乐与密集微事件补足，而不是引入 TTS。

## 风险 / 回退

- Canvas 2× 采集性能：先降 count/bokeh，仍不足切 three.js Points；同一 `explosionField` 数据可直接复用。
- 粒子遮挡字幕/文字：Canvas 在 SVG 之下 + 安全区遮罩；代表帧逐张检查。
- 粒子过密成雾：bokeh 比例/透明度受 tokens 控制；冲击期间点阵压暗。
- 音乐过强：score 保持低伏；impact 只在大事件；QA 复核响度。
- 确定性：无时间/随机源；`--det` 与 Vitest 覆盖；Canvas 同机可复现。
