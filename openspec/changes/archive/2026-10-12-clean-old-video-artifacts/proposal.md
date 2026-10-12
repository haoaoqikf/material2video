## Why

作品目录会积累旧成片、预演、抽帧和调试检查文件，容易混淆交付版本并占用空间。统一正式渲染成功后自动清理当前作品可再生成的旧视频产物，同时保留本次交付和可继续制作所需材料。

## What Changes

- 为统一正式渲染增加作品级旧产物清理，失败渲染不触发清理。
- 保留新成片及旁车、准备/评审记录和准备媒体；清理旧视频、预演和已知检查及调试产物。
- 更新统一制作说明和渲染输出参考。

## Capabilities

### New Capabilities

### Modified Capabilities
- `modular-video-production`: 正式渲染验收成功后清理本作品可再生成的旧视频产物。

## Impact

- 统一 CLI 的正式渲染收口及作品 `outputs/` 清理工具。
- `modular-video-production` OpenSpec、README 和 material2video Skill 文档。
- 金融作品 NVIDIA 的忽略目录产物；不改作品源材料或仓库共享缓存。
