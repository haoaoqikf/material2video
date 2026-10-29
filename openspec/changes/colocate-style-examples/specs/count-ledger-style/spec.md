## MODIFIED Requirements

### Requirement: 风格示例作品（视频专属，不属于包）

仓库 SHALL 在 `styles/count-ledger/examples/compound-interest/` 提供规范示例，声明 `style.id: "count-ledger"`。该作品 SHALL 保持 29 秒/870 帧、30 fps、无旁白、8 秒进入的无旋律环境床与同步事件音、1 枚圆片=1,000 元的资金状态机、收益再投入与累计总额比较；详细行为引用既有 `compound-interest-explainer-video`，本规格不复制其数学细节。示例 SHALL 通过 v8 校验与 `prepare`，生成媒体 SHALL NOT 入库。复利数学、分镜、圆片坐标与声音配方属于作品，SHALL NOT 进入共享风格实现或风格指纹。

#### Scenario: 示例可校验

- **WHEN** 对 `styles/count-ledger/examples/compound-interest/` 运行 `m2v validate` 与 `prepare`
- **THEN** 校验通过，实际时长 29 秒、870 帧、30 fps、无旁白，事件音与画面事件对应

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** `styles/count-ledger/examples/compound-interest` 不出现在风格清单中，也不能按风格 id 加载
