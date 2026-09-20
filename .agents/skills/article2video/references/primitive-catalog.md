# 视觉原语目录

本文件由 `web/src/registry/registry.json` 生成，不要手工维护表格。

| 类型 | 类别 | 子节点容量 | 属性 | 动效 | 用途 |
| --- | --- | --- | --- | --- | --- |
| `stack` | layout | 1–12 | `align`, `gap` | `reveal`, `fade`, `rise` | 叠放内容并按统一对齐排列 |
| `row` | layout | 1–6 | `align`, `gap` | `reveal`, `fade`, `rise` | 横向排列内容 |
| `column` | layout | 1–8 | `align`, `gap` | `reveal`, `fade`, `rise` | 纵向排列内容 |
| `split` | layout | 2–2 | `ratio`, `gap` | `reveal`, `fade`, `rise` | 按受控比例分成两栏 |
| `grid` | layout | 1–6 | `columns`, `gap` | `reveal`, `fade`, `rise` | 二列或三列网格 |
| `radial` | layout | 2–6 | 无 | `reveal`, `fade`, `rise` | 围绕中心按确定性圆周布局排布子节点 |
| `overlay` | layout | 1–6 | `align` | `reveal`, `fade`, `rise` | 在同一区域叠加图层 |
| `text` | content | 0–0 | `contentRef`, `role`, `align`, `state` | `reveal`, `fade`, `rise` | 显示分镜文本内容 |
| `number` | content | 0–0 | `contentRef`, `role`, `schematic`, `state` | `reveal`, `fade`, `rise`, `count` | 显示或递增数值 |
| `image` | content | 0–0 | `sourceRef`, `state` | `reveal`, `fade`, `rise` | 显示本地受控图片 |
| `icon` | content | 0–0 | `icon`, `state` | `reveal`, `fade`, `rise` | 显示内置符号 |
| `chart` | content | 0–0 | `contentRef`, `chart`, `schematic`, `state` | `reveal`, `fade`, `rise` | 显示柱状、折线或饼图 |
| `shape` | graphic | 0–0 | `shape`, `state` | `reveal`, `fade`, `rise`, `draw` | 显示受控基础形状 |
| `surface` | graphic | 1–8 | `state`, `gap`, `align` | `reveal`, `fade`, `rise` | 承载内容的卡片或面板 |
| `connector` | graphic | 0–0 | `direction`, `state` | `reveal`, `fade`, `draw` | 按确定方向绘制连接箭头，表达相邻内容之间的推进关系 |
| `group` | graphic | 1–12 | `direction`, `gap`, `align` | `reveal`, `fade`, `rise` | 为一组节点提供语义分组 |
