# 验证摘要

验证日期：2026-10-29。以下仅保留通用回归和其他作品记录。

## 合同与回归

- 全量非慢速测试在 `PYTHONIOENCODING=utf-8` 下通过（默认 Windows 控制台编码会让 pytest 捕获子进程中文输出时解码失败，属环境问题，与本变更代码无关）；web `pnpm typecheck` 通过；`pnpm test` 11 个文件 / 137 个用例通过。
- 三个固定示例 `validate` 均通过。仓库内既有金融与住宅作品 `videos/financial-timeseries/apple-since-2007`、`videos/housing-timeseries/zhengzhou-housing-2002-2024` 仍为旧 30fps 材料，按现行 60fps 契约校验失败；这些文件本轮未改动，属于版本升级后的既有材料不兼容，不是本变更引入的回归。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
