## 1. 跨平台存活探测

- [ ] 1.1 在 `src/m2v/engine/bundle_cache.py` 中按平台拆分 `_process_is_alive`，Windows 与其它平台各走一支；验证：`uv run python -c "import os; from m2v.engine.bundle_cache import _process_is_alive; print(_process_is_alive(os.getpid()))"` 输出 `True` 且命令退出码为 0（修复前该命令会以 `0xC000013A` 中断）
- [ ] 1.2 实现 Windows 分支：`ctypes` 调用 `OpenProcess`（请求 `SYNCHRONIZE` 与 `PROCESS_QUERY_LIMITED_INFORMATION`）配合 `WaitForSingleObject(handle, 0)`，并显式声明 `argtypes`/`restype`、确保 `CloseHandle` 释放；验证：1.1 的命令在 Windows 返回 `True`，且不产生控制台控制事件
- [ ] 1.3 实现错误映射：`ERROR_INVALID_PARAMETER (87)` 判为已退出，`ERROR_ACCESS_DENIED (5)` 与其它失败判为存活；验证：新增用例覆盖「不可打开的 pid 判为存活」这一分支
- [ ] 1.4 保持 POSIX 分支为原有 `os.kill(pid, 0)`，不改锁文件格式、`LOCK_STALE_S`、`GENERATION_LOCK_TIMEOUT_S` 与缓存键；验证：`git diff` 显示改动限于探测函数与测试，既有 `tests/test_bundle_cache.py` 用例语义未变

## 2. 回归测试

- [ ] 2.1 在 `tests/test_bundle_cache.py` 新增「当前进程判定为存活」用例；验证：该用例在 Windows 通过，且运行它的测试进程不被终止（旧实现会在此处自杀）
- [ ] 2.2 新增「已退出进程判定为已退出」用例：派生一个立即结束的子进程，回收后用其 pid 探测应得已退出；验证：用例通过，且在 Windows 与 POSIX 上均成立
- [ ] 2.3 新增「无法判定时保留锁」用例：让探测返回存活并配合旧锁文件，确认锁不被回收、等待方在超时后报出等待超时错误；验证：用例通过且断言锁文件仍存在
- [ ] 2.4 确认既有并发与过期回收用例仍通过，包括 `test_concurrent_bundles_are_serialized_by_the_generation_lock` 与 `test_lock_from_exited_process_is_reclaimed_before_the_age_threshold`；验证：`uv run python -m pytest tests/test_bundle_cache.py -q -o addopts=""` 全部通过

## 3. 全量验证

- [ ] 3.1 单独运行锁用例文件确认缺陷已消除；验证：`uv run python -m pytest tests/test_bundle_cache.py -q -o addopts=""` 退出码为 0 且不再中途中断
- [ ] 3.2 运行 README 记载的验收命令；验证：`uv run pytest` 全量跑完（901 项）且无失败、无中断
- [ ] 3.3 确认文档无需改动：README 与 Skill 未描述存活探测实现细节，本次修复只是让既有验收命令恢复可用；验证：检查 `README.md`、`.agents/skills/material2video/` 中无需要同步的表述

## 4. 归档与提交

- [ ] 4.1 把增量规格同步进 `openspec/specs/remotion-renderer/spec.md` 主规格，并将变更目录移入 `openspec/changes/archive/`；验证：`openspec list` 无进行中变更，主规格包含新增的两条需求
- [ ] 4.2 提交本次代码、测试与归档结果；验证：`git status` 干净，提交仅包含本变更相关文件（不含被忽略的产物与缓存）
