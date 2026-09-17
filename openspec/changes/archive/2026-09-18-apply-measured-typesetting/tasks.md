## 1. 让取档不再破坏标记

- [x] 1.1 改 `assets/typography.js` 的 `applyFit`：均衡断行时按文本节点重排，保留 `.key`、`.key-underline` 等元素子节点结构；结构无法安全映射时退回「只取字号、不改文案」，并在结果里记 `balanced: false`；以「取档后去掉换行符的字符序列与取档前完全相同」为验证。（新增 `reflow` / `canReflow` / `significant`，并导出以便直接测试；重排按代码点映射回原文本节点，换行追加在「前一个字符所属节点」末尾。）
- [x] 1.2 为 `applyFit` 补退化路径单测：空串、纯空白、单字符、含 `\n` 硬换行、含强调元素的混合文案；以 `uv run pytest tests/test_typography.py` 全绿为证。（`tests/test_typesetting_apply.py`，15 项通过。）
- [x] 1.3 加「同一帧重复取档不产生写入」的测试：对同一元素连续取档两次，第二次不得改动 `style` 与 `textContent`；以测试通过为证。（根因是签名用 `textContent`，重排会移动换行位置导致每帧重判为「内容变了」；改用有效字符做签名。）

## 2. 组件接入引擎

- [x] 2.1 为承载任意文案的组件文本元素声明 `data-a2v-fit="<档位>"`（至少 `.quote-text`、`.title-text`、`.closing-text`、列表与时间线的条目文字、对比场景的左右文字），档位取该元素在预设下的现有字号档；以「声明前后同一文案的取档结果等于样式表字号」为验证。（落点是 `.title-text`=display、`.quote-text`=lead、`.fig-number-label`=title、`.section-title`/`.stair-caption`/`.fig-number-caption`/`.closing-action`=body、`.vs-note`=caption；`.closing-text` 是逐字揭示结构，按安全判定不重排，故不声明；44px 的 `.title-sub-line`/`.vs-text` 不是字阶档位，不声明。同时把 `keynote.css` 的档位规则收成只声明字号——原先它连同档位的行高、字距、字重一起接管，会把 `.section-title` 的 0.14em 标签字距静默换掉。）
- [x] 2.2 用 `tests/test_keynote_layout.py` 的实测探针加一条一致性测试：在真实页面里取每个声明了档位的元素，断言引擎取到的字号等于其预设计算字号，且取档只发生在预设页面；以测试通过为证。（新增 `tests/test_typesetting_wiring.py`，走遍 8 幕；预设页面 11 个声明元素全部 `level == declared` 且实测字号 == `--a2v-size-*`，非预设页面零取档痕迹。）
- [x] 2.3 逐字节回归：`examples/keynote-baseline`（预设页面）与 `examples/declarative-number`（非预设页面）各做一次限帧 PNG 导出，SHA256 必须与接线前相同；以两次哈希比对为证。（非预设：`DAFDD423…208D31`，与接线前逐字节相同。预设：接线前 `7A0AC1EB…`／接线后一度 `CF0CF621…`，差异定位到 `keynote.css` 的档位规则把 display 档的行高字距一并接管；收成只声明字号后，8 幕各取 3 帧共 **24 帧逐像素一致**。）

## 3. 溢出闸门

