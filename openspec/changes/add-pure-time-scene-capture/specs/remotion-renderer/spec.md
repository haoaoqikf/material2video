## ADDED Requirements

### Requirement: 可选进程级分段渲染

渲染入口 SHALL 提供可选正整数 `--jobs`，默认 1。`--jobs: 1` SHALL 保持现有单会话渲染路径。`--jobs > 1` 时，系统 SHALL 先读取并交叉校验 composition 元数据，再按帧区间启动多个独立渲染进程；每段 SHALL 独立解码核对帧数、尺寸与帧率，拼接后 SHALL 复核总帧数，最后统一混入音轨。

`--jobs` SHALL 与 Remotion 页签级 `--concurrency` 区分；分段内部并发 SHALL 固定为 1。`--jobs` SHALL NOT 进入候选交付绑定：改变 jobs 仍可复用同一内容候选。任一段失败 SHALL 清理进程并明确失败，MUST NOT 留下可被误认为成功的成片。当前该能力 SHALL 仅对 `general` 开放，其他类型收到 `jobs > 1` SHALL 明确拒绝。

#### Scenario: 分段渲染

- **WHEN** general 作品以 `--jobs 4` 渲染全片
- **THEN** 四个帧区间独立渲染、逐段验收后无损拼接，成片帧数、尺寸、帧率与单进程一致

#### Scenario: 默认单进程

- **WHEN** 未声明 `--jobs` 或声明 1
- **THEN** 走现有单会话渲染，行为与产物不变

#### Scenario: 元数据不一致

- **WHEN** composition 报出的 fps、尺寸或总帧数与准备记录不一致
- **THEN** 在分段渲染开始前失败，不生成任何片段

#### Scenario: 某段失败

- **WHEN** 任一分段渲染或解码验收失败
- **THEN** 终止其余进程并报错，不拼接、不发布候选

#### Scenario: 其他类型

- **WHEN** 非 general 作品请求 `--jobs > 1`
- **THEN** 渲染前明确拒绝，不改变该类型的既有路径
