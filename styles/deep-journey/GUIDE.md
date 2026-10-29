# 深空旅程风格包（deep-journey）

## 可用范围与表现验证

- 适用类型：`general`；画幅：1920×1080；旁白不限制（可有可无）。
- 本包只提供表现层：深空色板、3D 舞台、轨道与行星表面、HUD 与字幕 scrim。选择风格不会自动换肤，场景必须显式导入组件。
- 包内不含天体数据、纹理、路径、旁白、分镜或声音；这些属于作品。
- 3D 组件通过 `m2v/code-scene` 使用 Three/R3F/drei，不直接裸导入。使用逐帧回调的组件只适用于顺序录制；声明 `capture.mode: "pure-time"` 的作品不要导入 `useFrame` 组件。
- 注册成功、组件构建通过不等于成片表达通过；成片仍按现有独立评审与视觉复核验收。

## 1. 什么时候用

适合**空间、尺度、地理与连续旅程**题材：天文、地理、建筑、历史路线、系统层级、从局部到全貌的揭示。核心是“同一个世界、连续移动、尺度经验”。

不适合：以文字、图表、档案照片或可数对象为主的题材；没有稳定空间关系的题材。

## 2. 选择与加载

```json
{"style": {"id": "deep-journey"}}
```

场景显式导入：

```tsx
import {useJourneyFrame} from 'm2v/style/components/kit';
import SpaceStage from 'm2v/style/components/space-stage';
import OrbitRing from 'm2v/style/components/orbit-ring';
import PlanetSurface from 'm2v/style/components/planet-surface';
import Atmosphere from 'm2v/style/components/atmosphere';
import ChapterTrack from 'm2v/style/components/chapter-track';
import StatusLine from 'm2v/style/components/status-line';
import InfoPanel from 'm2v/style/components/info-panel';
import SubtitleScrim from 'm2v/style/components/subtitle-scrim';
import BoundaryFootnote from 'm2v/style/components/boundary-footnote';
```

## 3. 色板与语义

| 颜色 | 语义 |
|---|---|
| `text` `#F2EEE5` | 主题、天体名称与结论 |
| `body` `#E7CCA2` | 对象说明与一句印象 |
| `nav` `#DABB86` | 当前站点、章节进度与方向提示 |
| `muted` `#A7B5C2` | 次要状态、单位与观察说明 |
| `line` `#9FB6CF` | 轨道、边界与结构性引导线 |
| `warning` `#E9BE7D` | 示意、推测结构与事实边界 |
| `footnote` `#9C8159` | 片尾边界与来源提示 |

自然天体色保留原本色相；代码生成的星场、粒子与材质必须明确为艺术示意。深空底色接近纯黑，暗部与高光按手机观看保留层次。

## 4. 版式与 HUD

- 主体在中央偏右；状态行在左上，章节轨在右上，信息面板在左侧；字幕 scrim 在底部。
- 文字只给对象名、一句印象、当前站点与必要边界；不堆信息卡。
- 章节轨只显示当前进度与少量站点，不逐站铺满。
- 字幕安全区只从场景上下文 `subtitleSafeArea` 取得，不在 tokens 复制。

## 5. 组件

| 组件 | 用途 |
|---|---|
| `space-stage` | 3D 画布：背景、相机、look、灯光、星场与后期；作品把世界作为 children |
| `orbit-ring` | 轨道环；可高亮当前主体 |
| `planet-surface` | 通用球体表面：颜色/贴图/自发光；复杂 shader 由作品实现 |
| `atmosphere` | 大气/边缘光；克制，不遮挡主体细节 |
| `chapter-track` | 右上章节进度轨 |
| `status-line` | 左上状态行：当前站点/方向 |
| `info-panel` | 左侧信息面板：名称、一句印象与必要边界 |
| `subtitle-scrim` | 底部字幕 scrim；不替代共享字幕层 |
| `boundary-footnote` | 小字边界/示意说明；次要位置 |

组件只接收天体、位置、镜头、进度与文字等 props，不内置天体名、距离、AU、NASA 文本或旁白。

## 6. 制作规则

- 单幕、同一三维世界、连续相机优先；不用硬切、叠化或换页替代空间移动。
- 镜头移动必须有认知作用：接近、离开、拉远、环绕或穿越应公开新关系，不只是把页面放大。
- 尺度通过可辨认参照、遮挡、远近层次与观察窗口建立；粒子数量与 Bloom 不自动等于规模感。
- 不确定性动画由受控帧号/R3F 时钟驱动，不使用挂钟、`Math.random`、CSS 动画或组件计时器。
- 使用 `useFrame` 的组件不得用于 `pure-time` 作品；静态闸门会明确失败。
- 纹理加载完成前不调用 `ready()`；首帧纹理上传与绘制应在同一布局效果内完成。

## 7. 验收

- 场景显式导入组件，未导入时画面与无风格一致。
- 同帧两次录制字节一致。
- 包指纹变化使准备失效；修改示例不改变包指纹。
- 示例作品 `styles/deep-journey/examples/solar-system-journey/` 通过 v8 校验、prepare 与代表性 QA。

## 8. 边界

- 不提供天体数据、纹理、路径、旁白、分镜或声音。
- 不提供 2D 图表、档案框或可数对象；这些属于其他风格或作品。
- 不自动换肤，不改变业务计算、制作门或评审职责。