- [x] 3.1 扩展 `scripts/a2v/inspect.py`：记录每个正文级文本块的墨迹边界（左右上下）与容器边界，供溢出判定使用；以产物 `report.json` 中出现该字段为证。（`texts[]` 增加 `right`/`top`/`bottom` 与 `block`——向上找到第一个非行内容器；`facts.safe` 给出安全区四边；`facts.noFit` 收集 `data-a2v-fit-fits="false"` 的元素。）
- [x] 3.2 在 `scripts/a2v/keynote.py` 增加溢出判定：正文级文本块墨迹越出安全区时按**错误**报告，给出文案、越界方向与实测像素值；引擎报告 `fits: false` 时报「需要拆场景」；以构造的越界合成帧报错、正常示例不报错为证。（新增 `gate_overflow`（K7）与 `_OVERFLOW_TOLERANCE = 8.0`；`applyFit` 把 `data-a2v-fit-fits` 写到元素上。负例：给开场幕注入 350 字副标题后报「硬判定：越出安全区：「title-text」上越界 285.2px」；`examples/keynote-baseline` 8 幕全通过，`report.json` 里 K7 共 8 条、汇总 0 失败。）
- [x] 3.3 在 `scripts/a2v/constitution.py` 与 `scripts/review.py` 中把溢出判定与既有的「可放行提醒」区分开报告，终端与 `report.json` 都要能看出它是硬判定；以 `review.py --declarative` 在 `examples/keynote-baseline` 上的输出为证。（新增 `cli._HARD_GATES = ("K7",)` 与 `cli._apply_hard_gates`：K7 失败并入错误列表，负例的「体检完成」从 0 个错误变成 1 个、退出码从 0 变成 2；顺带修掉 CLI 只对「跳过」显示 detail 的问题——硬判定失败原本看不到是哪段文字往哪个方向越界。设计宪法补上「K7 是 K 系列里的例外」。）
- [x] 3.4 为溢出闸门补测试：构造文字越出安全区的合成画面，断言报错条目包含越界方向与实测值；以 `uv run pytest tests/test_review.py` 全绿为证。（`TestOverflowGate` 8 项 + `TestHardGateReachesTheVerdict` 4 项：8px 容差、方向与像素值、按文本块归并取最大越界量、`fits: false` 判「需要拆场景」、无安全区几何时跳过、K7 已接入逐帧结论、K7 失败进错误数而 K2 不进。）

## 4. 文档同步

- [x] 4.1 更新 `references/keynote-design-system.md`：把排版引擎一节改成「引擎由组件声明接入」，列出哪些元素必须声明档位，并写清「未声明的元素不会被改动」。
- [x] 4.2 更新 `references/visual-spec.md` 与 `references/design-constitution.md`：补上溢出闸门及其硬判定性质，并说明它与「观感提醒」的分工。
- [x] 4.3 更新 `SKILL.md`：在制作流程里写明「新增组件文本元素时要声明档位」，把这一次修掉的三处失效（引擎空转、取档抹掉强调、引擎与 CSS 双真源）写进静默失效清单。（静默失效清单从 6 条扩到 11 条，新增的 5 条是本次实测出来的：引擎空转、取档抹掉强调标记、引擎与 CSS 双真源、可用宽度量的是自己、溢出无人管。）

## 5. 验收

- [x] 5.1 用启用预设的示例走通「校验 → 预览 → 限帧导出 → 视觉评审」：`validate.py --declarative --strict` 零错误、`review.py` 的 C 系列零错误、溢出判定零错误；以命令输出与 `report.json` 为交付物。（`review.py --declarative`：24 帧抽检 0 错误 0 提醒；K1–K7 共 38 通过 / 7 提醒 / 0 失败 / 11 跳过；`report.json` 的 `errors` 为空。）
- [x] 5.2 用一段**明显过长**的文案做负例：导出一幕，确认溢出被闸门判错且报出越界方向；以闸门输出为交付物。（350 字副标题 → `[opening] K7 文字溢出：实测 1；硬判定：越出安全区：「title-text」上越界 285.2px`，同时 `[error] opening: 文字溢出：…`、错误数 1、退出码 2。负例夹具建在 `examples/_neg-overflow/` 且已删除，未入库。）
- [x] 5.3 运行 `uv run pytest` 与 `openspec validate apply-measured-typesetting --strict`，确认全部通过；以命令输出为交付物。（`uv run pytest` 467 项全绿；`openspec validate apply-measured-typesetting --strict` 报 `Change 'apply-measured-typesetting' is valid`，`--specs --strict` 三个主规格全通过。）
- [x] 5.4 检查暂存内容不含生成媒体、缓存与密钥，提交本变更与配套文档，并在交付时报告 commit 标识与验证结果。（两次提交：`eff7753` 溢出闸门与文档同步、`348cdec` README 与项目规划同步；暂存前逐项检查，无 `outputs/`、无 `.mp4`、无缓存、无负例夹具。负例夹具 `examples/_neg-overflow/` 用完即删。）
