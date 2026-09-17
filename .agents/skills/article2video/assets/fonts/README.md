# 随仓库分发的字体资产

这层资产存在的理由只有一个：**字体是观感的第一个变量，也是「配色一样却看起来不一样」的主因。**
渲染是逐帧截图，字体必须离线可用；因此这里把用到的两套可变字体直接入库，
而不是依赖 CDN 或渲染机器的系统字体。

未启用设计语言预设的页面不会引用这些文件，行为与本次变更前一致。

## 文件清单

| 文件 | 字体 | 版本 | 大小 | SHA-256 |
| --- | --- | --- | --- | --- |
| `Inter-Variable.ttf` | Inter | Version 4.001;git-66647c0bb | 856 KB | `29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031` |
| `NotoSansSC-Variable.ttf` | Noto Sans SC | Version 2.004-H2 | 17.0 MB | `a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da` |
| `OFL-Inter.txt` | Inter 的许可证原文 | — | 4.3 KB | — |
| `OFL-NotoSansSC.txt` | Noto Sans SC 的许可证原文 | — | 4.3 KB | — |

来源：Google Fonts 官方仓库（`github.com/google/fonts`，路径 `ofl/inter` 与 `ofl/notosanssc`），
以仓库中的可变字体原文件直接落盘，未做任何重打包或子集化。

## 许可

两套字体均为 **SIL Open Font License 1.1**，许可证原文随字体一同分发。
OFL 允许随产品分发与再分发字体文件，要求许可证随附、不得单独售卖字体本身、
不得使用保留字体名称（Reserved Font Name）发布修改版。
本项目不对字体文件做修改，只做分发与引用。

## 使用方式

引用方只需要引入 `../keynote.css`，其中已用 `@font-face` 声明两套字体：

```css
@font-face {
  font-family: "A2V Sans";
  src: url("fonts/NotoSansSC-Variable.ttf") format("truetype");
  font-weight: 100 900;
  font-display: block;
}
```

要点：

- `font-weight: 100 900`：可变字体必须声明字重区间，否则只有默认字重可用；
- `font-display: block`：避免回退字体先渲染一帧（逐帧截图会把那一帧拍进去）；
- 字体栈把 Inter 放在 Noto Sans SC 之前，拉丁与数字用 Inter，汉字自动落到 Noto Sans SC；
- 行高由设计语言**显式指定**，不依赖字体自带度量。本机 Chromium 实测：100px 字号下
  两套字体的单行盒高度都是 132px，混排同样是 132px。

## 字体缺失时

字体路径由 `tests/test_offline_assets.py` 守住，共三层：

1. `@font-face` 必须引用 `fonts/` 下的两个文件名；
2. 资产层不得出现任何外部 URL（注释里记来源不算），且每一处 `url()` 都必须
   指向仓库内真实存在的文件——指向拼错的路径不会报错，只会安静地不生效；
3. 限帧导出必须跑得通。

注意 `validate.py` **不**检查字体：渲染前的本地资源查找对缺失项是静默跳过，
因此不要把「校验通过」当成「字体没问题」。真正的观感差异只有看成片才会发现，
这也是上面第 2 条必须存在的原因。

## 已知取舍

- 中文可变字体体积约 17MB。仓库当前总体量在 200MB 量级，可接受；
  若将来需要瘦身，应按「字体子集化 + 多份子集」处理，而不是回退到系统字体。
- 当前不做子集化：子集化会让「同一分镜换一篇文章」需要重新处理字体，
  与「克隆即可渲染」的目标冲突。
