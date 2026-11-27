# 《运气在舞台上》：把三成机会改为两成，第三柱会怎样？

[作品页](../../examples/principle-metaphor/luck-on-stage/README.md)又题为《运气到底是什么》。其中的三柱镜头没有抽样、掷骰子或模拟一批真实结果。每根柱表示一组条件下的**预期成功次数**。[分镜第 11 行](../../examples/principle-metaphor/luck-on-stage/storyboard.json#L11)限定了结论：当每次的成功概率都是 `p`，尝试 `N` 次的期望为 `N×p`，不是至少成功一次的概率，也不保证实际次数。下面只改变第三组的单次概率，对照源码推导画面，不改仓库中的正式示例，也不声称已经渲染变体。

## 找到第三组，而不是改屏幕上的数字

[分镜第 249–268 行](../../examples/principle-metaphor/luck-on-stage/storyboard.json#L249)定义 `bars` 场景和入口 `scenes/bars.tsx`；[第 270–285 行](../../examples/principle-metaphor/luck-on-stage/storyboard.json#L270)安排「只增加次数」再到「再提高单次概率」的叙述顺序。打开[场景源码第 7 行](../../examples/principle-metaphor/luck-on-stage/scenes/bars.tsx#L7)，三组条件分别为 10 次、10%；30 次、10%；30 次、30%。只有第二步改变尝试次数，第三步把次数固定在 30，单独比较概率。

在自己的副本中，把第三项 `{n:30,p:30,result:9}` 改成 `{n:30,p:20,result:6}`。这里 `p` 用百分数整数，写 `20`，不是 `0.2`。概念上只改了一个概率输入，但 `result` 是同一对象中预先写好的期望值，并不会根据 `p` 自动重算，因此必须把派生字段一起改成 `30×20÷100=6`。只改 `p` 会把标签改成两成，却仍绘制九次的柱子：那是数据不一致，不是模型出现了意外结果。

## 同一把尺上，第三柱从 414 降到 276

[源码第 9–16 行](../../examples/principle-metaphor/luck-on-stage/scenes/bars.tsx#L9)把柱子的目标高度写成 `result / 9 × 414`，再乘由落地至锁定推进的入场系数。保留这把尺，不把 `9` 改成 `6`。在锁定之后、拉远结束的 `zoom = 1` 视角下，前两柱仍是 46 和 138 个场景坐标单位，第三柱从 414 降为 276。[第 57–69 行](../../examples/principle-metaphor/luck-on-stage/scenes/bars.tsx#L57)让三根柱从同一条基线向上长，结果直接取 `s.result`，条件标签取 `s.n` 和 `s.p`。因此第三柱的「30 次 · 30%」「9」会变成「30 次 · 20%」「6」，前两组不变。

可在两版里对照[分镜第 311–324 行](../../examples/principle-metaphor/luck-on-stage/storyboard.json#L311)登记的场内帧：第三组在 124 帧起跳，150 帧落地，164 帧锁定，180 帧进入读数。比较 180 帧而非入场中的任意截图，可以避开正在增长的柱子。[源码第 18–39、49–52 行](../../examples/principle-metaphor/luck-on-stage/scenes/bars.tsx#L18)用事件和时间驱动小球、镜头拉远及闪光；这些不随第三组概率改动。定量差异发生在柱高与文字，而不是小球是否落中目标。

若要亲自做双版本对照，先按作品说明恢复独立工程，再在副本内预览原版和改版。分镜在[第 15–18 行](../../examples/principle-metaphor/luck-on-stage/storyboard.json#L15)从开场开始，四幕依次为 150、210、30、210 帧，入场都是硬切；`bars` 从全片第 600 帧开始。在作品目录运行 `pnpm run preview --start-seconds 20 --limit-frames 210` 可请求三柱窗口，拿预览内 6 秒的画面比对，对应局部 180 帧。除了读标题下方的数，也比一下第三柱的顶沿：若数字变了而柱仍高到原位，说明改错了渲染输入或误用了旧预览。

## 结论仍成立，增益变小了

第二组和第三组均尝试 30 次。原版的期望从 3 到 9，是三倍；变体从 3 到 6，是两倍。尝试次数不变时，提高单次成功概率仍能提高预期成功次数，只是提高的幅度小了。两组都没有承诺任一批实际尝试一定成功这么多次。若需要解释「至少成功一次」，还需另给概率模型；不能把这根柱直接改名成它。

只研究三柱，到这里就够了。若要导出贯穿全片的两成变体，还得同步下游：面积镜头在[第 8–12 行](../../examples/principle-metaphor/luck-on-stage/scenes/area.tsx#L8)把高度从 10% 推到 30%，[第 19–23 行](../../examples/principle-metaphor/luck-on-stage/scenes/area.tsx#L19)又把 `30 × 30% = 9` 写成字卡；按两成改写后，固定宽度下的目标高度由 360 降为 240，公式应为 `30 × 20% = 6`。[分镜第 369 行](../../examples/principle-metaphor/luck-on-stage/storyboard.json#L369)的「预期成功9次」和[收尾第 12–16 行](../../examples/principle-metaphor/luck-on-stage/scenes/closing.tsx#L12)重现的公式也要一起对齐。此前的[概率盘](../../examples/principle-metaphor/luck-on-stage/scenes/probability.tsx#L6)有自己的三成演示；只改第三组时不需要改它，但若叙事要把两幕当作同一个概率，就应一起修改并重新核对前后的文案。这个例子划清了边界：一个局部输入可以解释一组因果差异，却不是一键重算整部视频的开关。
