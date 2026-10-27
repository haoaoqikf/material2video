## ADDED Requirements

### Requirement: 字体来源可恢复

画面注册的字体 SHALL 由字体仓恢复，字体清单的源目录 SHALL 指向字体仓；字体缺失时缺字检查 SHALL 失败并提示恢复入口，SHALL NOT 把缺失当作"无字体可查"的通过状态。

#### Scenario: 字体仓已恢复

- **WHEN** `fonts/fetch.py` 成功完成
- **THEN** 缺字检查读取字体仓中的实际字体并给出既有覆盖结论

#### Scenario: 字体仓未恢复

- **WHEN** 字体清单指向的源文件不存在
- **THEN** 检查失败并提示运行 `uv run python fonts/fetch.py`
