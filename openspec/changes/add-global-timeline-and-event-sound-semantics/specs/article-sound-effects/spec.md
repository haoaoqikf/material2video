## ADDED Requirements

### Requirement: 语义事件用密度与强弱表达

作品 SHALL 能用现有声音字段表达语义变化：同一角色可在不同事件上重复使用同一 `assetId` 并通过事件数量控制密度，通过 `gainDb` 控制强弱，通过 `fadeInMs`/`fadeOutMs` 控制收束；需要不同质感时 SHALL 用不同 `assetId`（可来自不同合成 `seed`/`intensity`）。系统 SHALL NOT 要求新增音高参数才能表达计时、到达、接合或揭示。

每个音效 SHALL 用 `eventId` 或显式时间定位到所属幕；语义事件与音效起点 SHALL 由 prepare 的同一次解析产生。未声明音效的事件 SHALL 保持无声音，不自动补音。

#### Scenario: 计时密度变化

- **WHEN** 作品在计时段声明每秒一个 `tick` 事件，并在临近喂食时增加事件数量
- **THEN** 声音密度随事件数量变化，音效起点与事件帧一致

#### Scenario: 到达与揭示使用不同素材

- **WHEN** 食物到达声明 `grain`，揭示声明 `chord`
- **THEN** 两类事件使用不同 `assetId`，不需要新增音高参数

#### Scenario: 事件无音效

- **WHEN** 语义事件只被画面引用、没有声明音效
- **THEN** 该事件保持无声，系统不自动补音或改动其他声音
