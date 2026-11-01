## MODIFIED Requirements

### Requirement: 统一作品及制作入口

系统 MUST 支持 project.json v1 和 m2v types/init/validate/prepare/preview/review-template/review/status/render/migrate/relocate；`m2v init` MUST 将作品初始化到规范位置：未分类类型为 `videos/<type>/<slug>/`，属于类别的类型为 `videos/<category>/<type>/<slug>/`；作品相对材料以作品根解析，类型材料独立。退出码 MUST 区分成功0、执行或门禁失败1、材料或参数错误2。

#### Scenario: 材料归属与未知类型
- **WHEN** 在不同工作目录操作作品或传入未知类型/版本
- **THEN** 已知作品归属稳定，未知类型或版本在渲染前失败

#### Scenario: 按类型初始化作品
- **WHEN** 在工作区根对某个未分类的已登记类型执行 `m2v init --type general --project <slug>`
- **THEN** 作品和初始化材料创建在 `videos/general/<slug>/`

#### Scenario: 按类别初始化作品
- **WHEN** 在工作区根对已归入 `route-journey` 的 `driving-route` 执行 `m2v init --type driving-route --project <slug>`
- **THEN** 作品和初始化材料创建在 `videos/route-journey/driving-route/<slug>/`

#### Scenario: 仓库自带示例走统一入口
- **WHEN** 用统一入口对仓库 `styles/<style-id>/examples/<slug>/` 下的风格示例作品执行 prepare、preview 或 render
- **THEN** 媒体、预演与成片写入 `styles/<style-id>/examples/<slug>/outputs/`，
  不写进受版本控制的示例源文件，产物目录由 `.gitignore` 忽略

### Requirement: 逐作品路径迁移

系统 MUST 支持对已有统一契约作品逐个执行 `m2v relocate --project <非规范位置>`，按 `project.json` 中已登记的类型与类型目录中的类别推导目标位置：未分类类型移入 `videos/<type>/<slug>/`，属于类别的类型移入 `videos/<category>/<type>/<slug>/`。来源 MUST 位于工作区 `videos/` 下且为统一契约作品；`videos/<slug>/`、`videos/<type>/<slug>/` 等非规范位置 MUST 可迁移。迁移 MUST 在移动前创建包含完整旧目录的备份，并保持源材料、项目描述和整个 `outputs/` 的相对路径。目标已有同路径文件时 MUST 保留目标、将冲突源文件留在旧目录并报告；其他文件继续移动。迁移 MUST 可重跑以继续处理冲突，且不得覆盖目标文件。来源已在规范位置时 MUST 报错且不移动文件。仓库外内容根 SHALL 可通过 `--content-root` 或 `M2V_CONTENT_ROOT` 指定。

#### Scenario: 迁移统一契约作品路径
- **WHEN** 用户对 `videos/<slug>/` 下的作品执行路径迁移
- **THEN** 作品移动至该类型当前规范位置，完整备份旧目录，并保留其全部产物

#### Scenario: 迁移旧平铺分类路径
- **WHEN** 用户对 `videos/driving-route/<slug>/` 作品执行路径迁移
- **THEN** 作品移动至 `videos/route-journey/driving-route/<slug>/`，完整备份旧目录，并保留其全部产物

#### Scenario: 目标文件冲突及重试
- **WHEN** 目标目录已有同路径文件，且用户处理后重试旧目录
- **THEN** 目标版本始终不被覆盖，未冲突文件完成迁移，冲突源文件得到报告并在旧目录保留直至可迁移

### Requirement: 类型的单一登记来源

系统 MUST 在唯一一份类型目录中登记每个视频类型的身份、类别与材料入口：名称、一句话说明、作品初始化所需材料（材料名、默认文件名）与初始化模板内容；类型目录 MUST 同时登记可选类别（标识、标题与说明）以及类型所属类别。统一入口的类型清单、说明文案、初始化材料与规范作品位置 MUST 从该目录派生，禁止在作品契约或命令行入口中另行维护类型白名单、材料映射、初始化模板或类别成员。类型目录 MUST 拒绝未登记类别引用、没有成员的类别、重复类别标识，以及与类型同名的类别。类别 MUST NOT 成为可初始化或可渲染的类型。

新增视频类型 MUST NOT 需要修改统一入口的命令分发或作品契约的白名单；行为实现与目录登记是该类型仅有的两处落点。

#### Scenario: 新增类型只登记一次
- **WHEN** 为一个新视频类型实现行为并只在类型目录登记其身份、类别与材料入口
- **THEN** `m2v types` 列出该类型及其目录说明与类别，`m2v init --type <新类型>` 按目录声明生成材料文件并落到类别决定的规范位置，且统一入口的类型分发与作品契约白名单无需改动

#### Scenario: 类别不是可执行类型
- **WHEN** 用户以类别标识 `route-journey` 调用 `m2v init` 或要求处理该「类型」
- **THEN** 系统报错说明它是类型类别，并列出可选的子类型，不创建作品、不渲染

#### Scenario: 未登记的类型被拒绝
- **WHEN** 一个已注册的视频类型在类型目录中没有登记项
- **THEN** 使用该类型的操作在渲染前失败，报错指出类型目录缺少登记项并说明查询可用类型的方式；`m2v types` 仍能列出全部已注册类型，不因缺少登记项而中断

