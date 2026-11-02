## ADDED Requirements

### Requirement: 轨迹、爆散与字幕原语

系统 SHALL 在 `web/src/code-scene/` 提供以下纯数值原语，并从 `m2v/code-scene` 导出：

- `samplePath`：按弧长把单子路径 SVG path 采样为等距点；多子路径 MUST 明确失败，不把不连续段当作一条轨迹；
- `sampleTrail`：沿点列按 `progress` 与尾迹长度采样位置、切线、年龄与透明度；
- `burstField`：按显式种子、原点、方向、速度、阻力、重力、寿命与 `progress` 计算粒子位置、尺寸与透明度；
- `expandingRings`：每个环独立出生、半径与透明度，按 `progress` 与错峰求值；
- `dissolvePair`：返回互补的旧层与新层不透明度；
- `staggerReveal`：返回每个字符的 0–1 进度，步长压缩在窗口内；
- 字幕原语：激活窗口查询、两行切分、窗口包络与关键词切分。

所有原语 MUST 只接受显式 `progress`/0–1 进度、显式种子与显式缓动，MUST NOT 读取挂钟、帧号、上一帧状态、DOM、外部资源或计时器。相同参数与进度 MUST 产生相同输出。端点 MUST 透明或零值，不留下上一帧残影。原语 MUST NOT 内置颜色、字体、线宽、题材或事件时刻。

路径采样与锥形笔触 MAY 复用 MIT 许可的 `svg-path-properties` 与 `perfect-freehand`；引入第三方纯函数 MUST 在 `m2v/code-scene` 内封装，风格组件与作品 MUST NOT 直接导入。新增动效或可视化组件前 MUST 先检索并评估外部成熟方案，只有在无法满足逐帧确定性、许可、包体或风格边界时才允许自研，并在设计记录中写明结论。

#### Scenario: 同一进度重复求值

- **WHEN** 任一新增原语以相同参数与 `progress` 求值两次
- **THEN** 两次输出一致，不受调用时刻、调用顺序或已播放帧数影响

#### Scenario: 跳帧与端点

- **WHEN** 录制从 0.2 直接跳到 0.8，或求值 `progress` 为 0 与 1
- **THEN** 跳帧结果与逐帧求值一致，粒子、环与尾迹在端点为透明或零值

#### Scenario: 多子路径

- **WHEN** 把含多个 `M` 子路径的图标传给 `samplePath`
- **THEN** 调用明确失败并提示单子路径限制，不返回跨子路径的连续点列

#### Scenario: 未检索直接手写

- **WHEN** 新增的动效或可视化组件没有外部方案检索记录，或选型理由未写入设计记录
- **THEN** 审查判定不符合协作约定，须补检索与记录后再实施
