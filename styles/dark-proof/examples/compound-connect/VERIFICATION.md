# 当前规范示例验证

[当前40秒成片](outputs/video.mp4) / [近期创作复盘](CASE_STUDY.md)。1920×1080、30fps、1200帧，无旁白、无配乐，六项原创合成事件音。当前示例已独立重建，G0–G6有效，G2无static-expression风险而不适用；无必改未关闭。

- 视频SHA256：`87b4b0a24481c1adf14103b71f4c7d7813ea9e8df9f6704768108f46b3282f34`。
- 准备指纹：`f512022ef2bb0b08722b6842823b49c443121687fb8ec2bca03a2ae6bb8e977a`。
- 来源R5视频SHA256：`87b4b0a24481c1adf14103b71f4c7d7813ea9e8df9f6704768108f46b3282f34`。
- 风格1.2.0：指南修订前`0205e07232009e2d22adfcb1c0f0115f3e31d5656bd3f044c05b9c698acc42f0`，修订后`e92290ce71a71aee51c46b3258e082c820f7a93eb11b5c73a1dce5810b729c0e`。该变化来自已获用户明确授权的共享GUIDE修改；组件、tokens、版本和指纹算法未变，示例子树仍被排除。

## 实际检查

| 检查 | 结果与证据 |
|---|---|
| 专项测试 | 11项通过：模型101点递推/增量/坐标单调与乱序求值、空目录编排幂等/事件合同、风格指纹隔离、真实声音恢复/漂移拒绝/不覆盖、三幕构建及版本控制卫生；TypeScript专项通过。未跑全仓回归。pytest缓存目录权限警告未影响测试结果。 |
| 独立重建 | 六项声音从现有合成器离线恢复，固定摘要与来源R5一致；不依赖原作品或缓存。三幕源码及分镜与来源相同。 |
| 完整过程 | hook/proof/resolution三幕当前完整G4均pass，三段过程视频与来源R5逐字节相同。G3复用当前hook/proof过程，不重复录制animatic。 |
| 当前核心轮 | 新代理example-core完整查看0–29秒30页/24组1920和393宽配对，先盲看落盘，再核对中性条件，均pass。条件调用记录移除inputPaths中的报告路径后按纯格式修正版导入，原判定、观察及时间未改，原文件保留。 |
| 内部检查 | 本轮实看hook的318/329帧与proof首帧手机图；完整结构观察依据三幕同摘要及来源内部记录复用，未冒充本轮重新逐页查看；G5内部检查不计独立轮。 |
| 当前全片 | 在示例目录正式render及QA，全部技术项pass。解码1200帧逐帧与来源一致，PCM音频逐样本一致，标准用户文件访问可用。 |
| 当前终审 | 未参与核心的新代理example-final，覆盖当前全片616采样/39页、原生/393配对及200px结尾。先盲看落盘，再同轮条件核对，均pass；未继承来源或旧例的完成账本。 |
| 音轨 | -15.6 LUFS、-1.2 dBTP，音画时差0.00798秒；静音与暗帧候选另行记录处置，没有篡改QA测量。 |

## 记录入口

- [当前QA](outputs/qa.json)、[完整来源等价核验](outputs/production/source-equivalence.json)、[候选处置](outputs/production/signal-review.json)
- [核心盲看](outputs/production/example-core-blind-observation.md)、[核心条件](outputs/production/example-core-conditions-observation.md)
- [终审盲看](outputs/production/example-final-blind-observation.md)、[终审条件](outputs/production/example-final-conditions-observation.md)
- [内部检查](outputs/production/g5-observation.json)、[当前账本](outputs/production/final-status.json)、[唯一问题记录](outputs/visual-notes.md)、[替换来源](outputs/production/replacement-origin.json)
- [代码审查](CODE_REVIEW.md)、[数学与来源](SOURCES.md)、[重建与修改](HOWTO.md)

旧68秒示例及全部历史已保护在仓库根`outputs/historical/dark-proof-compound-connect-68s-20261105`，旧片SHA256为`73dbc145d5e828da3e8676a72faf7919a09b3aacf336626291c7e0ac50de1135`。原R5作品保留，本次没有改写其媒体、源码、准备或旧审核。由于共享指南指纹变化，来源作品未来再次导出前需自行重新prepare；旧视频历史摘要仍有效。

覆盖限制：以完整密集时码序列、同帧大小图及技术解码判断对象、位置、先后、停留和可读性，未实时播放或实际试听；主观速度感、音色、平台遮挡与观众留存未实测。200px只检验结尾回认，不推广到全部图表。无独立目标图，不补造图像对标通过。

源码、声音配方、固定摘要、测试与交付文档纳入Git；视频、音效二进制、缓存、基线与审核媒体不入库。恢复失败不接受摘要漂移或覆盖已有不同文件。更改后重建不自动继承本次独立结论。
