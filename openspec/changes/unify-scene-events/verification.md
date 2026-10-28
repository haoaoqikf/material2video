# 验证与独立审查

## 功能与逻辑

- 事件声明拒绝重复、未知字段、空ID、布尔/小数/负帧及越界；自动幕长在 prepare 后复核。
- 音效事件引用拒绝缺失事件与混合时间基准；事件帧偏移后仍须处于本幕。既有幕/旁白段音效语义保留。
- 准备集成测试验证改事件15帧后，解析起点、事件清单、音轨摘要、准备指纹和场景配置共同变化，旧准备不可使用。
- 两项真实浏览器测试通过：复利首片落点30→45帧与音效一致；局部第30帧PNG与较长窗口完全一致；特殊事件ID `__proto__`、`</script>` 可传输和查询；动作、计数、强调共同后移15帧。
- SDK 测试覆盖乱序、重复、子帧求值、输入快照和非法参数。

## 验证命令

- Python 相关回归：`uv run pytest tests/test_scene_events.py tests/test_article_sound.py tests/test_sound_library.py tests/test_compound_interest_example.py tests/test_general_frame_rate.py tests/test_examples_strict.py tests/test_code_scenes.py tests/test_cinematic_storyboard.py -m "not slow" -o addopts="" -q -p no:cacheprovider`。Windows 合并运行须设置 `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`，避免示例媒体恢复子进程的GBK输出破坏pytest捕获；初次未设置时137项通过后出现编码错误，分组运行通过。
- 两项真实浏览器：`uv run pytest tests/test_scene_events.py::test_real_compound_event_shift_and_local_capture tests/test_scene_events.py::test_browser_event_state_and_special_ids`。
- `pnpm -C web test`：137项通过；`pnpm -C web typecheck`、`pnpm -C web build`通过，构建保留既有大包提示。
- `sync_docs.py --check`、变更Markdown相对链接目标、`git diff --check`和OpenSpec严格校验通过。

UTF-8环境的合并回归最终结果：216项通过、14项慢测试未选中，耗时66.24秒；本功能的两项浏览器慢测试另行执行通过。

## 独立审查

独立子代理 `review_events` 完成代码审查并复查，发现P2：直接嵌入对象字面量导致 `__proto__` 事件键丢失。已改为安全的JSON字符串加 `JSON.parse` 注入，保留小于号转义，并以真实浏览器回归验证；复查确认关闭，无剩余阻断缺陷。独立代理重新执行事件测试（含浏览器）通过；其他回归和生产构建采用主代理结果。

## 性能与边界

每次准备线性解析事件与音效，SDK事件查询为常数时间，建议按配置memo初始化。最大单幕1024事件+128音效，100轮解析中位数0.593ms、最大1.761ms，低于本轮50ms中位数检查目标。配置注入增加一次JSON解析，不增加逐帧扫描或I/O。

本轮交付功能而非重制视频：未生成完整正式成片或重新作全片审美评审，复利历史验收不覆盖当前材料。事件保证声明时间共用，不证明音效素材内部瞬态与动作主观听感一致，也不自动发现未引用的时间常量。无新增依赖、媒体或字体入库。

审查质量评分95/100：核心接线、边界、缓存与真实采集已覆盖；扣分主要为未执行完整正式成片回归与全片观感检查。
