# 设计：两层根、内容根与 `/__a2v__/` 别名

## 背景：三处假设把文章钉在仓库里

| 位置 | 今天的假设 | 文章出仓库后会怎样 |
| --- | --- | --- |
| `a2v/paths.py` | 从输入文件向上找 `.agents/skills/article2video/SKILL.md`，再要求它下面有 `videos|examples/<slug>` | 找不到标记 → 直接报错，无法推导归属 |
| 页面 HTML | `../../.agents/skills/article2video/assets/*.css|js` | 相对路径指向内容根自己，404，画面无样式无时间轴 |
| `a2v/render.py` + `a2v/media.py` + `a2v/assets.py` | 用 `.git`/`pyproject.toml` 标记定位「项目根」，页面与资产都相对它记键 | 根为 `None`：共享资产不进指纹，陈旧判定只能给「无法判断」 |

只把 `videos/` 加进 `.gitignore` 解决不了第三列——那正是「解耦」要付的账。

## D1 两层根：仓库根与工作区根

```text
仓库根 repo_root        # .agents/skills/article2video/SKILL.md 所在处：脚本、共享资产、examples
工作区根 workspace_root # 存放 videos|examples/<slug> 与 outputs/ 的目录；内容根未设置时 == repo_root
```

- `ArticlePaths` 增 `repo_root` / `workspace_root`，`root` 保留为 `repo_root` 的兼容属性，
  避免一次性重命名把调用方全打散（`cli.py` 的三处 `article.root` 逐步改到语义正确的字段）。
- 推导顺序：输入文件命中 `<repo>/videos|examples/<slug>` → 工作区根 = 仓库根（**既有行为**）；
  否则要求命中 `<内容根>/videos|examples/<slug>` → 工作区根 = 内容根；两者都不是就报错。
- 内容根解析：`--content-root` > `A2V_CONTENT_ROOT` > 仓库根。**不引入配置文件**，
  也不自动探测（不猜）。报错信息点名这两条设置方式。

为什么「仓库内优先」而不是「内容根优先」：仓库内的 `examples/` 是仓库自带的示例，
不该因为作者把内容根指到别处就改变归属；既有文章的渲染结果也因此逐帧不变。

## D2 共享资产用 `/__a2v__/` 别名引用

内容根里的页面写：

```html
<link rel="stylesheet" href="/__a2v__/base.css">
<script src="/__a2v__/timeline.js"></script>
<script src="/__a2v__/vendor/spring.js"></script>
```

`LocalServer` 长出 `mounts: {"/__a2v__": <skill 资产目录>}` 与 `url_for(path)`：

- 只有声明过的前缀会被映射，其余仍走原静态根；前缀内的目标目录由脚本自身位置推出，
  与仓库放在哪里无关；
- 映射前先归一化并拒绝 `..`、绝对路径与越界解析，`/__a2v__/../secret` 一律 404；
- `url_for` 同时支持「页面在静态根内」与「页面在挂载内」两种情形，声明式流程
  （静态根 = 内容根、共享页面在仓库内）因此不必再要求两者同处一棵树。

被否掉的替代方案：

| 方案 | 为什么不用 |
| --- | --- |
| 静态根取仓库与内容根的公共祖先 | 会把公共父目录（可能含其他仓库）整个挂到回环端口上；`static_server.py` 现有注释明确写着「不扩大网页静态根目录」 |
| 在内容根建指向 `.agents` 的 junction/软链接 | Windows 上 `Path.resolve()` 会把链接解析回真实路径，于是「同一文件的两种视图」在推导里对不上；备份与 Git 工具也会困惑 |
| 内容根里复制一份 skill 资产 | 两份资产必然漂移，而成片溯源量的是「网页真正引用的资产」 |
| 页面写死到仓库的相对路径 | 相对位置随内容根移动而失效，且要求作者手工算层级 |

仓库内的页面（`examples/*`、`videos/never-fear-interviews/index.html`、共享页面
`assets/declarative.html`）**保持相对路径**：它们与资产同在一棵树里，相对路径本就稳定，
也避免了 `tests/test_offline_assets.py` 那种「用任意静态服务器直接打开页面」的用法失效。

## D3 成片溯源 version 3

v2 的三处字段在跨根场景下都会失准，因此升版并把定位方式换成**相对引用**：

```json
{
  "version": 3,
  "workspace": "../..",                // 从产物目录指向工作区根的相对路径
  "page": "videos/<slug>/index.html",  // 相对工作区根
  "assets": { "files": {
      "videos/<slug>/index.html": "…", // 页面与页面内资产：相对工作区根
      "__a2v__/theme.css": "…"         // 挂载资产：用别名键，按运行中的 skill 解析
  } }
}
```

- 判定时 `workspace = (成片目录 / workspace).resolve()`，页面与页面内资产据此解析；
  别名键按**运行中的** skill 资产目录解析。产物里仍然不写绝对路径（原有纪律不变）；
- `assets.local_assets()` 与 `asset_fingerprint()` 因此都要认别名键；两个新参数
  （`workspace_root`、`mounts`）都可省略，省略时行为与今天逐字节一致——
  这样既有测试不必改口径，新能力另加用例；
- v2 及更早的 sidecar 判为 `unknown` 并说明「旧格式，请重渲一次」，与 2→3 的既定做法一致；
  不自动改写产物，也不把「格式变了」说成「资产变了」。

## D4 产物跟着文章走

`outputs/` 与 `media/`、`previews/`、`inspect/` 一律挂在**工作区根**下：
内容根外置时，成片与配音缓存跟着文章，仓库里不再积累个人产物。
`outputs/examples/<slug>/` 的独立层级保持不变（示例产物不与同名文章互相覆盖）。

## D5 测试：内容不入库，测试也不依赖内容

- 硬依赖未跟踪内容的用例改成读仓库内示例：`test_figures_assets.py` 的页面契约改对
  `examples/why-effort-fails/index.html` 参数化到所有声明了 `DEFAULT_FIGURES` 的示例页面；
  两份字体测试的参数表移除 `videos/never-fear-interviews/storyboard.json`；
- 新能力各自带用例：内容根推导、`--content-root` 优先级、挂载与越界、别名资产的指纹与溯源、
  以及一条**跨根端到端**用例（临时内容根 + 声明式两幕 + 限帧渲染，断言产物落位）。
  端到端用例是这一轮唯一能证明「仓库内共享页面在内容根场景真的能跑」的证据，
  因此即便慢也要跑完整版（`pytest` 默认包含，`-m "not slow"` 可跳过）。
