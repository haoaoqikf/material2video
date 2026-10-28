# 风格接入契约

风格独立于视频类型：类型负责材料、业务计算和渲染流程；风格提供表现指导及可选参数、组件与资产。
仓库当前登记 `vibe-fable`（B 寓言）与 `vibe-night`（C 夜曲），没有内置或默认风格。查询 `uv run m2v styles [--json]`。

## 作品选择与制作

在 `project.json` 增加以下可选声明（占位 ID 不代表已有风格）：

```json
{"style": {"id": "example-style"}}
```

不声明则完全由作品设计。每个作品只能选一套风格，不支持混合、继承或自动迁移。
未知 ID、无效包、不支持的类型与实际画幅明确失败，不回退到其他风格。

制作助手读取所选包的 `GUIDE.md`，在作品 `DESIGN.md` 记录采用规则及调整。
优先级依次是项目强制契约、用户明确要求、作品显式调整、风格默认。
指导文档不被渲染器执行；选择风格不会自动换肤。风格不改变计算逻辑、制作门、验收条件或独立评审职责。
其他类型可使用指导和依赖绑定；参数、组件和资产的自动模块解析接口目前仅用于 general 代码场景。

### 验证状态分开披露

包的注册可用、组件技术验证、成片表现验证分别报告依据和限制：清单可加载不等于全部组件已验证，
组件构建与确定性通过不等于成片讲解或风格同族通过。方法写入 GUIDE 只说明制作指导可用；
机制仍须在实际完整窗口兑现。试制的未决差距如实保留，关键采用项关闭按
[检查点契约](checkpoint-gates.md#讲解机制与关键采用项的关闭)，不新增运行时状态字段。

## 包结构和清单

风格包放在仓库 `styles/<id>/`，与仓库外作品内容根无关。清单是唯一注册来源，不需修改类型目录。
`styles/examples/` 是保留目录，存放风格示例，不是风格包：发现时跳过，按该名直接加载明确失败；
其余直接子目录仍必须是有效包。示例放这里而不是包内，是因为包指纹覆盖包内所有文件。

```json
{
  "schemaVersion": 1,
  "id": "example-style",
  "version": "1.0.0",
  "description": "风格说明",
  "types": ["general"],
  "frames": [{"width": 1920, "height": 1080}],
  "guide": "GUIDE.md",
  "tokens": "tokens.json",
  "components": {"instrument": "components/instrument.tsx"},
  "assets": {
    "texture": {"path": "assets/texture.svg", "source": "原创", "license": "MIT"}
  }
}
```

本例为契约说明，不是已安装包。清单拒绝未知字段。

- `schemaVersion` 当前只接受整数 1；`id` 必须与目录名一致，为 1–63 位小写字母、数字或连字符。
- `version` 接受不带前导零的 `major.minor.patch`；不支持预发布后缀或旧版适配。
- `description`、非空 Markdown `guide`、不重复的非空 `types` 和 `frames` 必填。宽高为正整数。
- `tokens` 可省略，提供时必须为有限 JSON 对象；字段由风格自行定义，不预设主题词汇。
- `components`、`assets` 可省略，为资源名到入口的映射，资源名遵循 ID 格式。
  正式包可以登记组件共用的辅助模块（如 `kit`），场景按组件资源名导入；它不是可复用画面组件，
  也不自动改变画面。
- 组件入口接受 `.tsx/.ts/.jsx/.js`。资产接受 `.png/.jpg/.jpeg/.webp/.svg/.woff2/.ttf/.otf`，每项必须有非空来源与许可；声明不代替使用者核验许可。
- 所有路径使用包内正斜杠相对路径，不接受 `..`、绝对路径、符号链接或跨包引用。
- 字体通过登记的 `.ttf/.otf/.woff2` URL 显式加载；场景须在字体及其他资源就绪后调用 `ready()`。字体许可随包保存。风格包字体须为 TTF/OTF 才能进行缺字检查（`woff2` 需额外解析依赖）。
- 包内字体二进制由仓库根 `fonts/registry.json` 与 `fonts/fetch.py` 恢复，不进入 Git；缺失时 `m2v styles`、`validate` 或 `prepare` 明确失败并提示运行 `uv run python fonts/fetch.py`。

## general 场景接口

```tsx
import {identity, tokens} from 'm2v/style';
import Instrument from 'm2v/style/components/instrument';
import texture from 'm2v/style/assets/texture';
```

`identity` 为只读 `{id, version, fingerprint}`，`tokens` 为递归只读 JSON 对象。
没有选择风格时，二者分别为 `null` 和 `{}`；导入组件或资产仍会明确失败。
资产默认导出内联 URL，不产生外网请求。组件内部可使用包内相对源码、登记资产、`m2v/code-scene` 与现有批准依赖；禁止跨包、跨作品及宿主文件访问。
组件必须使用现有受控时钟、资源就绪和字幕安全区契约。声音方向写入指导，由作品走现有音轨编排；当前不渲染风格包音频资产。

## 准备、缓存和状态

`prepare` 保存所选风格的 ID、版本及全包文件内容指纹；指导、参数、组件、资产的添加、删除或修改都会改变指纹。
再次导出要求当前准备有效；风格变化后重新 `prepare`，受影响片段使用新缓存键。
`m2v status --project <目录>` 显示所选风格身份、指导路径及既有准备状态。包损坏或被删除时命令明确报错。
未选风格的准备记录不增加风格字段；风格文件哈希仅在加载阶段计算，不在逐帧渲染中执行。

## 验证要求

新增风格应校验清单、资源来源与许可、类型画幅适配，并用原创作品试制参数、组件与资产。
外观与动态表现继续按[参考风格契约](reference-style.md)和[独立评审](subagent-review.md)验证，注册成功不代表审美验收通过。
