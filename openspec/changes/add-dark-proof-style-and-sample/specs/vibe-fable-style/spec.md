## MODIFIED Requirements

### Requirement: 风格示例必须可校验并与包分离

仓库 SHALL 在目录 `styles/<style-id>/examples/<slug>/` 为每个正式风格提供规范示例：`vibe-night/fold`、`vibe-fable/pigeon`、`doc-archive/american-science-milestones`、`count-ledger/compound-interest`、`deep-journey/solar-system-journey` 与 `dark-proof/sample`。示例 SHALL 声明其演示的 `style.id` 并通过 v8 契约校验；其旁白与文字模式 SHALL 与所属风格契约一致：`vibe-night` / `vibe-fable` / `dark-proof` 无旁白并使用屏幕字幕，`doc-archive` / `count-ledger` 无旁白且文字画在场景内，`deep-journey` 保留旁白与共享字幕。风格发现 SHALL 只读取 styles 的直接子目录，SHALL NOT 把示例目录当作风格包。示例 SHALL NOT 改变其他风格的示例集合，也 SHALL NOT 改变任何风格包的指纹。

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 返回六个风格包，各风格的 `examples/` 及其子目录不出现在清单中

#### Scenario: 示例改动不使作品准备失效

- **WHEN** 修改某个风格示例的文件
- **THEN** 使用该风格的作品准备指纹不变，只有该示例自身的准备需要重做

#### Scenario: 示例可校验

- **WHEN** 对 `styles/<style-id>/examples/<slug>/` 下的六个示例运行 `m2v validate`
- **THEN** 校验通过；`vibe-night/fold`、`vibe-fable/pigeon` 与 `dark-proof/sample` 的屏幕字幕在字幕安全区内、无旁白且引用存在的场景入口，其余示例按其风格声明的旁白与文字模式通过校验
