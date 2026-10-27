## ADDED Requirements

### Requirement: 屏幕字幕量测角色

制作合同 MAY 在检查点 `measurement` 声明 `subtitleRoles`（非空字符串列表）。对命中角色的可见元素，量测 SHALL 检查包围盒完全落在字幕安全区内、文本不含换行、且不发生横向溢出；不满足时 SHALL 判失败。该规则 SHALL 为可选，未声明时不改变现有量测结果，也不替代 `subtitleTop` 对正文越界的检查。

#### Scenario: 屏幕字幕在安全区内

- **WHEN** 检查点声明 `subtitleRoles: ["subtitle"]`，且该角色元素的包围盒在字幕安全区内、单行、未溢出
- **THEN** 量测判定通过

#### Scenario: 屏幕字幕越界或溢出

- **WHEN** 屏幕字幕超出安全区、包含换行或横向溢出
- **THEN** 量测判定失败，并记录实际包围盒与安全区

#### Scenario: 未声明角色

- **WHEN** 检查点没有声明 `subtitleRoles`
- **THEN** 不产生新的量测项，既有结果不变
