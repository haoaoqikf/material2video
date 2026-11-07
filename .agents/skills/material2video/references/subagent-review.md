# 独立子代理评审

适用性与机器格式见[评审契约](review-contract.md)，本页只规定隔离执行。试制与终审均使用新建上下文子代理，只给当前隔离包；不提供 DESIGN.md、研究理由、源码、作者身份、旧结论或匿名映射。

先盲看并落盘观察，再在独立对照包中提供中性原条件和实际目标媒体。对照只能读取同一评审者自身同轮盲看，先前报告不能污染新盲看。时间、输入文件与阅读报告 ID 由真实调用记录保存，不伪造工具执行。

终审使用未参与该作品前期试制的代理；常规一名综合终审，具体风险妨碍单人覆盖时显式分为结构、视觉文案两名互相隔离的终审者。时长、等级或追求高级本身不能作为增加人数理由。

## 执行与降级

代理只读取清单登记文件，按窗口、显示条件记录实际看见或听见的内容与限制。完整过程需要视频及有序时间码帧证据；无播放或试听能力如实限定，未知不写通过。自审/外部意见可补充，但不能授权独立项关闭。

实质争议交给新代理先盲看后核对原条件，不读旧结论、不投票挑宽松结果；重复失败比较匿名且同等精度的不同机制，分别记录收益和损失，不凑固定候选数量。

## 评审输出模板

报告 version=2，round 为 trial/final，reviewType 为 blind/consistency。每个 coverage 项与包内 id/window 完全一致，分别保存理解、表现、代表性的状态与观察，limitations 说明声音、连续性或平台遮挡等覆盖限制。pass 必须全部覆盖通过，fail 必须有具体失败项。评审包与报告字段详见[媒体格式](review-contract.md#媒体与报告格式)。

调用记录包含 id、reviewerId、freshContext、startedAt、completedAt、inputPaths、readReportIds；时间有时区且晚于包创建，输入只来自包内已登记文件。盲看 readReportIds=[]，对照仅包含自身同轮盲看报告 ID。

`freshContext` 记录评审代理最初创建时与作者上下文的隔离；同一隔离代理继续同轮对照时保持 `true`，不要求更换评审者。`inputPaths` 只列本次包内登记文件，自身盲看报告通过 `readReportIds` 单独追溯，不把包外报告路径再次放入 `inputPaths`。这两个字段的归类不改变实际读取范围、观察与结论；更正元数据须保留原件和原因，不补造调用。

## 评审包

只读包位于 outputs/review-pack/<id>/，manifest.json 维护净化媒体、原生与手机帧、时间码与摘要；实际源路径、源码依赖和采用目标留在包外私有绑定。盲看不包含目标媒体；有采用目标时对照在盲看导入之后建立。已投喂包不得修改，问题应重建新包。

<!-- generated:review-manifest:start -->
```json
{
  "version": 2,
  "reviewId": "R01",
  "cycleId": "example-cycle",
  "createdAt": "2026-11-07T00:00:00+00:00",
  "round": "trial",
  "fps": 30,
  "items": [
    {
      "id": "window-1",
      "path": "evidence-0000.mp4",
      "window": [
        0,
        90
      ],
      "dynamic": true,
      "sequence": []
    }
  ],
  "files": [
    {
      "path": "evidence-0000.mp4",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  ],
  "displaySizes": [
    1920,
    393
  ],
  "reviewType": "blind",
  "blindId": null,
  "requiresComparison": false
}
```
<!-- generated:review-manifest:end -->
