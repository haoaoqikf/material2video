## Context

见 proposal.md 的 Why。影响实现约束的现状：

- 画布在本类型固定 1080×1920、30 fps（`src/m2v/types/stock/brief.py` 的 `WIDTH/HEIGHT`）。
- 现有粗筛只区分竖/横/方（`src/m2v/types/stock/pixabay.py::_candidate`），排序键只把方向当一项（`search.py::_score`）；画面用 `objectFit: cover`（`web/src/compositions/StockMontage.tsx`）。
- `provider._target_height` 在 `orientation: "any"` 时返回 1080，使视频变体偏向横屏版本。
- `search_fingerprint` 已包含整个 `provider` 字典，但 scene 指纹只含 `id/keywords/media/assetId`。
- `load_record` 对记录里的 provider 块做精确字典比较，新增字段必须同步加入期望值。
- 依赖里已有 `imageio-ffmpeg`（`audio.py`、`output_validation.py` 在用），可用 `get_ffmpeg_exe()` 探测本地媒体尺寸；不引入新依赖。
- 模块依赖方向：`brief.py` 顶层 import `provider.PROVIDER_DEFAULTS`，因此比例辅助函数不能放在 `brief.py` 或 `provider.py` 里被对方反向引用。

## Goals / Non-Goals

**Goals:**

- 把「素材长宽比 = 画布长宽比」变成材料可声明、检索可强制、记录可复核的契约。
- 让记录里的像素尺寸等于所下载文件的实测尺寸，使比例与「素材可核验」基于同一份事实。
- 既有能力（Pexels/Pixabay 适配、缓存、脱敏、时间轴、音轨、预演门禁）行为不变。

**Non-Goals:**

- 不新增横屏/方形画布，也不支持任意自定义比例（幕级只有 `canvas`/`any` 两态）。
- 不改变画面合成方式：仍用 `cover` 铺满画布，静图推拉平移的有意缩放保留。
- 不做联网的 Pexels 验证（本机无凭据），Pexels 侧只做代码与离线测试覆盖。
- 不改动时间轴编译、音频、字幕、评审与输出清理流程。

## Decisions

1. **新增独立模块 `src/m2v/types/stock/aspect.py` 承载比例契约**，而不是把规则塞进 `brief.py` 或 `provider.py`：画布常量、`canvas`/`any` 枚举、默认容差、`ratio_matches()`、`effective_mode()` 只在这里定义一份，`brief.py` 的 `WIDTH/HEIGHT` 改为引用该模块常量。这样 `provider.py`、`pixabay.py`、`search.py` 都能用它而不产生循环 import。备选方案是在 `provider.py` 里放辅助函数（`brief.py` 已依赖 provider，方向可行），但画布尺寸会与 `brief.py` 重复定义，规则也会散落两处。
2. **默认值取 `canvas` + 2% 容差**：需求是「长宽比一致」，默认不约束就等于没修；2% 覆盖图库缩放取整（如 1280×853 这类 ±1px 误差）同时让 `cover` 裁切落在不可察觉范围。备选是精确相等（容差 0），会因图库缩放取整误杀合格素材。
3. **硬过滤而非降权**：需求是「必须一致」，降权仍可能选中比例不符的素材。硬过滤在 `search.py` 逐幕应用，`any` 模式保持原有排序键逐项不变，保证旧行为可回归。
4. **视频变体按比例选择**：目标比例存在时按 `(abs(w/h − ratio), −area, url)` 取最小，替代「最接近目标高度」。备选是保留高度偏置并在后面过滤，但那样会大量丢弃可用变体，也可能选到比例不符的版本。
5. **Pexels 图片改取保持原始比例的缩略图**：Pexels 的 `portrait` 缩略图是平台裁切过的版本，其实际比例与候选记录的原始尺寸不符，会让「记录尺寸 = 实测尺寸」失守。比例匹配开启时优先 `original/large2x/large`，其它模式保持现状。
6. **下载后用 ffmpeg 实测尺寸并写入记录**：新增 `src/m2v/engine/media_probe.py`，用 `ffmpeg -hide_banner -i <file>` 解析第一条 `Video:` 流的 `宽x高`（与 `output_validation.py` 既有解析方式一致，只读不写）。实测比例超容差时删除刚落盘的素材并抛错，保证 `assets/stock/` 不留未被记录引用的文件、也不写部分记录。备选是只信图库声明尺寸，但那样无法发现声明不实，也无法满足规格里「留证所下载版本尺寸」。
7. **画面层不改**：比例在检索与记录门禁处保证，`cover` 本身不产生变形。备选是改成 `contain`，但会引入黑边，且会掩盖比例问题而不是解决它。

## Risks / Trade-offs

- [严格 9:16 显著缩小候选池，尤其图片] → 报错必须响亮并给出放宽阶梯（提高 `perPage`、竖屏方向、换关键词、幕级 `any` 或提高容差）；出片时按该阶梯逐级尝试，不静默放宽。
- [默认值变化让既有作品的检索记录失效] → 记录 provider 块新增字段会触发既有「请重新执行 m2v stock search」错误；文档与 README 明确写出这是本次的破坏性变化。
- [实测尺寸依赖 ffmpeg 可用] → `imageio-ffmpeg` 已是既有依赖；探测失败按素材不可用报错并附 ffmpeg 输出尾部。
- [容差内的轻微裁切] → 2% 以内的裁切在成片尺度不可见；容差可按作品收紧或放宽，属于声明项而非隐藏行为。
- [幕级 `any` 被误用为默认] → 文档与评审要点明确 `any` 是有意放宽，规格要求报错信息把 `any` 作为放宽路径之一而不是推荐默认。

## Migration Plan

1. 合并后既有 `stock-montage` 作品重新执行 `m2v stock search`（材料无需改动，默认即启用画布比例匹配）；如需保留旧行为，显式声明 `provider.aspectRatio: "any"`。
2. 重新检索后按既有流程 `prepare` → 完整 `preview` → `render`；旧素材文件未被新记录引用时可手工清理，工具不做自动删除。
3. 回滚策略：把 `provider.aspectRatio` 改为 `any` 并重新检索即可恢复旧行为；代码回滚不影响作品材料格式（新字段在旧实现里会被判为未知字段，需同时移除）。
