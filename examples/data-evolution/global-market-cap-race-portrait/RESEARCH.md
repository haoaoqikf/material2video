# 全球市值前十 · 研究

## 市值口径

[随附数据](scenes/market-cap-history.json)固定 70 期，覆盖 2000 年 3 月 31 日至 2026 年 11 月 20 日。市值统一换算成万亿美元。早期观察点间隔较长，视频的逐月日期和中间金额由相邻快照插值，只有采样日期对应来源记录。榜单按未舍入的当帧金额排序，画面金额显示三位小数。

| 时间 | 来源和采用方式 |
| --- | --- |
| 2000 年 3 月 31 日 | 联合国拉美经委会表 III.1 汇编的 FT Global 500。原表单位为十亿美元。[ECLAC 原表](https://easterncaribbean.un.org/en/download/76196/141484) |
| 2001–2022 年 | Data Driven Decisions 的年度整理，包含退市、合并及历史序列覆盖较晚的公司。2004 年采用同一项目的年末重算。[固定版本的数据来源与局限](https://github.com/datadrivendecisions/marketcap/blob/2ebbd6d5297ecac75420ccd8fe0b92e5482eebd7/DATA_SOURCES.md) |
| 2023 年 1 月至 2026 年 11 月 | CompaniesMarketCap 的月末附近快照，最后一期为 11 月 20 日。[历史日期榜单](https://companiesmarketcap.com/time-machine/) · [最后一期](https://companiesmarketcap.com/time-machine/2026-11-20/) |

数据文件采用 UTF-8 和 LF 换行时的 SHA-256 为 `b1552106a28fedb2d5fa815e5888399d4c02eec3f253f84aab12ef2fabaf9a08`。使用该文件能够复现片中使用的历史视图。

## 舞台与交接

原制作参考了黑底上以冷暖沿边反射勾勒金属曲面的做法。[Apple iPhone 16 Pro 发布视觉](https://www.apple.com/newsroom/2024/09/apple-debuts-iphone-16-pro-and-iphone-16-pro-max/)本片由 Canvas 和网页样式绘制独立金属环、内轨和舞台暗部。主要信息集中在左侧；用大字号区分当前榜首，其余名次以固定行位维持可读性。

原制作以苹果与微软的代表性样片检验交接。公司身份与金额在同一张卡上，金额交叉时同步切换实际第一名与高光。相邻两次易位共用同一个三卡窗口，避免卡片在短时间内重新开合。右侧和下方以模拟抖音白色界面层，对照测试发布时的点赞标记与用户标题。对应的可复查区间见[画面与过程设计](DESIGN.md)。