#### Scenario: 未知类型在渲染前失败
- **WHEN** 作品描述声明了未注册的类型
- **THEN** 系统在渲染前以「未知视频类型」失败并指向 `m2v types`，退出码为执行或门禁失败（1）

### Requirement: 文档中的类型清单由类型目录生成

README、Skill 与项目规划中描述视频类型的清单 MUST 由类型目录生成，不得手工维护。清单 MUST 按类别组织并显示类别标题；未分类类型 MUST 单独列出且不得被隐藏。仓库 MUST 提供一致性校验，使生成产物与磁盘内容不一致时校验失败，并指出需要重新生成的文档。

生成 MUST 是幂等的：类型目录未变化时重新生成不产生任何差异。

#### Scenario: 文档与类型目录漂移
- **WHEN** 类型目录新增类型、修改某类型的文档文案或调整类别成员，而对应文档未重新生成
- **THEN** 一致性校验失败，并指出需要重新生成的文档

#### Scenario: 按类别分组
- **WHEN** `driving-route` 与 `road-trip` 归入「路线旅程」
- **THEN** 三份文档的类型清单都在「路线旅程」下显示这两个类型，其余类型在「未分类」下显示

#### Scenario: 幂等重新生成
- **WHEN** 类型目录与文档当前一致时重新运行生成
- **THEN** 文档内容逐字节不变

### Requirement: 当前类型统一制作入口

系统 MUST 在既有正式类型基础上增加 `road-trip`，并通过统一 init、validate、prepare、preview、render 入口处理该类型；通用类型中文名为“通用”，以 storyboard 材料制作 v8 讲解；通用类型辅助操作 MUST 使用 `m2v general`，自驾路线采集 MUST 使用 `m2v driving-route fetch`，普通道路底图采集 MUST 使用 `m2v driving-route basemap`；地图游记采集 MUST 使用 `m2v road-trip fetch`，游记底图采集 MUST 使用 `m2v road-trip basemap`。旧 `article-narrative` 类型与 `m2v article` 命令 MUST 被拒绝。通用作品标准位置 MUST 为 `videos/general/<slug>`；自驾路线与地图游记属于 `route-journey` 类别，其标准位置 MUST 分别为 `videos/route-journey/driving-route/<slug>` 与 `videos/route-journey/road-trip/<slug>`。

#### Scenario: 查询与初始化类型
- **WHEN** 用户查询类型或初始化通用作品
- **THEN** 类型列表包含金融、通用、自驾路线、地图游记及既有正式类型，并按类别显示归属，通用模板与目录采用 general 身份

#### Scenario: 旧入口被拒绝
- **WHEN** 用户指定 article-narrative 类型或执行 m2v article
- **THEN** 系统报告无效类型或命令，不提供兼容分发

#### Scenario: 已移除住宅类型不可使用
- **WHEN** 请求初始化 housing-timeseries，或对标记为该类型的旧作品执行校验、准备、预演、渲染或评审
- **THEN** 系统明确报未知视频类型，不创建新作品、不生成候选、不执行兼容或迁移

#### Scenario: 独立自驾路线入口
- **WHEN** 初始化 driving-route 或对其执行统一生命周期、m2v driving-route fetch 或 m2v driving-route basemap
- **THEN** 使用独立请求及路线材料，标准作品位置为 videos/route-journey/driving-route/<slug>，不要求 general storyboard；底图命令只在授权与 mapTiles 落实时取图

#### Scenario: 独立地图游记入口
- **WHEN** 初始化 road-trip，或对其执行统一生命周期、m2v road-trip fetch 或 m2v road-trip basemap
- **THEN** 使用 trip.json 与每日 routes/day-XX.json，标准作品位置为 videos/route-journey/road-trip/<slug>，不要求 general storyboard；取数与底图命令只在授权与 mapTiles 落实时执行

## ADDED Requirements

### Requirement: 类型类别与父子登记

类型目录 MUST 支持两级的「类别 → 类型」登记。每个类别 MUST 声明唯一标识、非空标题与说明；每个类型 MUST 可选择性地声明唯一一个所属类别。类别标识 MUST 遵循与类型名相同的命名规则，MUST NOT 与任何类型名相同。类别 MUST 至少包含一个类型成员。类别和类型 MUST 共同构成单一来源，供 `m2v types`、初始化路径、作品位置校验、迁移与文档生成消费。

#### Scenario: 登记路线旅程类别
- **WHEN** 类型目录声明类别 `route-journey`（标题「路线旅程」），且 `driving-route` 与 `road-trip` 声明该类别
- **THEN** `m2v types` 显示两个类型同属「路线旅程」，两者的规范作品位置都包含 `route-journey` 层级

#### Scenario: 引用未登记类别
- **WHEN** 某个类型声明了类型目录中不存在的类别标识
- **THEN** 读取类型目录立即失败并指出类型与类别标识，不进入初始化或渲染

#### Scenario: 没有成员的类别
- **WHEN** 类型目录声明了一个没有任何类型引用的类别
- **THEN** 读取类型目录失败并指出该类别，避免留下死分类

#### Scenario: 类别与类型同名
- **WHEN** 某类别标识与某个类型名相同
- **THEN** 读取类型目录失败并指出冲突，不把类别当作类型分发
