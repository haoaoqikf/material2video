## ADDED Requirements

### Requirement: 包内字体缺失提示恢复

风格包字体资产 SHALL 由字体仓恢复；包内字体缺失时风格加载、校验或准备 SHALL 明确失败，错误信息 SHALL 指向字体恢复命令，SHALL NOT 把缺失字体当作已就绪资产继续渲染。

#### Scenario: 未恢复字体包

- **WHEN** 风格包声明的字体文件尚未恢复
- **THEN** `m2v styles`、`validate` 或 `prepare` 失败并提示恢复

#### Scenario: 恢复后加载

- **WHEN** 字体仓恢复完成且包内字体摘要一致
- **THEN** 风格包正常注册，准备指纹包含该字体
