## MODIFIED Requirements

### Requirement: 每幕必须声明镜头语言
作品 SHALL 在全片 world.camera 声明镜头段及稳定对象焦点；阶段 visualIntent SHALL 记录构图、单一焦点及情绪，与实际画面对应。镜头 SHALL NOT 在阶段边界隐式重置。

#### Scenario: 焦点冲突
- **WHEN** 阶段声明焦点与实际主体位置不符
- **THEN** 评审定位阶段和帧并形成返工项

#### Scenario: 镜头声明与画面冲突
- **WHEN** 场景声明左侧焦点但所有主要元素都在右侧
- **THEN** 评审报告指出声明与实际布局不一致

### Requirement: 镜头由受控多段轨迹组成
全片镜头 SHALL 使用 hold、push-in、pull-out、pan、reframe、settle 有序轨迹，每段绑定有效全局 beat 或阶段语义区间，从上一段终态连续开始。阶段稳定阅读窗口内 SHALL 无主要镜头漂移。

#### Scenario: 跨阶段推进
- **WHEN** 推进段在下一阶段完成
- **THEN** 镜头连续求值，不回到初始缩放或位置

#### Scenario: 持续漂移
- **WHEN** 阶段末稳定窗口内镜头仍有非零速度
- **THEN** 严格评审失败并指出区间

#### Scenario: 镜头随推理推进
- **WHEN** 一个阶段先建立整体、再强调局部、最后展示结论
- **THEN** 镜头依次停留、推进到焦点并收束，段边界与相应 beat 对齐

#### Scenario: 镜头持续漂移
- **WHEN** 镜头从幕首到幕尾始终保持非零位移或缩放速度
- **THEN** 严格评审失败并指出没有停留或收束的区间

### Requirement: 镜头焦点必须对应稳定节点
非静态镜头 SHALL 指向全局可定位对象，以确定性几何计算变换。焦点缺失、不可见或缺几何 SHALL 在相关帧验证失败，不靠寻帧时 DOM 测量或默认焦点回退。

#### Scenario: 重构图
- **WHEN** 目标节点有效
- **THEN** 连续平移缩放到目标构图

#### Scenario: 无效焦点
- **WHEN** 目标在镜头作用区间不可见
- **THEN** 报告节点和区间，阻断正式输出

#### Scenario: 重构图到新焦点
- **WHEN** `reframe` 段从整体转向一个有效节点
- **THEN** 画面连续调整平移和缩放，使该节点进入声明的构图重心而不触发运行时 DOM 测量

### Requirement: 风格包统一作品级视觉语言

一个作品 SHALL 只启用一个主风格包；色彩、表面、线条、排版、动效曲线和阶段衔接规则 SHALL 从该风格包取值。风格包 SHALL 是导演简报的必填枚举，缺失或取未登记值时 SHALL 在校验阶段失败，SHALL NOT 回落到默认值继续渲染。

#### Scenario: 分镜声明风格包
- **WHEN** v4 分镜指定 `directingBrief.stylePack`
- **THEN** 预览和渲染按该风格包选择视觉令牌与动画语言

#### Scenario: 未声明风格包
- **WHEN** 分镜的 `directingBrief` 缺少 `stylePack`，或取值不在登记的枚举里
- **THEN** 校验失败并指出字段路径，不存在「用默认风格包继续渲染」的分支


## REMOVED Requirements

### Requirement: 场景之间必须声明视觉转场
**Reason**: 全片持续场景不再切换独立幕或执行跨幕视觉转场。
**Migration**: 使用全局对象身份、状态轨道与全片镜头，不提供旧模式回退。
