## Purpose

让文章成为可以离开仓库的内容：仓库只保留制作方法与共享资产，文章与产物可以放在任意内容根里，
而路径推导、共享资产引用与成片溯源在两种位置下行为一致、命令不变。

## ADDED Requirements

### Requirement: 文章内容与仓库解耦

系统 SHALL 把文章内容视为**仓库之外的内容**：仓库 SHALL NOT 跟踪文章目录下的源文件
（`videos/<slug>/`），文章源文件与产物 SHALL 可以位于仓库外的工作区目录。

系统 SHALL 支持两层根：**仓库根**（skill 与共享资产所在处）与**工作区根**
（存放 `videos|examples/<slug>` 与 `outputs/` 的目录）。工作区根 SHALL 按
`--content-root` > `A2V_CONTENT_ROOT` > 仓库根 的优先级解析；未提供两个来源时
工作区根 SHALL 等于仓库根，使既有调用方式与画面保持逐帧不变。

输入文件位于仓库根的规范目录（`videos|examples/<slug>`）时，归属 SHALL 按仓库根判定；
位于其他位置时 SHALL 按工作区根判定。两者都不满足时系统 SHALL 报错，
SHALL NOT 猜测归属，并 SHALL 在错误信息中给出 `--content-root` 与 `A2V_CONTENT_ROOT`
两条设置方式。

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

### Requirement: 跨根的共享资产引用

内容根里的页面 SHALL 能通过服务器别名路径 `/__a2v__/<相对路径>` 引用 skill 的共享样式与脚本，
使页面不必依赖内容根与仓库的相对位置。系统 SHALL 在渲染、预览与体检所用的本地服务器上
把该别名映射到 skill 资产目录，且 SHALL 只映射已声明的前缀。

别名解析 SHALL 拒绝路径穿越（`..`、绝对路径、越出挂载目录的解析结果），
SHALL NOT 因此扩大网页静态根目录。

仓库根内的页面 SHALL 继续可以用相对路径引用共享资产，其画面 SHALL NOT 因为引入别名而改变。

#### Scenario: 内容根页面引用共享资产
- **WHEN** 内容根里的页面用 `/__a2v__/base.css` 与 `/__a2v__/timeline.js` 引用共享资产，并在内容根下渲染
- **THEN** 页面加载到这些资产，时间轴契约可用，成片正常产出

#### Scenario: 别名路径穿越
- **WHEN** 请求 `/__a2v__/../` 或其他越出挂载目录的路径
- **THEN** 服务器拒绝该请求，不返回挂载目录之外的文件

#### Scenario: 渲染前静态扫描覆盖共享资产
- **WHEN** 内容根页面的共享样式表里写了 `animation:` / `transition:`，或共享脚本里用了 `Date.now()` / `Math.random()`
- **THEN** 渲染前的静态提示仍会报出这些写法，不因页面在仓库外而漏扫

### Requirement: 产物归属工作区根

成片、字幕、媒体清单与缓存、限帧预览、体检产物 SHALL 落在**工作区根**的
`outputs/<slug>/` 下；示例产物 SHALL 保持独立的 `outputs/examples/<slug>/` 层级。
显式 `--out`、`--out-dir` SHALL 继续优先。

媒体清单与音轨 SHALL 仍须属于同一篇文章：跨文章合成 SHALL 被拒绝，
判据 SHALL 基于工作区根下的源目录与媒体目录。

#### Scenario: 外置内容根的默认产物位置
- **WHEN** 工作区根为仓库外目录，渲染或体检省略输出参数
- **THEN** 产物写入 `<工作区根>/outputs/<slug>/`，仓库内不新增产物

#### Scenario: 跨文章合成仍被拒绝
- **WHEN** `--storyboard` 属于一篇文章，而 `--media` 指向另一篇文章的媒体目录
- **THEN** 命令报错并拒绝合成
