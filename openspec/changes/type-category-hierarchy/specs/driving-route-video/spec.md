## MODIFIED Requirements

### Requirement: 独立自驾路线材料与生命周期

系统 MUST 提供 `driving-route` 类型，以独立的 `request.json` 和 `route.json` 执行初始化、校验、准备、片段预演、完整渲染、状态及可选评审，MUST NOT 要求 general storyboard。请求 MUST 声明起终点地址、所属城市、画面名称、高速优先策略及视频时长；初始化默认30秒。路线 MUST 记录请求摘要、定位结果、实际路线端点、明确坐标系、有序分段坐标、道路名称、总距离、提供方、采集时间及来源使用依据。画幅 MUST 固定1080×1920 竖屏、30 fps；时长 MUST 为大于6秒的整数，首尾各保留2秒，剩余时间行驶。`driving-route` MUST 属于 `route-journey` 类别，作品标准位置 MUST 为 `videos/route-journey/driving-route/<slug>/`。

#### Scenario: 初始化与更换端点
- **WHEN** 初始化 driving-route 作品并设置任意受支持的起终点
- **THEN** 创建独立类型材料模板；补齐有效真实路线后可制作，无需 general 分镜，且不把上海郑州写死为唯一端点

#### Scenario: 初始化到类别目录
- **WHEN** 在工作区根执行 `m2v init --type driving-route --project <slug>`
- **THEN** 作品创建在 `videos/route-journey/driving-route/<slug>/`，显式平铺路径 `videos/driving-route/<slug>/` 被拒绝并给出规范位置

#### Scenario: 不完整与非法材料
- **WHEN** 材料仍含占位、缺少来源、坐标非有限或越界、无可行驶路线、时长非法，或显式输出画幅帧率与类型不一致
- **THEN** 校验指出字段及原因，拒绝准备和渲染，不以示意坐标填充真实路线

#### Scenario: 旧横屏材料被拒绝
- **WHEN** 材料或 `project.json` 仍为 1920×1080 横屏，或 driving-route 仍声明 30 fps
- **THEN** 校验明确失败并提示按 1080×1920、30 fps 重新初始化或更新后重新准备，不输出旧契约成片
