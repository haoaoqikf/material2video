## 背景

抖音网页的详情接口需要 `a_bogus`、`msToken` 等由页面脚本即时计算的参数。逆向这些算法会随页面改版反复失效，也和本项目「材料获取可复核、渲染离线确定」的边界无关。方案只读取浏览器页面已经拿到的数据。

## 数据链路

1. **输入解析**：从分享文本中取出第一个抖音 URL；支持 `v.douyin.com` 短链、`douyin.com/video|note/<id>` 与 `iesdouyin.com/share/...`。
2. **页面取数**：Playwright 以持久化 profile 打开链接，监听 `/aweme/v1/web/aweme/detail/` 响应并解析 `aweme_detail`。这是视频页的主路径，签名由页面自己完成。
3. **页面兜底**：图文页不请求详情接口，改为解析页面内 `self.__pace_f.push([...])` 的 RSC 载荷，取 `aweme.detail`。两条路径都失败时报告最终 URL、页面标题，并提示用 `--headed` 人工完成登录或验证。
4. **规范化**：把接口的 snake_case 与 RSC 的 camelCase 统一成同一份元数据；`images` 非空即图文，否则为视频。
5. **下载**：视频按「h264 最高码率 → play_addr → h265」顺序尝试直链；图文优先使用 `urlList`（无水印）逐张下载。请求带桌面 UA 与 `Referer: https://www.douyin.com/`，校验响应非空且文件头与媒体类型相符。
6. **留证**：临时目录下载完成后写入 `metadata.json` 与 `recipe.json`，再整体移入目标目录；失败时清理临时目录，不留下半成品。

## 目录与文件

```text
refs/douyin/<awemeId>/
  video.mp4            # 视频作品
  images/001.webp      # 图文作品，逐张保存
  metadata.json        # 作者、文案、发布时间、来源链接、声明尺寸
  recipe.json          # schemaVersion、媒体文件相对路径、SHA-256、字节数、实测尺寸
```

`refs/` 是内容目录：默认位于工作区根（`--content-root` / `M2V_CONTENT_ROOT` 或仓库根），加入 `.gitignore`。浏览器 profile 放在 `.cache/douyin-profile/`，其中可能含登录 cookie，同样不进版本控制。

`--output` 只改变参考素材根目录，作品 ID 子目录仍由程序生成，避免同一作品散落多份。

## 失败与边界

- 作品已存在且校验通过：默认直接说明并退出 0，不重复下载；校验不通过时要求显式 `--force`，不静默覆盖。
- 短链解析失败、无权限、风控页、直链全部失败：抛出 `M2VError`，附最终 URL、HTTP 状态或文件头诊断。
- 不实现登录、扫码、代理或地区切换；`--headed` 复用同一 profile，供人工完成必要交互后重试。
- 参考素材只用于分析与比对，不复制进成片；项目的内容/媒体入库规则保持不变。

## 取舍

- 不引入 yt-dlp 或 f2：两者都需要持续跟进签名与解析变化，而本项目需要的只是单条作品；浏览器路径复用已有依赖，改版时通常只需调整字段名。
- 不做批量主页/合集抓取：当前需求是单条参考，批量入口会扩大风控与版权面。
