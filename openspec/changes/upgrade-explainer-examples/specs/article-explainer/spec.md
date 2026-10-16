## ADDED Requirements

### Requirement: 固定示例的内容驱动演示
仓库 MUST 保持缓冲、试错、选择三个固定示例，每片提供约 120～180 秒的完整讲解，合计覆盖七种模板及已批准的动画、图表与三维组件。核心代码演示 MUST 有对应旁白并按实际旁白时间窗推进；示意数据 MUST 明确标识，文章 MUST 说明论点的适用边界。示例说明 MUST 提供论点、旁白、画面与组件的对应关系。

#### Scenario: 三片完整制作
- **WHEN** 使用三个固定示例通过统一入口完成准备、完整预演与导出
- **THEN** 每片为 1080×1920、30 fps，含配音与烧录字幕，实际时长为 120～180 秒，动画解释对应文章且成片保存到各自 videos/examples/<slug>/outputs

#### Scenario: 覆盖检查
- **WHEN** 检查固定示例分镜与源码
- **THEN** 合计覆盖观点、对比、步骤、因果图、图片、视频和代码场景，以及 Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei，核心代码幕包含旁白
