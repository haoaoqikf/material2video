# 复利 40 年 · 研究

观众先要知道在比较同一笔钱的两个二十年，随后用一次具体的「旧利息又赚一百」理解余额为何越长越快。参考案例取其构图、对象变化与镜头节拍，场景中的玻璃、数据、动画与旁白独立制作。

| 参考与观察 | 采用 |
| --- | --- |
| Investor.gov 的课堂算例把第二年利息拆成原本金和去年利息带来的两份。 [课堂算例](https://www.investor.gov/additional-resources/information/youth/teachers-classroom-resources/what-compound-interest) | 开场把投资条件和比较对象放在一起，近景让新增小片从旧收益所在位置升出。 |
| Dabarti 项目页的静帧中，亮边勾勒透明体厚度，台面和场景的光纹保有共同方向。 [The Photons](https://dabarti.com/work/the-photons/) | 冷蓝底座、暖色收益片和近景台面共享入射方向，让主体变化在透射或接触光中可见。 |
| Cheng 等对数据视频的编码显示，年份、柱体尺度与柱顶读数可在口播中一一配对，口播停顿也可留给画面继续推进。 [论文](https://www.microsoft.com/en-us/research/wp-content/uploads/2022/05/NarrationsAnimationsInDataVideos-EuroVis2022.pdf) | 「又赚一百」绑定小片升起。「六点七三倍」落在同底线的量高完成后。 |

## 短版柱图与动效补研

| 参考与观察 | 采用 |
| --- | --- |
| Apache ECharts 官方柱图在 Chromium 取六个有序时点，柱脚相对零线稳定，出现时刻逐柱错开。 [官方示例](https://github.com/apache/echarts-examples/blob/gh-pages/public/examples/ts/bar-animation-delay.ts) | 年柱用单调缓动从零线增长，光随柱顶移动，长满后停留读数。 |
| Datamations 示例的有序帧保留原始对象、组别、汇总三种状态，Gemini² 用分阶段变换连接数据图形。 [Datamations](https://www.microsoft.com/en-us/research/project/datamations/) · [Gemini²](https://idl.uw.edu/papers/gemini2) | 年柱按组同向拉开后归塔，每根沿用同一年度身份，年柱末态直接接续归塔起态。 |
| FALZ 的抽帧覆盖折片立起、折角出现和接缝闭合，折线方向与投影跨镜头延续。 [创作者案例](https://schoberth.studio/en/falz/) | 两组沿各自外缘折为塔层，落点保持可辨，最终闭合触发提示音与台面亮纹。 |

图表和归塔共用三维几何，实际时间由现有逐帧输入驱动。作品锁定 Three.js、Three GPU Pathtracer、three-mesh-bvh 与 xatlas-web，版本与来源见[依赖锁](pnpm-lock.yaml)。三维柱变化、照明、字幕及事件落点由[实际采集](DESIGN.md#验收证据)核对。
