## MODIFIED Requirements

### Requirement: 风格示例作品（视频专属，不属于包）

仓库 SHALL 在 `styles/deep-journey/examples/solar-system-journey/` 提供规范示例，声明 `style.id: "deep-journey"`。该作品 SHALL 保持单幕一镜到底、15 段旁白、31 个首尾相接的镜头、60 fps、路径与换站空间过渡、独立行星视觉分离与分段节奏；旁白、字幕、配乐与音效沿用原作品契约。示例 SHALL 通过 v8 校验与 `prepare`，生成媒体 SHALL NOT 入库。天体数据、纹理、路径、分镜、旁白与声音属于作品，SHALL NOT 进入共享风格实现或风格指纹。示例使用逐帧 3D 回调时 SHALL NOT 声明 `capture.mode: "pure-time"`。

#### Scenario: 示例可校验

- **WHEN** 对 `styles/deep-journey/examples/solar-system-journey/` 运行 `m2v validate` 与 `prepare`
- **THEN** 校验通过，单幕、60 fps、15 段旁白与 31 个镜头保持，路径首尾相接

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** `styles/deep-journey/examples/solar-system-journey` 不出现在风格清单中，也不能按风格 id 加载
