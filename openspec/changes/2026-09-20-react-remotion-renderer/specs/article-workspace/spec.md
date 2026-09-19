## MODIFIED Requirements

### Requirement: 文章内容与仓库解耦

系统 SHALL 把文章内容视为**仓库之外的内容**：仓库 SHALL NOT 跟踪文章目录下的源文件
（`videos/<slug>/`），文章源文件与产物 SHALL 可以位于仓库外的工作区目录。

系统 SHALL 支持两层根：**仓库根**（前端工程与共享组件所在处）与**工作区根**
（存放 `videos|examples/<slug>` 与 `outputs/` 的目录）。工作区根 SHALL 按
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
- **THEN** 工作区根为仓库根，源目录为该文章目录，产物写入 `<仓库根>/outputs/<slug>/`

#### Scenario: 内容根指向仓库外
- **WHEN** `--content-root` 或 `A2V_CONTENT_ROOT` 指向仓库外目录，输入文件位于 `<内容根>/videos/<slug>/`
- **THEN** 源目录为该文章目录，产物写入 `<内容根>/outputs/<slug>/`，且命令与工作目录无关

#### Scenario: 仓库内优先
- **WHEN** 已设置内容根，而输入文件位于仓库根的 `examples/<slug>/`
- **THEN** 归属仍按仓库根判定，产物写入 `<仓库根>/outputs/examples/<slug>/`

#### Scenario: 无法推导归属
- **WHEN** 输入文件既不在仓库根的 `videos|examples/<slug>` 内，也不在已解析的工作区根内
- **THEN** 命令报错并列出实际路径，错误信息包含 `--content-root` 与 `A2V_CONTENT_ROOT`

#### Scenario: 内容根里的作品带专属画面
- **WHEN** 作品与它的专属画面模块位于仓库外的内容根下
- **THEN** 生成的动态入口按工作区根解析并引入该模块，渲染正常完成

#### Scenario: 生成入口不入库
- **WHEN** 生成动态入口之后检查版本控制状态
- **THEN** 入口目录被忽略，不产生待提交的改动

## REMOVED Requirements

### Requirement: 跨根的共享资产引用

**Reason**: 该能力解决的是「内容根里的 HTML 页面用 `/__a2v__/<文件>` 别名引用仓库内的共享样式与脚本」。
迁移到前端工程后，共享组件、样式与字体在**构建期**被编译进画面实现，作品不再从内容根引用共享资产，
别名机制因此没有消费者。保留一个没有消费者的跨根 HTTP 别名只会扩大静态服务器的暴露面。

**Migration**: 作品去掉对 `/__a2v__/<文件>` 的引用，专属画面改为工作区根下的 React 模块
（见上文「文章内容与仓库解耦」）。共享资产由前端工程统一提供，作品不需要也不应该再声明它们的位置。
渲染前的禁用写法静态检查 SHALL 改为对画面实现源码与生成入口做检查，
SHALL NOT 因为别名机制退出而漏掉共享组件——那正是当初引入别名扫描要堵的口子。
