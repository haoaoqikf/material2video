# 第三方视觉组件接入

第三方组件按动画机制分类，机器可读真源是
`web/src/third-party/catalog.json`：

| 分类 | 接入规则 | 当前示例 |
| --- | --- | --- |
| `static` | 无动画，可直接接入 | 静态卡片候选，尚未进入渲染包 |
| `css-keyframes` | 必须经过 `FrameSyncedCssAnimation`，暂停自动播放并以负延迟按帧定位 | Magic UI `ShineBorder`，本次唯一代表组件 |
| `clock` | 不得直接接入；必须移除动画库、随机数、计时器和布局循环，改为帧驱动 | Number Ticker 候选，本次不进入注册表 |

`ShineBorder` 固定自 Magic UI 提交
`d7207e5692d14c00dceafa8488d6d01f197fa0e4`，采用 MIT 许可证，许可证全文在
`web/LICENSES/magicui-LICENSE`。本地版本移除了 Tailwind 工具类，并用统一包装层接管时间。

自带时钟类的结论是：没有真实文章提出明确需求时，不值得预先改写。后续只有在某种视觉表达
无法由现有帧驱动组件完成时才开启单组件时间盒；改写成本高于自研时，优先自研帧驱动组件。
未改写的组件不得进入 composition，也不得以“预览看起来正常”作为例外。
