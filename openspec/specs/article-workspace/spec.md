## Purpose

让文章成为可以离开仓库的内容：仓库只保留制作方法与共享组件，文章与产物可以放在任意内容根里，
而路径推导、专属画面接入与成片溯源在两种位置下行为一致、命令不变。

## Requirements

### Requirement: 文章内容与仓库解耦

系统 SHALL 把文章内容视为**仓库之外的内容**：仓库 SHALL NOT 跟踪文章目录下的源文件
（`videos/<slug>/`），文章源文件与产物 SHALL 可以位于仓库外的工作区目录。

系统 SHALL 支持两层根：**仓库根**（前端工程与共享组件所在处）与**工作区根**
（存放 `videos|examples/<slug>` 与作品目录下 `outputs/` 的目录）。工作区根 SHALL 按
`--content-root` > `A2V_CONTENT_ROOT` > 仓库根 的优先级解析；未提供两个来源时
工作区根 SHALL 等于仓库根。

输入文件位于仓库根的规范目录（`videos|examples/<slug>`）时，归属 SHALL 按仓库根判定；
位于其他位置时 SHALL 按工作区根判定。两者都不满足时系统 SHALL 报错，
SHALL NOT 猜测归属，并 SHALL 在错误信息中给出 `--content-root` 与 `A2V_CONTENT_ROOT`
两条设置方式。

作品的专属画面以工作区根下的 React 模块声明，系统 SHALL 据此生成前端工程的动态入口。
该入口目录 SHALL 由工具生成、SHALL NOT 入库，其位置 SHALL 解析自工作区根，
使内容根位于仓库之外时作品仍能被渲染。

#### Scenario: 未设置内容根
- **WHEN** 既没有 `--content-root` 也没有 `A2V_CONTENT_ROOT`，输入文件位于仓库的 `videos/<slug>/`
- **THEN** 工作区根为仓库根，源目录为该文章目录，产物写入 `<仓库根>/videos/<slug>/outputs/`

#### Scenario: 内容根指向仓库外
- **WHEN** `--content-root` 或 `A2V_CONTENT_ROOT` 指向仓库外目录，输入文件位于 `<内容根>/videos/<slug>/`
- **THEN** 源目录为该文章目录，产物写入 `<内容根>/videos/<slug>/outputs/`，且命令与工作目录无关

#### Scenario: 仓库内优先
- **WHEN** 已设置内容根，而输入文件位于仓库根的 `examples/<slug>/`
- **THEN** 归属仍按仓库根判定，产物写入 `<仓库根>/videos/examples/<slug>/outputs/`

#### Scenario: 无法推导归属
- **WHEN** 输入文件既不在仓库根的 `videos|examples/<slug>` 内，也不在已解析的工作区根内
- **THEN** 命令报错并列出实际路径，错误信息包含 `--content-root` 与 `A2V_CONTENT_ROOT`

#### Scenario: 内容根里的作品带专属画面
- **WHEN** 作品与它的专属画面模块位于仓库外的内容根下
- **THEN** 生成的动态入口按工作区根解析并引入该模块，渲染正常完成

#### Scenario: 生成入口不入库
- **WHEN** 生成动态入口之后检查版本控制状态
- **THEN** 入口目录被忽略，不产生待提交的改动

### Requirement: 产物归属作品目录

默认产物 MUST 位于对应作品目录下的 `outputs/` 子目录，而不是工作区根下的独立产物树。

#### Scenario: 正式作品默认输出

- **WHEN** 文章位于 `videos/demo/`
- **THEN** 默认媒体、预览、检查报告、字幕、溯源和成片写入 `videos/demo/outputs/`

#### Scenario: 示例作品默认输出

- **WHEN** 示例文章归属为 `examples/demo/`
- **THEN** 默认产物写入 `videos/examples/demo/outputs/`，并与正式作品隔离

#### Scenario: 外部内容根

- **WHEN** `--content-root` 或 `A2V_CONTENT_ROOT` 指向外部内容根
- **THEN** 使用该内容根下的 `videos/<slug>/outputs/` 同构路径

#### Scenario: 显式输出参数

- **WHEN** 用户传入 `--out` 或 `--out-dir`
- **THEN** 显式路径优先，继续保持原有兼容行为

#### Scenario: 外置内容根的默认产物位置

- **WHEN** 工作区根为仓库外目录，渲染或体检省略输出参数
- **THEN** 产物写入 `<工作区根>/videos/<slug>/outputs/`，仓库内不新增产物

#### Scenario: 跨文章合成仍被拒绝

- **WHEN** `--storyboard` 属于一篇文章，而 `--media` 指向另一篇文章的媒体目录
- **THEN** 命令报错并拒绝合成

### Requirement: 迁移保护

迁移已有产物时 MUST NOT 覆盖目标中的同名文件。

#### Scenario: 迁移目标存在冲突

- **WHEN** 目标路径中已有与源文件同名的文件
- **THEN** 迁移停止并报告冲突，不修改冲突文件
