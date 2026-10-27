# 字体仓

字体二进制**不入库**。来源、版本、摘要、许可与恢复目标以 `registry.json` 为准，`fetch.py` 负责离线恢复与校验。

## 恢复

```powershell
uv run python fonts/fetch.py --check     # 只校验，不写文件
uv run python fonts/fetch.py             # 从本地缓存恢复
uv run python fonts/fetch.py --download  # 缓存缺失时联网（仅登记了下载地址的字体）
```

恢复后字体落在：

- `fonts/files/`：唯一本地副本；
- `registry.json` 的 `targets`：web 注册目录与风格分包内目录。

首次使用或 fresh clone 后，在 `pnpm -C web build`、`uv run m2v prepare` 或 `uv run m2v render` 之前执行一次。

## 离线缓存

把字体文件放进以下任一位置即可离线恢复：

1. `M2V_FONT_CACHE` 指向的目录；
2. `fonts/.cache/`；
3. 原目标位置（例如 `web/src/assets/fonts/`）。

文件必须与 `registry.json` 的字节数和 SHA-256 一致；不一致时脚本拒绝覆盖并说明差异。

## 许可

`licenses/` 中的 OFL 文本随仓库分发。恢复或构建字体时，许可证必须与字体一起分发，不得删除。

## 新增或升级字体

1. 在 `registry.json` 增加或修改登记项：来源、版本、字节数、SHA-256、许可与 targets；
2. 把文件放入缓存并执行 `uv run python fonts/fetch.py`；
3. 同步 `web/src/assets/fonts.json`（web 注册语义）与相关文档；
4. 用缺字检查与构建验证，确认没有回退到系统字体。

字体升级属于兼容性变更：摘要变化会使准备与片段缓存失效，需要重新 `prepare`。

## 故障处理

| 现象 | 处理 |
| --- | --- |
| `字体文件缺失` | 运行 `uv run python fonts/fetch.py`；没有网络时先把文件放入缓存 |
| `摘要不符` | 不要覆盖；确认拿到的字体版本与登记一致，必要时更新登记 |
| 风格包加载失败 | 包内字体由 `fetch.py` 复制，先恢复再 `validate`/`prepare` |
| 构建失败 | 先恢复字体；构建不会静默使用系统字体 |
