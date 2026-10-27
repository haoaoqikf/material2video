# 验证记录

## 变更 C：add-canvas-painter-layer

### 单元测试

```powershell
pnpm -C web test
# 7 个测试文件、106 项全部通过（含新增 painter.test.ts 的 11 项）

$env:PYTHONIOENCODING='utf-8'
uv run pytest tests/test_canvas_painter.py tests/test_motion_primitives.py tests/test_cinematic_scene_kit.py -q
# 全部通过
```

新增覆盖：

- **原语确定性**：同一帧两次求值的清单与调用序列完全相同。
- **清单几何**：文字记入清单时带与绘制一致的字号、文本与状态；宽高来自同一份布局计算。
- **不进清单的绘制**：无 `role` 的绘制、`measurable: false` 的文字都不产生代理。
- **折线生长**：`k=0.5` 只画前一段；`along()` 返回插值坐标与切向。
- **像素密度**：非正密度明确抛错。
- **代理状态聚合**：按角色计数；同角色状态冲突时置空而不是猜一个；空清单得到空列表。
- **实现指纹**：绘制层全部文件都在 `implementation_inputs()` 内。
- **确定性闸门**：绘制层通过 `source_policy.scan`；目录级扫描（排除刻意重导出 `motion`/`gsap` 的 SDK）。
- **反例**：注入 `Date.now()` 与 `Math.random()` 时闸门确实拦下。
- **无内嵌文案**：`text()` / `chars()` 的实参不含中文。
- **代理同源**：代理文件不含 `getBoundingClientRect` 或 `measureText`，几何只来自清单。

### 端到端（慢测试）

`test_painter_scene_builds_and_measures` 用真实 esbuild 打包 + Playwright 录制一个使用绘制层的最小场景，断言：

- DOM 读到 `role="subject"`、`state="revealed"`、`textContent` 正确；
- `measure.evaluate()` 的「对象状态」「文字状态」均为 `pass`；
- **「观测范围」这条检查不再出现**（即不再是 `unverified`）；
- `evaluate_probe()` 全部通过。

### 原创样片（videos/general/painter-sunset，不入库）

31.2 秒（936 帧）、三幕、1920×1080/30fps，三幕都使用绘制层：

- 第一幕：太阳沿弧线下落，辉光随接近地平线变暖，弧线虚线随进度生长，两行主句逐字显影。
- 第二幕：光束从左侧长出，90 个蓝点沿途散开并随距离变淡，末端留暖色光斑，底部一把刻度尺。
- 第三幕：回场——同一个太阳分出两条路，近而短的白、远而长的转暖，两条都长完后结论才出。

流程全部跑通：

```
m2v validate  → 材料校验通过
m2v prepare   → 已生成准备产物（936 帧）
m2v lookdev --sheet 1 5 9 13 17 21 25 29  → 8 帧拼图
m2v gates check --gate G4  → 三个检查点 status: pass
```

`gates check` 的关键结论（三个检查点全部 `pass`）：

| 检查点 | 断言 | 结果 |
|---|---|---|
| `cp-sun-frame` | `lead`、`tail` 各 1、状态 `revealed` | 对象状态与探针均 pass |
| `cp-scatter-frame` | `axis-label` 1、文字与合同相等 | 对象状态、文字状态、探针均 pass |
| `cp-answer-frame` | `headline`、`conclusion` 各 1，`path-label` 2 | 对象状态与探针均 pass |

三份报告中**均未出现「观测范围：未验证」**。量测读到的实际元素形状为
`[('lead','revealed','太阳越低'), ('tail','revealed','光穿过的大气越厚')]`，
探针同步为 `[{role:'lead',count:1,state:'revealed'}, ...]`。

### 制作中发现并修复的三个缺陷（已回写契约）

1. **文字进辉光层被冲出重影**。首轮拼图前四格的主句明显叠了数层。加 `overlay` 锐利层，画在辉光之后。
2. **文字与细线被自身光晕糊掉**。与第 1 条同因，第二幕的轴标签一并移到 `overlay`。
3. **量测代理的文字被真实渲染**。代理最初用普通 `color`，与画布文字叠在一起，每个字都出现重影。改为 `-webkit-text-fill-color: transparent`——这是唯一同时满足「屏幕上不可见」「计算样式 `color` 仍是原值」的写法。`opacity: 0` 会被判不可见，`color: transparent` 会让颜色断言全部失败。

修复后重截，重影消失，文字清晰。

### 未覆盖项

- **未做最终终审与全片完整评审**：样片是验证片，只跑了 G4 检查点与一次核心画面独立评审，未走粗片与终审轮。
- **第三幕在首轮截图中暴露并被修复的两处取景问题**：太阳本体被画面左边界裁掉；两条路的长度差异不明显。改为太阳内缩、两条路从同一点出发并落到同一高度，只让横向距离不同。
- **未接声音**：绘制层不渲染音频，本片无音轨。
- **未验证 60fps**：样片只按 30fps 跑；绘制层不读帧率，帧号来自 `elapsedSeconds * fps`，逻辑上无关，但无实测。
- **长期维护成本**：绘制层是第三种载体，作者需在 DOM/SVG、`painter`、`three` 之间选择；选择依据已写进运行时契约，但实际使用中的边界仍待作品检验。
