# 视觉原语目录

本文件由 `web/src/registry/registry.json` 生成，不要手工维护表格。

## 语义动作词汇

beat 的 `action` 只能取下表的值；`建立` 类动作只让对象出现或更醒目，
不改变对象状态与关系，因此 A3 闸门（动画论证评审）不把它算作一次推理。

| 动作 | 含义 | 是否改变状态或关系 |
| --- | --- | --- |
| `establish` | 建立对象或关系 | 否（中性动作） |
| `connect` | 连接两处内容，表达推进或因果 | 是 |
| `transfer` | 把量或注意力从一个对象转移到另一个 | 是 |
| `accumulate` | 累积增长 | 是 |
| `deplete` | 消耗衰减 | 是 |
| `transform` | 改变形态或类别 | 是 |
| `compare` | 并置比较 | 是 |
| `highlight` | 只强调，不改变状态 | 否（中性动作） |
| `loop` | 形成闭环回路 | 是 |
| `break` | 打断或断开关系 | 是 |
| `restore` | 回到先前状态 | 是 |

## 受控图标白名单

`icon` 与 `pictogram` 的 `icon` 属性只能引用下表的名字：
未知名字在**校验阶段**失败，运行期不做动态解析，也不发起网络请求。

| 图标名 |
| --- |
| `arrow` |
| `check` |
| `cross` |
| `spark` |
| `up` |
| `down` |
| `users` |
| `clock` |
| `target` |
| `alert` |
| `lock` |
| `link` |
| `database` |
| `coin` |

## 原语清单

「语义动作」列是该原语**支持**的动作子集：beat 的目标原语不支持某个动作时校验失败。

| 类型 | 类别 | 子节点容量 | 属性 | 动效 | 语义动作 | 用途 |
| --- | --- | --- | --- | --- | --- | --- |
| `stack` | layout | 1–12 | `align`, `gap` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform` | 叠放内容并按统一对齐排列 |
| `row` | layout | 1–6 | `align`, `gap` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform` | 横向排列内容 |
| `column` | layout | 1–8 | `align`, `gap` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform` | 纵向排列内容 |
| `split` | layout | 2–2 | `ratio`, `gap` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform`, `compare` | 按受控比例分成两栏 |
| `grid` | layout | 1–6 | `columns`, `gap` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform`, `compare` | 二列或三列网格 |
| `radial` | layout | 2–6 | 无 | `reveal`, `fade`, `rise` | `establish`, `connect`, `compare`, `highlight`, `transform` | 围绕中心按确定性圆周布局排布子节点 |
| `overlay` | layout | 1–6 | `align` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform` | 在同一区域叠加图层 |
| `text` | content | 0–0 | `contentRef`, `role`, `align`, `state` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform`, `compare` | 显示分镜文本内容 |
| `number` | content | 0–0 | `contentRef`, `role`, `schematic`, `state` | `reveal`, `fade`, `rise`, `count` | `establish`, `accumulate`, `deplete`, `transform`, `compare`, `highlight`, `restore` | 显示或递增数值 |
| `image` | content | 0–0 | `sourceRef`, `state` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform`, `compare` | 显示本地受控图片 |
| `icon` | content | 0–0 | `icon`, `state` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform` | 显示内置符号 |
| `chart` | content | 0–0 | `contentRef`, `chart`, `schematic`, `state` | `reveal`, `fade`, `rise` | `establish`, `accumulate`, `deplete`, `transform`, `compare`, `highlight`, `restore` | 显示柱状、折线或饼图 |
| `shape` | graphic | 0–0 | `shape`, `state` | `reveal`, `fade`, `rise`, `draw` | `establish`, `accumulate`, `deplete`, `transform`, `compare`, `highlight`, `restore` | 显示受控基础形状 |
| `surface` | graphic | 1–8 | `state`, `gap`, `align` | `reveal`, `fade`, `rise` | `establish`, `highlight`, `transform`, `compare` | 承载内容的卡片或面板 |
| `connector` | graphic | 0–0 | `direction`, `state` | `reveal`, `fade`, `draw` | `establish`, `connect`, `break`, `highlight`, `transform`, `restore` | 按确定方向绘制连接箭头，表达相邻内容之间的推进关系 |
| `group` | graphic | 1–12 | `direction`, `gap`, `align` | `reveal`, `fade`, `rise` | `establish`, `connect`, `highlight`, `transform`, `compare` | 为一组节点提供语义分组 |
| `flow` | layout | 2–6 | `direction`, `state`, `gap` | `reveal`, `fade`, `rise`, `draw` | `establish`, `connect`, `transfer`, `accumulate`, `deplete`, `transform`, `highlight`, `loop`, `break`, `restore` | 按确定方向串起阶段并画箭头，突出当前阶段 |
| `cycle` | layout | 2–6 | `direction`, `state`, `gap` | `reveal`, `fade`, `rise`, `draw` | `establish`, `connect`, `transfer`, `accumulate`, `deplete`, `transform`, `highlight`, `loop`, `break`, `restore` | 把阶段排在闭环轨道上并标出方向与当前阶段 |
| `timeline` | layout | 2–6 | `direction`, `state`, `gap` | `reveal`, `fade`, `rise`, `draw` | `establish`, `connect`, `transfer`, `accumulate`, `deplete`, `transform`, `compare`, `highlight`, `loop`, `break`, `restore` | 按确定方向排列里程碑并画出推进进度 |
| `gauge` | content | 0–0 | `contentRef`, `schematic`, `state` | `reveal`, `fade`, `rise`, `count`, `draw` | `establish`, `accumulate`, `deplete`, `transform`, `compare`, `highlight`, `restore` | 用受控指针与刻度显示百分比量级 |
| `pictogram` | content | 0–0 | `contentRef`, `icon`, `schematic`, `state` | `reveal`, `fade`, `rise`, `count` | `establish`, `accumulate`, `deplete`, `transform`, `compare`, `highlight`, `restore` | 用固定数量的受控图标单位显示占比 |
