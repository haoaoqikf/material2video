## Purpose

让文章成为可以离开仓库的内容：仓库只保留制作方法与共享组件，文章与产物可以放在任意内容根里，
而路径推导、专属画面接入与成片溯源在两种位置下行为一致、命令不变。

## Requirements

### Requirement: 文章内容与仓库解耦
系统 SHALL 保持文章内容及产物不入主项目Git，允许通过 --content-root 或 M2V_CONTENT_ROOT 创建作品。初始化默认归属仍为 videos/<type>/<slug>，七例仍为 examples/<type>/<slug>；已有独立作品 SHALL 能在任意目录直接执行或通过显式 --project 使用，SHALL NOT 为运行强制要求上级目录名称或主项目标记。作品 SHALL 拥有全部本地运行输入，SHALL NOT 生成主项目web/.gen入口、挂载主项目资源或读取共享依赖。

#### Scenario: 任意位置运行
- **WHEN** 独立作品被复制到含空格的新目录，未设置内容根且主项目不存在
- **THEN** 按作品自身说明可恢复、构建、预览与导出，所有产物归作品。

#### Scenario: 初始化内容根
- **WHEN** 使用显式内容根或环境变量初始化任一五类作品
- **THEN** 仍按显式参数优先于环境变量、环境变量优先于仓库根的顺序选择创建位置，创建完整独立工程。

#### Scenario: 未设置内容根
- **WHEN** 初始化时没有内容根参数或环境变量
- **THEN** 默认在主项目videos/<type>/<slug>创建完整工程，生成后执行不依赖该父目录。

#### Scenario: 内容根指向仓库外
- **WHEN** 初始化时内容根指向仓库外
- **THEN** 在指定内容根创建完整工程，恢复和运行不需要主项目web目录。

#### Scenario: 仓库内优先
- **WHEN** 已设置内容根而显式操作仓库内的独立示例
- **THEN** 始终使用被显式选中的示例根，输出保留在该示例目录。

#### Scenario: 无法推导归属
- **WHEN** 显式作品路径不是有效独立工程且无法读取其manifest
- **THEN** 明确报告实际作品路径和缺失／无效材料，不猜测其他作品；独立有效工程不因位于任意目录而失败。

#### Scenario: 内容根里的作品带专属画面
- **WHEN** 作品和场景位于仓库外
- **THEN** 构建使用作品自身入口、配置及依赖，不向主项目写动态入口。

#### Scenario: 生成入口不入库
- **WHEN** 作品构建生成临时入口
- **THEN** 入口只位于作品忽略的缓存／输出目录，不向主项目写文件。

### Requirement: 产物归属作品目录

默认产物 MUST 位于对应作品目录下的 `outputs/` 子目录，并保留 `outputs/` 内部布局。

#### Scenario: 正式作品默认输出

- **WHEN** 文章位于 `videos/text-motion/demo/`
- **THEN** 默认媒体、预览、检查报告、字幕、溯源和成片写入 `videos/text-motion/demo/outputs/`

#### Scenario: 示例作品默认输出

- **WHEN** 随附示例作品归属为 `examples/<type>/<slug>/`
- **THEN** 默认产物写入 `examples/<type>/<slug>/outputs/`，与正式作品隔离，且继续由 `.gitignore` 的 `outputs/` 规则排除

#### Scenario: 外部内容根

- **WHEN** `--content-root` 或 `M2V_CONTENT_ROOT` 指向外部内容根
- **THEN** 使用该内容根下的 `videos/<类型路径>/<slug>/outputs/` 同构路径

#### Scenario: 显式输出参数

- **WHEN** 用户传入 `--out` 或 `--out-dir`
- **THEN** 显式路径优先，继续保持原有兼容行为

#### Scenario: 外置内容根的默认产物位置

- **WHEN** 工作区根为仓库外目录，渲染或体检省略输出参数
- **THEN** 产物写入 `<工作区根>/videos/<类型路径>/<slug>/outputs/`，仓库内不新增产物

#### Scenario: 跨文章合成仍被拒绝

- **WHEN** `--storyboard` 属于一篇文章，而 `--media` 指向另一篇文章的媒体目录
- **THEN** 命令报错并拒绝合成
