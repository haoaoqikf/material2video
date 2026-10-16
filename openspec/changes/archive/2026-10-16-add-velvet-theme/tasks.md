## 1. 主题成为共享真源

- [x] 1.1 新增 `web/src/themes.json`：dark/light 取值与现值逐字相等，velvet 按改编后的取值登记，并写明改编理由。
- [x] 1.2 `web/src/palette.ts` 改为读清单，保留 `Palette`/`palettes` 以便既有消费点不动，新增 `typography`/`motion` 访问器。
- [x] 1.3 新增 `src/m2v/engine/themes.py`：读取清单并校验（缺字段、未知字段、非正整数、默认主题不存在），只暴露编排需要的部分。

## 2. 画面接入主题

- [x] 2.1 `ArticleExplainer` 的标题字重/字距/大小写与正文行高改由主题提供，入场时长改为主题的 `entranceFrames`。
- [x] 2.2 去掉 `ArticleExplainerProps` 与 `Root.tsx` 里重复的主题联合类型，改引用 `Theme`。

## 3. 契约与准备阶段

- [x] 3.1 `explainer.py` 的主题校验改为按清单派生，去掉硬编码的 `{"dark","light"}` 与默认值。
- [x] 3.2 `explainer_prepare.py` 的转场时长与阅读停留改为「主题优先、分镜兜底」，并把 `themes` 纳入实现摘要。
- [x] 3.3 `code_scenes.record` 去掉硬编码的默认主题。

## 4. 文档与规格

- [x] 4.1 `design-tokens.md` 增加「视觉主题」一节：主题表、三条改编、主题与令牌层的边界、覆盖分镜的规则、两个已知影响。
- [x] 4.2 `storyboard-schema.md` 的主题说明改为引用清单，并写明作品代码需覆盖每一个主题。
- [x] 4.3 规格增量：`article-explainer` 新增「视觉主题」需求并泛化两处「深浅主题」措辞；`keynote-design-system` 明确多主题不得走作用域层。

## 5. 验证与交付

- [x] 5.1 新增 `tests/test_theme_motion.py`：主题名单与默认值、未知主题拒绝、覆盖/让位规则、阅读停留进入时长账本、清单校验失败路径。
- [x] 5.2 新增 velvet 浏览器验收：布局通过，背景色、字重、字距与 36 帧入场确实落到画面上。
- [x] 5.3 实测 dark 改动前后的采样帧截图哈希一致，确认既有画面逐像素不变。
- [x] 5.4 运行完整测试、前端构建、文档生成检查与规格校验。
- [x] 5.5 三个固定示例重新准备，确认时长账本与改动前一致。
- [x] 5.6 按仓库约定提交，随后归档并同步主规格。
