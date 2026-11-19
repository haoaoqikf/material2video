## 消费者核对

| 主项目位置 | 消费者和处置 | 验证 |
| --- | --- | --- |
| `web/src/code-scene/motion-components/l1.tsx`、`l2.tsx`、`text.tsx`、`paths.ts`、`morph.tsx`、`noise.tsx`、`charts.tsx`、`timeline.tsx` | 当前模板和四部示例均无依赖。旧复利示例曾采用部分本地副本。删除只服务于这些包装的实现、总入口、导出与测试。 | 引用核对、Web 类型检查及构建。 |
| `web/src/code-scene/motion-components/gauge.tsx` | 原理隐喻示例采用 `arcPath`，保留其参考实现。两种 React 仪表包装仅为总入口导出，退役。 | 圆弧几何与源码闸门。 |
| `web/src/code-scene/motion-components/styles.ts`、`web/src/code-scene/chart-geometry.ts` | 纪实示例采用样式变换，金融来源参考使用统一曲线，保留。 | CSS 插值、金融场景、示例本地构建。 |
| `web/package.json` 与锁文件 | 三个 Remotion 辅助包、roughjs、d3-scale 与配套类型的直接消费者已退役。独立作品的声明各自维护。 | 更新锁文件并验证冻结安装。 |

保留现有确定性原语和采集测试。制作指南改为从仍在使用的局部参考出发，作品需要其他展示方式时按实际选型采用本地实现或固定版本的第三方库。

## 实施验证

- Web 锁文件移除 6 个直接依赖及其专属传递节点，冻结离线安装、TypeScript 和 Vite 构建通过。
- 9 项 Web 和 22 项 Python 定向测试通过。覆盖保留的圆弧、样式、金融场景、源码检查、四部示例构建、ECharts 顺序时钟、事件同步及纯时间重复定位。纯时间浏览器测试从已退役包装改用保留的生长与缓动原语。
- 视觉工具复测发现参考构建器的 KaTeX 原始 CSS 分支只匹配正斜杠路径。用 Node 的平台路径解析识别导入者后，公式、ELK 图示和图标在 Windows 的离线浏览器采集通过，缺失或损坏字体仍会失败。
- 79 处文档相对链接、受影响 JSON、文档投影和引用检查通过。代码审查 97/100。删除集中于共享实现与依赖，作品本地的采集和渲染成本不受共享删除影响。本次验证覆盖场景构建及适用浏览器采集。
