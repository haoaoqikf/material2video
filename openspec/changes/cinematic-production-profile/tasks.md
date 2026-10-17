## 1. 口径修正与文档基线

- [x] 1.1 修正 `.agents/skills/material2video/references/article-to-storyboard.md` 与 `AGENTS.md` 的固定示例名单：删除 keynote-baseline，改为 buffer-smoothing、darts-trial-and-error、solar-system-journey，并同步横竖屏与时长描述。
- [x] 1.2 修正 `.agents/skills/material2video/references/media-contract.md` 中「节拍音效当前不渲染」的过时表述，明确 `soundtrack.effects` 已进入母版混音，并补一条 effects 混音验收口径。
- [x] 1.3 更新 `docs/PROJECT_PLAN.md`：加入 standard/cinematic 双档位与电影级路线；把「复杂转场/第二套渲染引擎」改为「不换引擎，新增电影级后期与母版」；保留「不自动选曲」，改为支持本地/程序化音床。
- [x] 1.4 新增 `.agents/skills/material2video/references/cinematic-video.md`：参考板、look bible、shot grammar、材质/后期/声音清单、20 项检查表、反模式与成本表。
- [x] 1.5 更新 `SKILL.md`：档位表、cinematic 触发词、Brief → Look-dev → Hero → Full film → QA/Master 阶段、cinematic 的 look-dev 批准例外、禁止静默降级。
- [x] 1.6 更新 `production-workflow.md`、`visual-review-rubric.md`、`design-tokens.md` 的交叉引用；说明 cinematic 不替代作品自由设计。
- [x] 1.7 运行 `python .agents/skills/material2video/scripts/sync_docs.py --check`、相对链接检查与文档 JSON 示例检查。

## 2. 档位、字段与指纹

- [x] 2.1 在 `project.json` 增加可选 `productionProfile`（standard/cinematic，默认 standard），校验未知值与非法类型，并写入准备记录、预演与溯源。
- [x] 2.2 在 general v8 分镜增加可选 `leadInFrames`、`tailFrames`、`readingHoldFrames`；未声明时保持 24 帧阅读停留与当前时间轴不变。
- [x] 2.3 在 `content.props` 增加 `shots` 与 `look` 的 schema 校验：镜头时间窗落在旁白段内、hero ≥ 3、字段类型/范围/未知字段检查；非法时定位到具体镜头。
- [x] 2.4 在 narration segment 增加可选 `claims`（画面特征列表）；校验非空字符串、去重、长度上限，并写入准备记录。
- [x] 2.5 把 profile、shots、look、claims、leadIn/tail/readHold 纳入准备指纹与代码片段缓存键；只改 look 或镜头也必须重新 prepare。
- [x] 2.6 为 standard 作品补回归：未声明新字段时准备记录、缓存键、时间轴与现有成片行为不变。
- [x] 2.7 增加 CLI：`--profile standard|cinematic` 覆盖作品配置，并拒绝非法值；记录实际来源。

## 3. 共享电影套件与确定性

- [x] 3.1 在 `web/package.json` 与锁文件加入 `postprocessing`、`@react-three/postprocessing`；更新批准依赖清单与 bundle cache 键。
- [x] 3.2 在 `m2v/code-scene` 导出共享电影组件：`PostFX`、`CameraRig`、`LookProvider`、`Starfield`、`ParticleBelt`、`Atmosphere`、`Rings`、`SunSurface`、`Corona`、`Prominence`、`OortCloud`、`Comet`。
- [x] 3.3 实现镜头路径与缓动：CatmullRom/Bezier、quintInOut、每镜头 FOV/滚转/曝光、焦点拉移、穿球与背景裁切检查。
- [x] 3.4 实现确定性后期：Bloom、DOF、grain、vignette、CA、LUT 全部由 `elapsedSeconds`/帧号驱动；粒子噪声使用「帧号 + shot id」种子。
- [x] 3.5 实现运动模糊与 SSAA 选项：hero 2–4 子帧、2× 渲染降采样；standard 默认关闭。
- [x] 3.6 扩展 `useMediaAsset` 返回 colorSpace、alpha、许可；保持未知 ID 与越界访问的失败语义。
- [x] 3.7 增加测试：同帧 PSNR ≥ 60dB、源码闸门仍拒绝挂钟/随机/CSS 动画、缺少 postprocessing 时提前失败、standard 画面不因新依赖改变。
- [x] 3.8 更新 `storyboard-schema.md`、`render-contract.md`、`design-tokens.md` 与 SDK 类型说明，明确「当前支持」与「cinematic 专用」。

## 4. 太阳系 look-dev 与 60 秒改写

