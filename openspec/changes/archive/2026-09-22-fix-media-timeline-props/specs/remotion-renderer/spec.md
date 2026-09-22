# remotion-renderer 变更（delta）

## MODIFIED Requirements

### Requirement: Python 入口与 Node 渲染器分工

系统的命令行入口 SHALL 继续由现有脚本提供，并 SHALL 保持现有参数与默认输出位置。
路径归属推导、分镜与作品源码校验、配音与字幕准备、体检与溯源 SHALL 继续由 Python 侧编排；
当前作品代码场景的静态清单生成、前端打包、逐帧渲染与编码 SHALL 交给 Node 侧工具链。

渲染入口 SHALL NOT 要求用户预先进入前端工程目录，也 SHALL NOT 依赖调用时的工作目录。
作品源码位于仓库外内容根时，系统 SHALL 通过显式内容根解析并只纳入当前作品允许的文件。

启用配音媒体清单时，系统 SHALL 把清单派生的分镜时长（每幕实际 `durationInFrames`）
写回源分镜快照形成有效分镜，并 SHALL 把有效分镜作为 composition 的 props 提供给
契约页与 Remotion 渲染；SHALL NOT 让画面按声明时长运行而音轨按派生时长合成。
代码场景清单与作品归属的解析 SHALL 继续使用原始分镜路径。

#### Scenario: 命令不变

- **WHEN** 用户沿用既有的校验、预览、渲染、体检命令处理声明式或代码场景
- **THEN** 参数含义与产物位置不变，渲染由共享 Node 侧工具链完成

#### Scenario: 缺少前端依赖

- **WHEN** 前端工程依赖未安装而用户直接渲染
- **THEN** 命令报错并说明需要先安装前端依赖，SHALL NOT 产出一个空成片

#### Scenario: 渲染期离线

- **WHEN** 依赖已安装，字体、作品源码和资产均为本地文件，渲染时无网络
- **THEN** 声明式场景与代码场景均正常完成渲染

#### Scenario: 外部内容根中的代码场景

- **WHEN** 分镜和代码场景位于显式内容根中的规范作品目录
- **THEN** 系统从该内容根解析模块和素材，输出仍按该作品归属推导

#### Scenario: 有声渲染的 props 时间轴

- **WHEN** 带 `--media` 渲染、预览或评审
- **THEN** composition 的 props 使用媒体清单派生的延长时长，总帧数与派生时间轴一致；
  体检抽帧与契约页使用同一条时间轴

#### Scenario: 无声路径不受影响

- **WHEN** 不带 `--media` 渲染、预览或评审
- **THEN** props 与页面 URL 仍指向原始分镜，行为与产物不变
