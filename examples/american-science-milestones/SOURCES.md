# 事实与素材来源

核验日期：2026-10-19。选取美国主导的代表成果，包含在美工作的移民与国际协作；不主张计算机、互联网或人工智能为一国独创。1776为建国叙事起点，第一项技术里程碑始于1844。

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
| ARPANET1969 | [DARPA](https://www.darpa.mil/news/features/arpanet) | 初始四节点网络，互联网先驱；画面档案图为1970年的网络 |
| 基因组2003 | [NHGRI](https://www.genome.gov/about-genomics/educational-resources/fact-sheets/human-genome-project) | 国际合作参考序列，非当年已无缺口；照片为历史测序工作 |
| 大模型2020—2022 | [GPT-3原始论文](https://arxiv.org/abs/2005.14165)、[2022年对话模型发布](https://openai.com/index/chatgpt/) | OpenAI代表进展；全球研究积累，不声称首次发明所有大模型 |

## 搜索与取舍

优先官方档案，其次许可明确公共媒体。国会图书馆API部分返回403，但官方事实页及公共领域档案可通过Commons原片获取；Commons原尺寸照片部分429，晶体管采用官方建议的1280像素缩略版本。NASA和NHGRI可取得可用素材。大模型已检索原始论文及发布资料，但未取得能真实呈现模型内部运算且许可明确的历史动态素材，因此采用原创代码动画并标注原理示意，不用机器人或数据中心代称模型本体。

## 九项素材与许可

以下素材通过统一assets import进入内容寻址目录。对应原始URL和变换步骤见assets/recipe.json，可运行assets/fetch.py重新获取。外站可能变更或限流，脚本失败会明确报错，不静默代换。

- **telegraph**：[未知](https://commons.wikimedia.org/wiki/File:Morse_telegraph.jpg)；Public domain；实际1308×1988。
- **telephone**：[Unknown authorUnknown author](https://commons.wikimedia.org/wiki/File:First_Bell_telephone_1875.png)；Public domain；实际453×348。
- **flight**：[John T. Daniels](https://commons.wikimedia.org/wiki/File:First_flight2.jpg)；Public domain；实际6603×4280。
- **trinity**：[Jack W. Aeby, July 16, 1945, Civilian worker at Los Alamos laboratory, working under the aegis of the Manhattan Project.](https://commons.wikimedia.org/wiki/File:Trinity_shot_color.jpg)；Public domain；实际2426×2790。
- **eniac**：[Unidentified U.S. Army photographer](https://commons.wikimedia.org/wiki/File:Classic_shot_of_the_ENIAC_(full_resolution).jpg)；Public domain；实际2100×1518。
- **transistor**：[Unitronic](https://commons.wikimedia.org/wiki/File:1st-Transistor.jpg)；CC BY-SA 3.0 https://creativecommons.org/licenses/by-sa/3.0；实际1280×960。
- **arpanet**：[UCLA and BBN](https://commons.wikimedia.org/wiki/File:ARPANET_1970_Map.png)；CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0；实际684×463。
- **moon**：[NASA](https://images.nasa.gov/details/Apollo_11_Introduction_720p)；Public domain (NASA-produced footage); https://www.nasa.gov/nasa-brand-center/images-and-media/；实际1280×720。
- **genome**：[National Human Genome Research Institute](https://www.genome.gov/about-genomics/educational-resources/fact-sheets/human-genome-project)；Public domain; https://www.genome.gov/image-gallery；实际1280×1134。

照片在成片中裁切、调色及平移；首飞原图仅重新JPEG压缩，保留6603×4280原生尺寸。NASA片段截取原片84.25–91.75秒以0.75倍慢放至10秒并去音轨，其余不改内容。晶体管图片作者Unitronic，许可[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)；ARPANET图作者UCLA与BBN，许可[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)。其改编内容与整支成片按[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)提供，保留署名与来源，不暗示背书。

NHGRI图片使用依据为[官方图库声明](https://www.genome.gov/image-gallery)，页面未另行标注版权；NASA依据[媒体使用政策](https://www.nasa.gov/nasa-brand-center/images-and-media/)，选用NASA制作的历史影像，不含商业配乐及第三方标识用途。其他图片的公共领域依据见逐件来源页。许可按项目逐件记录，不由“政府网站”域名推定。
