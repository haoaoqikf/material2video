# 事实与素材来源

本次重制核对电报、登月和阿帕网的采用材料。十项展示美国主导或参与的节点，保留移民、国际协作和全球研究积累的贡献边界。

本文件承载事实依据、来源页、作者、许可与改编记录。片尾保留晶体管照片的来源和图像处理。

## 十项事实

| 项目 | 核验页 | 贡献边界 |
|---|---|---|
| 电报1844 | [国会图书馆](https://www.loc.gov/item/mcc.019/) | 华盛顿—巴尔的摩示范；不声称全球最早电报概念 |
| 电话1876 | [国会图书馆](https://www.loc.gov/collections/alexander-graham-bell-papers/articles-and-essays/telephone-and-multiple-telegraph/) | 以贝尔清晰语音实验为节点；照片为1875年装置复制品历史照 |
| 飞机1903 | [Smithsonian](https://airandspace.si.edu/collection-objects/1903-wright-flyer/nasm_A19610048000) | 可控、持续动力飞行；照片为真实首飞 |
| 原子弹1945 | [美国能源部](https://www.energy.gov/management/july-16-1945-trinity-test) | Trinity首次核试验；指出人道代价，不将其等同基础核物理全部成果 |
| ENIAC1946 | [宾夕法尼亚大学](https://penntoday.upenn.edu/news/penns-eniac-worlds-first-electronic-computer-turns-80) | 早期通用电子数字计算里程碑；不使用无条件的世界第一台计算机 |
| 晶体管1947 | [贝尔实验室](https://www.nokia.com/bell-labs/about/history/) | 点接触晶体管；博物馆实物照不声称摄于1947 |
| 登月1969 | [NASA](https://www.nasa.gov/mission/apollo-11/) | 首次载人登月；月面档案片段 |
| ARPANET1969 | [DARPA](https://www.darpa.mil/news/features/arpanet) · [UCLA 当事人口述史](https://static.library.ucla.edu/oralhistory/text/masters/21198-zz002k431w-4-master.html) | 年末四节点拓扑中 UCLA、UCSB、SRI 为三角，犹他大学连 SRI。顺序用于讲解 |
| 基因组2003 | [NHGRI](https://www.genome.gov/about-genomics/educational-resources/fact-sheets/human-genome-project) | 国际合作参考序列，非当年已无缺口；照片为历史测序工作 |
| 大模型2020—2022 | [GPT-3 原始论文](https://arxiv.org/abs/2005.14165) · [ChatGPT 发布](https://openai.com/index/chatgpt/) | 这些是大模型走向公众的代表节点。片中问答由网页制作，用于演示语言生成，标明示意 |

## 搜索与取舍

2026-11-16 检索「1844 telegraph message paper tape」和「Apollo 11 lunar mobility」，查看美国国会图书馆展览原件及 NASA 月面日志。电报目录页部分访问返回 403，实际取得展览的第 1 段原图。登月以 16 毫米月面活动代替舱梯近景，原片低清且帧间有扫描重影，按真实人物位置和连续动作取舍。贝尔话筒分辨率较高的参照图用于构图研究，正式采用原先可恢复的早期装置复制品照片。阿帕网使用代码绘出 1969 年末拓扑。旧版用的 1970 年地图、旧登月片段、电报装置照和品牌图标见 Git `3bd0d620` 对应台账。

## 采用素材与许可

以下素材通过统一assets import进入内容寻址目录。对应原始URL和变换步骤见assets/recipe.json，可运行assets/fetch.py重新获取；媒体不入库，恢复时按登记摘要、尺寸和时长校验，已正确的文件直接复用。外站可能变更或限流，脚本失败会明确报错且不改写已有素材，不静默代换。

- `morse-tape`：Samuel Finley Breese Morse，1844 年 5 月 24 日电报纸带第 1 段，1024×357。美国国会图书馆手稿部公共领域原件。画面保留馆名，开场接第一项是同一镜头中的连续展示。[馆藏展览](https://www.loc.gov/exhibits/treasures/tr22c.html#obj3)
- 电报段沿原件左侧手写 W，在纸带下方按三次拟音揭示国际摩尔斯码的点、划、划。画面标注「现行国际摩尔斯码示意」，历史纸带按原扫描呈现。[ITU-R M.1677-1 附件一](https://www.itu.int/rec/R-REC-M.1677/en)
- `telephone`：作者未知，早期装置复制品照片，公共领域，453×348。照片旁标明复制品，波形为代码示意。[原文件](https://commons.wikimedia.org/wiki/File:First_Bell_telephone_1875.png)
- `flight`：[John T. Daniels](https://commons.wikimedia.org/wiki/File:First_flight2.jpg)；Public domain；实际6603×4280。
- `trinity`：[Jack W. Aeby, July 16, 1945, Civilian worker at Los Alamos laboratory, working under the aegis of the Manhattan Project.](https://commons.wikimedia.org/wiki/File:Trinity_shot_color.jpg)；Public domain；实际2426×2790。
- `eniac`：[Unidentified U.S. Army photographer](https://commons.wikimedia.org/wiki/File:Classic_shot_of_the_ENIAC_(full_resolution).jpg)；Public domain；实际2100×1518。
- `transistor`：Nokia Bell Labs 百年媒体资料库的点接触晶体管照片，1920×1080。源页提供下载，单张开放许可未声明，未发现针对当前用途的明确禁止。成片保留出处和裁切、调色记录。[Nokia Bell Labs 媒体资料库](https://www.nokia.com/about-us/newsroom/media-resources/nokia-bell-labs-centennial/)
- `moon-walk`：NASA 阿波罗 11 号 16 毫米胶卷 1092-K，旗帜旁的阿姆斯特朗和阿尔德林。原片按每秒一帧拍摄，索引发布版为 1920×1080、每秒 24 帧。采用发布版 169.416667 秒起连续窗口，保留 1440×1080 原档画面，裁去发布侧栏。以发布版一半的速度呈现和去除音轨，成片取前 3.5 秒。在使用窗口标 NASA。[Apollo Flight Journal 视频索引](https://www.apollojournals.org/afj/ap11fj/videoindex.html)
- `genome`：[National Human Genome Research Institute](https://www.genome.gov/about-genomics/educational-resources/fact-sheets/human-genome-project)；Public domain; https://www.genome.gov/image-gallery；实际1280×1134。

照片按画面需求裁切、调色或平移。首飞原件导入前重新 JPEG 压缩，保留 6603×4280。晶体管照片保留三角尖端和锗片接合的视觉上下文，片尾标记照片来源与改动。

电键和网络连线的声音使用运行时自带 `click`，作为拟音与事件共用触发帧。核试验和月面窗口使用视觉档案，输出不含档案原声。

NHGRI图片使用依据为[官方图库声明](https://www.genome.gov/image-gallery)，页面未另行标注版权；NASA依据[媒体使用政策](https://www.nasa.gov/nasa-brand-center/images-and-media/)，选用NASA制作的历史影像，不含商业配乐及第三方标识用途。其他图片的公共领域依据见逐件来源页。许可按项目逐件记录，不由“政府网站”域名推定。
