## MODIFIED Requirements

### Requirement: 版本 3 渲染契约

系统 SHALL 提供一个可被浏览器自动化驱动的契约页，把共享 composition 挂载为可寻址的帧序列，
并在 `window.__M2V__` 上暴露 `version`、`fps`、`width`、`height`、`durationInFrames`、
`ready()` 与 `seekToFrame(frame)`。

`version` SHALL 为 `3`。`ready()` SHALL 在字体、当前作品代码 bundle、首批本地资源就绪
且第 0 帧已绘制后 resolve。`seekToFrame(frame)` SHALL 把画面切换到第 frame 帧、暂停播放，
并在场景树或代码场景的画面更新完成后 resolve；`frame` 从 `0` 开始，
最大值为 `durationInFrames - 1`。

契约 SHALL 由 Remotion 的 Player 实现，SHALL NOT 由每个作品自行实现。
`seekToFrame` 返回后，所有场景组件观察到的当前帧 SHALL 等于 `frame`。

契约页 SHALL 另外暴露当前帧的只读诊断读数，供验收流程在量测失败时判断画面停在何处；
该读数 SHALL NOT 参与 `seekToFrame` 的语义。

#### Scenario: 契约可用

- **WHEN** 浏览器打开契约页并调用 `ready()` 与 `seekToFrame(f)`
- **THEN** 两者按上述语义 resolve，且场景树和代码场景观察到的帧号均等于 `f`

#### Scenario: 声明与分镜不一致

- **WHEN** 契约页报告的 `fps`、`width`、`height` 或 `durationInFrames` 与分镜不一致
- **THEN** 渲染入口报错终止并列出两边的值

#### Scenario: 作品代码或本地资源未就绪

- **WHEN** 代码场景 bundle、字体或首批本地资源加载失败
- **THEN** `ready()` 失败并给出原因，不截取未完成画面

#### Scenario: 版本不匹配

- **WHEN** 页面暴露的 `__M2V__` 版本不是 `3`
- **THEN** 渲染入口报错终止并说明当前支持的契约版本