- [x] 4.1 重写 `examples/solar-system-journey/article.md` 与 `storyboard.json`：9 章、9 段旁白、总量约 230–260 汉字、目标 60 秒、验收 55–65 秒；保留 1920×1080、60 fps、中文 TTS 与烧录字幕。
- [x] 4.2 编写 shot list：冷开场、9 章、3 个 hero（地球、土星、奥尔特云）与太阳冷开场；每镜头声明 tier、时间窗、camera、focus、exposure、post。
- [ ] 4.3 升级资产：太阳/地球/土星/木星/冥王星/土卫六 hero 资产 4K+；补 normal/roughness/emissive；土星环径向纹理 ≥ 4K×512；更新 `assets/media-sources.json`、`SOURCES.md` 与许可。
- [x] 4.4 实现 60 秒镜头：单程向外、3 次回望、hero 连续镜头、前景虚化、硬切/match cut；删除每段返回同一总览机位的逻辑。
- [ ] 4.5 实现视觉细节：地球夜景/云影/海面高光/大气、太阳临边昏暗/日珥/耀斑、土星环逆光/自阴影/粒子、木星大红斑、冥王星心形、土卫六雾霾。
- [x] 4.6 实现 UI：左栏出入、章节进度轨、片头片尾免责声明、字幕 scrim、距太阳 AU 读数；重要文字与主体避让字幕安全区。
- [x] 4.7 选择并保存音色：对 2 个候选音色做同一段 20 秒 A/B；保存 `tts.voice`、`selection`、`speech`（约 `rate -2%`、comma 0.15、period 0.55、paragraph 0.8、headPad 0.08）。
- [x] 4.8 制作配乐与音效：60–70 BPM 环境底、低频 drone、飞近 whoosh、环 shimmer、冰裂、风、深空静默；写入 `soundtrack` 并留证许可/生成器。
- [ ] 4.9 运行 `m2v lookdev`：输出 3–5 张 4K 静帧 + 接触表 + 20–30 秒有声样片；实际观看并记录时间码、问题与复查到 `outputs/visual-notes.md`。
- [ ] 4.10 在 look-dev 样片上取得用户确认；确认前不铺全片。

## 5. Hero、全片与声音

- [ ] 5.1 完成地球 hero：夜面灯光 → 晨昏线日出 → 海面高光 → 云影，月球前景虚化；验证 8–12 秒连续镜头。
- [ ] 5.2 完成土星 hero：环从侧刃到展开、逆光冰晶、卡西尼缝、环影、土卫六雾霾前景；验证 8–12 秒连续镜头。
- [ ] 5.3 完成奥尔特云结尾：日球层顶气泡边界、彗星、拉远到太阳成点；验证 6–8 秒无旁白收尾。
- [ ] 5.4 完成其余章节的 4–7 秒镜头与转场；确保每个章节至少一个可识别主体，旁白 claims 在该段可见。
- [ ] 5.5 完成 60 秒全片：对齐 9 段旁白、leadIn/tail、readingHold、硬切与音乐段落；实际时长落在 55–65 秒。
- [ ] 5.6 完成声音设计：音乐、环境、音效、旁白闪避、母版响度 −14 LUFS / −1 dBTP；检查 mono 兼容与真峰值。
- [ ] 5.7 完成 UI 与字幕：对比度 ≥ 4.5:1、安全区、片头片尾、进度轨、AU 读数；无文字被主体或字幕遮挡。
- [ ] 5.8 运行 `m2v prepare`、`m2v preview`，确认 60 秒完整预演、音画同步、字幕与 claims 检查通过。

## 6. QA、母版与交付

- [ ] 6.1 实现并运行 `m2v qa`：接触表、冻结/重复帧、banding、aliasing、字幕对比度、响度/真峰值、音画同步、claims 可见性；输出 `outputs/qa.json`。
- [ ] 6.2 实现并运行 `m2v assets audit`：4K/贴图齐全度/环径向分辨率/色彩空间/许可；hero 资产不合格时阻断。
- [ ] 6.3 运行 cinematic 评分卡：十项各 0–4 分，≥ 34/40；记录 hero 实看时间码、问题与复查。
- [ ] 6.4 运行 `m2v render --profile cinematic`：ProRes/DNxHR 母版 + H.264 交付；核对 10bit/48k/帧数/时长/音轨。
- [ ] 6.5 运行 `m2v master` 或等价入口，确认母版、交付版、provenance、performance 与 QA 报告齐全；profile/look/post/audio 写入溯源。
- [ ] 6.6 更新 README、PROJECT_PLAN、SKILL、DESIGN、VERIFICATION、SOURCES、示例 README；说明太阳系已改为 60 秒 cinematic，缓冲/试错仍为 standard。
- [ ] 6.7 运行完整验证：`uv run pytest`、`pnpm -C web test`、`pnpm -C web build`、三个示例严格检查、文档链接检查、`openspec validate --strict`。
- [ ] 6.8 检查暂存内容，排除密钥、缓存、生成媒体与临时产物；提交实现与文档，随后按项目规则同步主规格、归档并提交。
