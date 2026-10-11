## Why

构建缓存锁用于串行化「生成全局代码场景清单 → 打包完成」这一段，防止并发生成互相覆盖清单。最近一次重构（提交 `0e5302e`）为「持有进程已退出」的快速回收引入了 pid 存活探测 `os.kill(pid, 0)`。

这是 POSIX 惯用法，在 Windows 上不成立：`signal.CTRL_C_EVENT` 的值就是 `0`，因此该调用等价于 `GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid)`，会向控制台进程组发送 Ctrl+C。实测 `uv run python -c "import os; os.kill(os.getpid(), 0)"` 使进程以 `0xC000013A`（`STATUS_CONTROL_C_EXIT`）退出。

后果有两层：一是 `tests/test_bundle_cache.py` 在 Windows 上必然杀死自身进程，导致 README 记载的验收命令 `uv run pytest` 稳定停在 15%–18%（901 个用例只跑到约 176 个）；二是生产路径同样会走到该探测——并发构建共享同一控制台时会互相中断，而若目标 pid 不是进程组，`GenerateConsoleCtrlEvent` 会以 `winerror 87` 失败并被现有代码判为「持有者已退出」，从而提前回收仍然有效的锁，恰好绕过这把锁要提供的串行化保护。

## What Changes

- 锁持有者的存活判定改为跨平台实现：Windows 使用 Win32 进程句柄查询，POSIX 保留原有的 `os.kill(pid, 0)` 探测。
- 明确「无法判定」时的保守语义：查询被拒绝或调用失败时一律视为持有者仍存活，宁可等待也不误回收锁。
- 新增针对该行为的回归测试，覆盖「当前进程存活」与「进程已退出」两条路径，并确保在 Windows 上不产生任何控制台控制事件。
- 不改动缓存键、锁文件格式、锁超时与过期阈值，也不引入新依赖。

## Capabilities

### New Capabilities

（无。本次不引入新能力，只修正既有并发保护在 Windows 上的行为。）

### Modified Capabilities

- `remotion-renderer`: 新增需求，规定构建锁持有者存活判定必须跨平台安全，且无法判定时不得回收锁。

## Impact

- `src/m2v/engine/bundle_cache.py`：`_process_is_alive` 的实现与 `_reclaim_stale` 的判定语义。
- `tests/test_bundle_cache.py`：新增回归测试；既有用例恢复可在 Windows 下完整运行。
- 依赖与契约：不新增第三方依赖，不变更缓存键、锁文件内容格式、`LOCK_STALE_S` 与 `GENERATION_LOCK_TIMEOUT_S`。
- 验证方式：`uv run pytest` 全量恢复可跑通；`tests/test_bundle_cache.py` 单独运行不再中断。
