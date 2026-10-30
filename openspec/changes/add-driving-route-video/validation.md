# 实施校验与独立审查

## 本轮实施范围

已实现 `driving-route` 类型：独立 `request.json` / `route.json` 材料、`m2v driving-route fetch`、高德定位与高速优先驾车规划客户端、离线校验/准备/预演/渲染、`DrivingRoute` composition、类型指南与文档接入。未创建真实首例，未调用高德服务。

## 自动验证

- `uv run pytest -m "not slow"`：收集 1099 项，全部通过（含新增 52 项自驾路线用例）。
- `pnpm -C web test`：11 个测试文件、149 项通过。
- `pnpm -C web typecheck`、`pnpm -C web build`：通过。
- `uv run python .agents/skills/material2video/scripts/sync_docs.py --check`：通过；阅读预算 entry=1338、plan=2567、iterate=1963、final=1658。
- `openspec validate add-driving-route-video --strict`：通过。
- 合成材料 `prepare` 与 `preview --limit-frames 24`：生成 1920×1080、60 fps、无音轨预演；抽取开场、跟随、结尾帧检查。证据帧保存在被忽略的 `work/driving-route-visual-check/`：开场/收束完整显示路线与两端，跟随时车辆居中且不裁切端点标签，结尾已走路线完整、画面里程等于 API 总距离。
- 合成完整渲染：1800 帧、30.00 秒、1920×1080、60 fps，成片只有视频流；重复导出在 3 秒内复用同一候选，未重新编码。

## 独立审查

独立子代理首轮审查：核心取数、材料校验、离线生命周期与候选绑定无功能性阻断；提出字体未使用登记字体（必改）、道路标签 React key 可能重复（应修），以及超大整数溢出、短路线跟随出画、fetch 落盘竞态、城市校验时机和文档状态等边界问题。

已修复并补测：根样式改用 `var(--m2v-font, "M2V Inter", "M2V Sans", sans-serif)`；标签 key 改为道路名加沿路距离；`_finite_number` 捕获溢出；跟随前瞻限制为当前视域比例；落盘前复核请求摘要并改用唯一临时文件；定位后立即校验城市；design、tasks 与 validation 同步为实施状态。复审确认修复成立、未引入新问题，结论为“复审通过，无阻断项”。

## 真实数据与首例边界

- 1.1、5.1、5.2 未完成：尚未核验高德账号/用途对路线离线留存、二维衍生画面与视频发布的授权依据，未真实取数，未制作上海人民广场→郑州二七广场首例，也未执行首例独立视觉评审。
- Key 已设置在本机用户环境变量中，但当前会话进程未继承；授权落实后，真实 `fetch` 需在新会话中执行或显式读取用户作用域。
- 实现、测试与文档已提交；5.3 仍缺真实取数与首例验收证据，因此不勾选、不归档。
