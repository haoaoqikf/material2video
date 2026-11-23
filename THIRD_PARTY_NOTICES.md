# 第三方声明

Material2Video 的原创代码、文档及示例源码和原创文案采用 MIT 许可证。另有许可标注的内容沿用其声明。 [项目许可证](LICENSE)

项目通过各工程的 `uv.lock` 和 `pnpm-lock.yaml` 安装第三方依赖。各依赖的版权和条款以对应版本随附的许可证为准。

## 主要依赖

| 组件 | 使用范围与许可 |
| --- | --- |
| Remotion `4.0.526` | 用于渲染和预览。上游免费许可适用于个人、不超过三名员工的营利组织、非营利组织及符合条件的非商业评估。不符合免费许可条件的使用者须取得公司许可。 [许可文本](docs/licenses/remotion.txt) · [上游锁定版本](https://github.com/remotion-dev/remotion/blob/v4.0.526/LICENSE.md) |
| GSAP `3.15.0` | 参考前端依赖，采用 GSAP Standard License。用于与 Webflow 的视觉动画构建能力竞争的特定无代码动画工具时，须事先取得书面同意。 [上游许可](https://gsap.com/community/standard-license/) |
| elkjs `0.12.1` | 参考前端的图布局依赖，采用 EPL-2.0。 [许可文本](docs/licenses/elkjs.txt) · [上游锁定版本](https://github.com/kieler/elkjs/blob/0.12.1/LICENSE.md) |
| lucide-react `1.68.0` | 参考前端的图标依赖。Lucide 采用 ISC，源自 Feather 的图标保留其 MIT 声明。 [许可与署名](docs/licenses/lucide-react.txt) |
| FFmpeg | 用于媒体处理。可执行文件的许可取决于实际构建选项和组件。 [FFmpeg 许可说明](https://www.ffmpeg.org/legal.html) |

## 字体、模型和示例素材

- 字体的来源、版本、摘要和许可证见[字体登记](fonts/registry.json)及[字体许可](fonts/licenses/)。
- 配音和对齐模型按[独立工程声明](templates/standalone/THIRD_PARTY_NOTICES.md)引用的登记及许可恢复。素材索引模型和可选依赖见[模型登记](src/m2v/materials/model_registry.json)。
- 五部示例分别提供独立声明。 [复利 40 年](examples/data-evolution/compound-after-20/THIRD_PARTY_NOTICES.md) · [全球市值前十](examples/data-evolution/global-market-cap-race-portrait/THIRD_PARTY_NOTICES.md) · [运气到底是什么](examples/principle-metaphor/luck-on-stage/THIRD_PARTY_NOTICES.md) · [太阳系之旅](examples/spatial-3d/solar-system-journey/THIRD_PARTY_NOTICES.md) · [美国科学里程碑](examples/documentary-edit/american-science-milestones/THIRD_PARTY_NOTICES.md)

用户添加的文稿、素材和音色沿用其各自许可或授权。再次分发素材或发布含有这些素材的成片时，按具体用途核对相应权利及署名要求。
