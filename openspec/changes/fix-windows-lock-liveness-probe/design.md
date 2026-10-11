## Context

构建缓存用文件锁串行化「生成全局代码场景清单 → 打包完成」，实现位于 `src/m2v/engine/bundle_cache.py`：`_exclusive()` 以 `O_CREAT | O_EXCL` 建锁并写入持有者 pid，`_reclaim_stale()` 在锁已存在时判断能否回收，`generation_lock()` 是它的调用方。动机见 `proposal.md`。

判断回收的现有逻辑是：

```
dead_owner = owner 已知 and not 持有者存活
if not dead_owner and 年龄 < LOCK_STALE_S:  保持等待
否则:                                        回收锁
```

与本次设计相关的约束：

- `LOCK_STALE_S = 6 小时`，`GENERATION_LOCK_TIMEOUT_S = 1 小时`，`_exclusive()` 在超时后报错退出。
- 引入 pid 探测（提交 `0e5302e`）是为了让「持有者已崩溃退出」的锁不必等满 6 小时即可回收；这个收益需要保留。
- 项目依赖保持精简且可离线（`pyproject.toml` 只有 Playwright、imageio-ffmpeg、edge-tts），不宜为此引入新依赖。
- 仓库在 Windows 上开发，`uv run pytest` 是 README 记载的验收命令。

## Goals / Non-Goals

**Goals:**

- 让存活探测在 Windows 上不产生任何控制台控制事件，不终止当前进程、持有者或同控制台的其它进程。
- 保留「持有者已退出 → 立即回收」的快速路径。
- 让「无法判定」时的行为保守且可预期：宁可继续等待，也不误回收仍有效的锁。
- 不引入新依赖，不改锁文件格式、缓存键与超时/过期阈值。

**Non-Goals:**

- 不把文件锁改造成操作系统级文件租约或跨机器锁（当前锁只服务于本机同一工作区内的串行化）。
- 不改并发渲染参数、缓存键覆盖范围或成片验收标准。
- 不处理 pid 复用导致的历史 pid 被误判为存活的情形（见 Risks）。

## Decisions

### 决策一：Windows 走 Win32 进程句柄查询，POSIX 保留原探测

按平台分支：Windows 使用 `ctypes` 调用 `OpenProcess` + `WaitForSingleObject` 判断目标是否仍在运行；其它平台保留 `os.kill(pid, 0)`——在 POSIX 上它确实是「只探测不发送」的惯用法。

考虑过的替代方案：

- **保留 `os.kill(pid, 0)`**：拒绝。Windows 上 `signal.CTRL_C_EVENT == 0`，该调用会向控制台进程组发送 Ctrl+C。实测 `uv run python -c "import os; os.kill(os.getpid(), 0)"` 使进程以 `0xC000013A` 退出。
- **改用 `os.kill(pid, signal.CTRL_BREAK_EVENT)`**：拒绝。同样是控制台控制事件，问题不变。
- **把控制台事件改用 `TerminateProcess` 路径**：拒绝。探测存活不应有终止进程的副作用。
- **引入 `psutil`**：拒绝。违背精简依赖与离线可用的取向，而 `ctypes` 属标准库。
- **Windows 上直接恒返回「存活」**：拒绝作为主路径，因为它放弃了本次要保留的快速回收收益；但它的语义被采纳为「无法判定」时的兜底。

### 决策二：用等待语义而非退出码判断存活

使用 `WaitForSingleObject(handle, 0)`：返回 `WAIT_OBJECT_0` 表示进程已结束，返回 `WAIT_TIMEOUT` 表示仍在运行。

考虑过的替代方案：`GetExitCodeProcess` 配合 `STILL_ACTIVE (259)` 比较。拒绝，因为一个恰好以 `259` 退出的进程与「仍在运行」无法区分，等待语义没有这个歧义。

访问权限请求 `SYNCHRONIZE`（等待所需）并辅以 `PROCESS_QUERY_LIMITED_INFORMATION`，以尽量降低对权限的要求。

### 决策三：错误映射遵循「不确定即视为存活」

`OpenProcess` 失败时按下述映射：

- `ERROR_INVALID_PARAMETER (87)`：pid 不存在 → 判定为已退出。
- `ERROR_ACCESS_DENIED (5)`：进程存在但无权打开 → 判定为存活。
- 其它错误、或 `ctypes` 调用本身不可用：无法判定 → 判定为存活。

这条映射与规格中「权限不足或查询失败时视为存活」一致。要注意它**不会造成永久死锁**：`_reclaim_stale()` 在「视为存活」之后仍会检查年龄，锁文件一旦达到 `LOCK_STALE_S` 依然会被回收；等待方另有 `GENERATION_LOCK_TIMEOUT_S` 兜底报错。也就是说「不确定」退化为重构前的纯年龄语义，而不是卡死。

### 决策四：以「进程存活」作为可测的观察点

回归测试直接断言探测函数的返回值：对当前进程应返回存活，对已退出的进程应返回已退出。在 Windows 上，旧实现会在第一条断言处杀死测试进程，因此「测试进程能跑完」本身就是该缺陷的回归信号——不需要也无法直接断言「未发送 Ctrl+C」。

## Risks / Trade-offs

- [pid 复用：历史锁记录的 pid 被新进程占用，导致误判为存活] → 保持 `LOCK_STALE_S` 年龄兜底，锁本身是短生命周期的；该暴露面在改动前后相同，本次不扩大也不消除。
- [个别 Windows 环境禁止打开进程句柄] → 归入「无法判定」，按年龄兜底回收，行为退化为重构前语义，不会误回收。
- [`ctypes` 调用写错签名导致未定义行为] → 显式声明 `argtypes`/`restype`，并用「当前进程存活 / 已退出进程」两条路径覆盖。
- [非 Windows 平台缺少回归覆盖] → POSIX 分支保持原实现不变，既有用例继续覆盖；新增用例在两个平台都可运行。
- [测试无法在 CI 之外直接验证「未产生控制台事件」] → 用进程存活这一可观察结果替代，并保留缺陷复现命令在变更文档中。

## Migration Plan

单文件改动，无数据迁移、无锁文件格式变更。

- 上线：合并后在 Windows 执行 `uv run pytest`，确认全量跑完，并单独运行 `tests/test_bundle_cache.py` 确认不再中断。
- 回滚：还原 `src/m2v/engine/bundle_cache.py` 与新增测试即可；已存在的锁文件仍被新旧两版逻辑识别。
- 不需要清理历史锁文件：格式未变，年龄兜底逻辑未变。

## Open Questions

（无。实现所需的技术选择已在本设计中确定，剩余细节属于编码层面。）
