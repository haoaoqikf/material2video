## ADDED Requirements

### Requirement: 数学字体受控恢复

KaTeX 实际使用的 WOFF2 字体 MUST 登记版本、摘要、字节数、许可与恢复目标，并复用现有恢复和校验机制。依赖包已安装的字体文件 MAY 作为登记候选来源；字体二进制 MUST NOT 入库，缺失或摘要失配 MUST 阻止相关公式构建/准备，不允许系统字体静默回退。

#### Scenario: 安装依赖后恢复
- **WHEN** 已安装固定版本 KaTeX 并执行字体恢复
- **THEN** 校验源字体并恢复登记目标，公式无需在线字体
