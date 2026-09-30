## REMOVED Requirements

### Requirement: 迁移保护

**Reason**: 该条要求「迁移已有产物时不得覆盖目标中的同名文件」，对应一个已删除的迁移程序；Python 侧对 `migrate`／迁移的引用为 0，且 `storyboard-v3-contract` 已规定系统不提供迁移命令。判定对象不存在，本条不可验证。

**Migration**: 无需迁移。系统不提供迁移能力；产物归属仍由路径推导给出，同名冲突不再是流程的一部分。

## MODIFIED Requirements

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
该入口文件 SHALL 由工具生成、SHALL NOT 入库，SHALL 落在前端工程所在目录（仓库
`web/.gen/` 下）；入口 SHALL 记录工作区根，使内容根位于仓库之外时作品模块仍能被解析
与打包。

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
- **THEN** 生成的动态入口记录该工作区根并引入该模块，渲染正常完成

#### Scenario: 生成入口不入库
- **WHEN** 生成动态入口之后检查版本控制状态
- **THEN** 入口目录被忽略，不产生待提交的改动
