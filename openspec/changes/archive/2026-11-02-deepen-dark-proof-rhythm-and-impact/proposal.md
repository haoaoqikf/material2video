## Why

实测《样本》与参考片仍有量级差距：明显变化事件 1.2 次/10 秒（参考 5.47），近静止秒数 54%（参考 8%），金色像素峰值 1.38%（参考 14.0%），亮部峰值 3.34%（参考 15.0%）；参考片 57.9 秒的粒子云占 74% 宽 × 66% 高，而《样本》最大爆散粒子实际只走约 44 px。根因之一是 `burst.tsx` 固定 `drag:4`，`burstField` 的实际位移只有 `speed` 的约 24.5%。声音侧，参考片有持续人声与低伏配乐；《样本》是无节拍环境床，频谱通量 0.06 vs 0.37，类起音 0 vs 2.06/秒。

用户要求解决这两个问题，允许深度重构，并确认：不加旁白；保留 58 秒、1740 帧与八段论证；段内拆成 12–16 个微拍；4–5 个关键转折做整屏爆散；允许缓慢单向推近。

## What Changes

- 通用层新增 `explosionField`（多层、带深度/bokeh/streak 的闭式爆散）、`moteField`（环境微尘）、`impactEnvelope`、`beatPhase`/`beatPulse`，以及透明 Canvas `ScreenBurstLayer`。粒子位置只由 progress 与 seed 求值，可逐帧 seek。
- SDK 导出上述能力；`screen-burst.tsx` 使用 `captureScale` 后备缓冲、预渲染 sprite、加法混合与字幕安全区遮罩；不使用 rAF/useFrame/计时器。
- `dark-proof` 新增 `impact` 组件与 `shatter/reveal/formula/finale` 四个 preset；版本升为 1.2.0；`burst` 的 `drag` 从 4 降到 1.2，局部爆散实际位移恢复。
- 《样本》在八拍内部加入 12–16 个微拍与 4 个整屏冲击（738、1194、1440、1580），加入 ambient dust、金点/关键词节拍脉冲与全片 8% 缓慢单向推近；硬切仍只在 600 帧。
- 声音改为 58 秒、112 BPM 原创程序化配乐（低频 kick、反拍 tick、和声垫、hat build、riser、impact），保留 9 个资产 ID；新增 `line-shatter`、`elephant-reveal`、`formula-impact` 事件与撞击音。
- 更新 GUIDE、DESIGN、SOUND、SOURCES、README、PROJECT_PLAN、测试与 OpenSpec 主规格。

不改变 v8 schema、视频类型、CLI、共享旁白字幕层、composition 跨幕转场、论证顺序或唯一硬切位置；不改 13 条屏幕字幕文本/窗口与 10 个检查点窗口。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `scene-motion-primitives`: 新增整屏粒子、环境微尘、冲击包络与节拍原语；明确 Canvas 层与逐帧确定性边界。
- `react-code-scenes`: 代码场景 SDK 导出透明整屏效果层与新增纯函数；效果层使用 captureScale、无 rAF/useFrame。
- `dark-proof-style`: 新增 impact 组件与四个整屏冲击；允许缓慢单向推近、环境微尘与 112 BPM 微拍节奏；保留唯一硬切与字幕安全区。

## Impact

- 新增/修改 `web/src/code-scene/{dynamics,rhythm}.ts`、`effects/screen-burst.tsx`、`sdk.tsx` 与测试；实现指纹变化，引用作品需重新 prepare。
- 修改 `styles/dark-proof/` 的 impact、burst、tokens、style.json、GUIDE 与版本 1.2.0；风格指纹变化。
- 修改示例场景、storyboard 事件、合成音频、SOUND/DESIGN/README/VERIFICATION；生成媒体与 outputs 不入库。
- 不改 58 秒/1740 帧/13 条字幕/10 个检查点；旧候选、QA 与并排证据失效，需重渲染与重审。
