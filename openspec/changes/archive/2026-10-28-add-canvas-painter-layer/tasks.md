## 1. 绘制原语与出帧

- [x] 1.1 新建 `web/src/code-scene/painter/frame.ts`：绘制原语（分组、临时层合成、光晕、光点、尾迹、线、折线带生长进度、沿线取点、圆、椭圆、矩形、路径、文字、逐字、排版、测量、线性与径向渐变）；验证 `pnpm -C web test` 下相同帧号两次求值结果相同，且不含颜色/字体/主题内置值。
- [x] 1.2 新建 `web/src/code-scene/painter/bloom.ts`：底、内容层、缩小两次模糊加法叠回、颗粒；验证同一帧两次出帧像素一致，且不读取挂钟或随机源。
- [x] 1.3 新建 `usePainter.ts` React 绑定与画布组件，按 `captureScale` 分配后备缓冲并换算坐标；验证 `captureScale=2` 时后备缓冲达逻辑尺寸两倍，不触发像素不足。

## 2. 量测代理

- [x] 2.1 新建 `painter/measure-proxy.tsx`：从同一份绘制数据渲染透明 `data-m2v-role`/`data-m2v-state` 元素，位置尺寸对应绘制包围盒、字号与字体一致、文本与文字计划相等；验证代理几何与绘制数据逐项相等。
- [x] 2.2 实现逐帧状态探针写入 `window.__M2V_REVIEW_STATE__`，在每个观测帧推进完成前写入；验证 `measure.evaluate()` 对绘制层场景给出"观测范围"非未验证、"对象状态"通过、有活动文字计划时通过而非失败，且 `evaluate_probe()` 与代理结果一致。
- [x] 2.3 从 `web/src/code-scene/sdk.tsx` 导出绘制层，导出名与既有 R3F `Canvas` 区分；验证未导入绘制层的作品画面与改动前逐像素一致。

## 3. 闸门与指纹

- [x] 3.1 扩展确定性检查的测试扫描范围至 `web/src/code-scene/**/*.{ts,tsx}`，覆盖绘制层、宿主与 SDK；验证注入违规写法（挂钟、随机数、计时器、未关闭 CSS 动画）时测试失败并指出文件与行号。
- [x] 3.2 确认绘制层进入 `implementation_inputs()` 并计入准备指纹与片段缓存键；验证修改绘制层后旧准备失效、需重新 prepare。
- [x] 3.3 确认绘制层不内嵌面向观众的中文文案：新增测试断言绘制层源码不含中文字面量，文案只来自作品参数或文字计划。

## 4. 文档

- [x] 4.1 更新 `references/code-scene-runtime.md`：绘制层用途与边界、原语清单、采集像素密度要求、量测代理与探针的推荐写法、三种绘制载体的选择依据；验证相对链接与锚点可解析。
- [x] 4.2 更新 `references/storyboard-schema.md` 的全画布代码场景一节，说明可选绘制层与文字计划的关系；验证 `storyboard-schema` 仍含既有关键词（`m2v/code-scene`、`subtitleSafeArea`、`useMediaAsset`），既有测试不回归。

## 5. 端到端样片验证

- [x] 5.1 在 `videos/general/<新 slug>/` 建 30–45 秒原创作品，至少两幕真实使用绘制层，含辉光、线条生长与逐字显影；验证 `m2v validate` 与 `m2v prepare` 通过、目录被 Git 忽略。
- [x] 5.2 用 `m2v lookdev --sheet` 与 `--still-scale 2` 截图核对画面，确认辉光出帧在成片里成立、主体可辨；若辉光不成立，记录结论并降级为"仅提供原语"。
- [x] 5.3 在 `DESIGN.md` 合同声明检查点，`expected` 写绘制层代理的角色与数量，跑 `m2v gates check --gate G4 --checkpoint <ID>`，验证关键项为通过而非未验证。
- [x] 5.4 按 `subagent-review.md` 的隔离要求走一次核心样片独立子代理评审；如实记录未覆盖项（最终终审、声音等）。

## 6. 验证与交付

- [x] 6.1 运行 `pnpm -C web test`、`pnpm -C web build`、`uv run pytest -m "not slow"` 与相关 slow 用例；确认固定示例、金融与住宅类型不回归。
- [x] 6.2 检查暂存范围（排除 `videos/` 内容与生成媒体）后提交实施；同步 `openspec/specs/react-code-scenes/spec.md` 主规格，移入 `openspec/changes/archive/2026-10-28-add-canvas-painter-layer/` 并提交归档。
