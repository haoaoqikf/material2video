# 独立工程生成与命令委托阶段记录

本阶段对应任务 1.3、2.8、3.1；其余任务不因本记录自动完成。七例、样品／lookdev／时间线、可选组件采用、旧运行路径删除和最终归档仍待实施。

## 已实现边界

- 主项目和模板只接受 project v3、准备记录 contractVersion=3；材料、附属输入、协议入口及产物使用作品内可移动相对路径，拒绝旧版本、类型错误、越界和失效摘要。
- `m2v init` 复制完整基础模板，排除依赖、字体二进制、媒体、输出、缓存及目录链接；五类决定初始分镜和默认目录，不隐式安装三维／图表等组件。显式路径和生成后的搬移不要求类型目录层级。
- `validate/prepare/preview/render` 由同一类型适配器调用作品本地入口；QA同样委托本地检查，并独立核对报告的实际视频、摘要、准备身份和技术范围。status使用本地inspect，并复核相对候选收据。
- 默认入口是参数数组 `uv run --frozen python scripts/video.py`，使用作品cwd和环境，不经过shell，不注入主项目Python／Node模块路径。独立工程可省略runtime；只有接入m2v时才要求管理协议。
- 结果是唯一的 `__VIDEO_RESULT__` JSON行，外层只有version=1、command、result。result含匹配命令的status和非空environment；有产物时含相对path与SHA-256；prepare／inspect／preview／render还核对当前准备身份。
- 完整render必须匹配当前delivered候选、实际交付路径和摘要；preview／render均核对本地溯源的准备身份、实际帧窗和技术参数，然后独立完整解码，并复核期间未改动视频或磁盘manifest。成功退出与自报JSON均不能独立证明成功。
- production依赖绑定只读取作品拥有的可达源码、宿主、资源、字体和本地锁文件；动态引用保守扩大作品内范围。遍历前拒绝越界目录联接，不能通过字体扫描读取作品外目录。
- prepare/current在一次管理调用内复用已核验准备记录，避免重复完整哈希；没有跨命令缓存，后续编辑仍立即可见。

## 进程树方案与选型依据

沿用Python subprocess和现有psutil，不引入另一套执行框架。核对[Python subprocess官方文档](https://docs.python.org/3/library/subprocess.html#subprocess.Popen)与[Windows Job Objects官方文档](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)后，Windows采用标准库ctypes调用Job对象及KILL_ON_JOB_CLOSE：先创建只等stdin的启动屏障，归入Job后才释放作品命令，消除子进程先逃逸的竞态。正常返回、超时、取消或回调异常都终止并等待后代；主进程退出后仍持有stdout的浏览器也会收回。

POSIX使用独立进程组并补充psutil已观察后代回收；本机未执行POSIX验证，不据Windows结果宣称跨平台通过。未采用pywin32等额外运行依赖，因为当前只需少量稳定的原生Job接口，增加完整绑定包没有额外收益；没有自研渲染或动效实现。

## 实际验证

- 新增管理边界测试覆盖真实Windows超时／取消／正常退出后代／日志异常回收、环境隔离、五类完整生成、协议唯一结果／状态／摘要、旧版本与坏准备结构、实际采用输入变化、搬移后候选、主项目渲染器不可调用、目录联接、相对候选清理、同尺寸旧视频误报、预览帧窗、QA待检视频和磁盘配置变更。
- 管理相关用例按变动范围分次执行；失败后只重跑失败项和新增关联项，不把复跑累加为新增覆盖。相关已有optional review/status及output_cleanup测试，连同新增两项render事件顺序／失败不清理测试，共32项通过。未运行全仓回归。
- 本阶段改动的Python模块编译通过；`git diff --check`通过。TypeScript源码未改动，真实初始化实验仍以本地tsc和Vite执行构建；文档新增相对链接与v3 JSON示例已检查。
- 五类各自通过真实 `m2v init` 和本地独立uv环境 `scripts/video.py validate`：text-motion、data-evolution、principle-metaphor、spatial-3d、documentary-edit，约5.8至7.2秒／类。实验位于系统临时目录 `m2v-five-types-lz6pmtky`，结构化记录在忽略的 `.cache/standalone-verification/initial-types.json`。
- 当前源码快照生成到 `m2v-management-3rl85sne/a folder/independent-video`：冻结Node安装7.453秒；本地setup4.890秒；独立Python确认没有m2v包；直接prepare和m2v prepare身份完全一致。
- `m2v render`完整导出90帧1920×1080／30fps视频并独立复核，用时84.766秒；再运行本地render用时11.297秒，复用同一候选，未重新整片编码。三帧m2v preview20.812秒、status2.578秒、QA(step=5)4.078秒，均退出0且技术QA为pass。
- 当前准备指纹为 `f0ec046ecfbdb0933f16b79e5abcc26e486f389c0f5b3e8685a14b4e34219a4f`，复用视频SHA-256为 `134b92e323d9848a165e571b703f09e04a158ace0806a7cecd7077d70af154e9`。记录在 `.cache/standalone-verification/management-stage.json` 和实验目录日志；媒体及依赖不入Git。主项目可选委托本身需要主项目，直接脱库访问保护的既有实验见[基础阶段记录](implementation-base.md)，不将二者混称同一次实验。

## 发现、修复与独立复查

真实实验首先发现旧output_cleanup按进程cwd解释相对候选并误删；修复为作品根解析并保护当前候选及其收据。严格相对路径校验又发现Windows implementation_inputs仍使用反斜杠；改为as_posix并排除未参与运行的测试文件。两次失败结果保留于忽略的阶段记录，未改写为通过。

独立新上下文代理 `/root/standalone_management_review`审查并实际复现了候选误报、QA视频绑定、Windows junction越界及检查期间manifest变化。对应修复及必要的真实小媒体／目录联接复查均通过。候选、窗口、实际媒体和QA绑定无开放必改项；最终代码质量评分94/100，评分依据和限制来自该代理实际复查，不代表媒体美术评审。

逻辑影响是新版契约明确不兼容、主入口改为本地委托以及相对媒体身份；配置／输入变化或协议误报现在明确失败，render候选事件与失败不清理语义保留。性能增加流式日志队列、Job归属和独立媒体解码；一次管理调用内已消除重复全输入哈希。上述计时仅为本机三秒基础工程，不据此宣称七例或跨硬件性能。

剩余验证包括长浏览器／编码工作负载的异常、外部强杀主工具、POSIX、带旁白／字幕／声音的完整链路、复杂三维／公式／真实媒体、七例全部完整独立导出、外部检查器规则身份、样品及制作证据调用方。任务清单保持这些项目未完成；技术候选与本阶段代码审核不等于整个改造或制作完成。
