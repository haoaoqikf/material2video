# 全球市值前十 · 竖屏发布会

2000 年 3 月至 2026 年 11 月，谁曾是全球市值最高的上市公司？榜首站在深色金属环舞台前。领先者接近时，公司各在固定卡位展示名次和金额，再由新榜首接过舞台。右侧和底部为抖音白色点赞图标及发布时添加的标题保留深色空间。

独立工程包含整个历史场景，输出 1080 × 1920、30 帧/秒、3,214 帧，约 107.13 秒，无音轨。见[总设计](DESIGN.md)、[分镜](storyboard.json)及[数据口径与视觉依据](RESEARCH.md)。

## 恢复、预览与导出

可将整个目录复制到仓库外运行。需要 Node.js 22.12 或更新版本、pnpm 10.15.0、uv 和 Python 3.11 或更新版本。

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
pnpm run validate
pnpm run build
pnpm run video:prepare
pnpm run preview --start-seconds 70.8 --limit-frames 58 --jobs 1
pnpm run render --jobs 1
pnpm run qa
```

`setup` 恢复两套字体并安装 Playwright Chromium。已有匹配字体时，可将 `M2V_FONT_CACHE` 指向字体缓存目录，再执行不带 `--download` 的 `setup`。文件名、摘要和公开下载源见[字体登记](fonts/registry.json)。

以上预演覆盖一段苹果与微软的榜首交接。其余过程可按[复核窗口](design/formal-review-windows.json)调整预演起点与长度。正式成片在 `outputs/video.mp4`，技术报告在 `outputs/qa.json`。

## 修改入口

- 历史时点与市值用[结构化快照](scenes/market-cap-history.json)维护，排序和插值在[数据模型](scenes/market-history-model.ts)。
- 榜首交接的卡位及剩余名次的行位在[舞台编排](scenes/market-history-stage.ts)。视觉由[场景组件](scenes/market-history-portrait.tsx)、[样式](scenes/market-history-stage.css)和[底色绘制](scenes/market-history-stage-backdrop.ts)共同控制。

本示例的原创代码和文档采用 [MIT 许可证](LICENSE)。依赖、字体和数据来源见[第三方声明](THIRD_PARTY_NOTICES.md)。
