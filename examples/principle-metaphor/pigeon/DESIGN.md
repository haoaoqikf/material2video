# 本轮示例设计

本轮合并设计记录和执行引用，未重新渲染或补造独立评审；历史观察只作原版本依据。来源与许可继续沿用既有登记。

## 全片原则

相关方法：[视觉创意导演方法](../../../.agents/skills/material2video/references/visual-creative-direction.md)。

计时器、箱子和角色保持同一房间与全片时间。由计时器转向角色，再回到计时器；目标是看清食物周期和动作的先后，真实周期为 15 秒。

切镜理由：`feeder` 建立食槽与计时器的关系，`wander` 转向鸟的行为但保留右侧物件作为空间锚点，`coincide` 靠近食槽观察结果，`again` 再用计时器与鸟同框解释第二次喂食。两次落粮的间隔来自同一时钟，不以行为强度的虚构读数解释。

核心时间预算（秒，允许重叠）：9–13.5 建立并阅读找食，13.5–15 观察转圈与接近喂食，15–16.2 观察食槽打开和食物到达，16.2–19.2 看结果；26.5–29.9 观察重复行为与时钟，30–32.8 观察第二次喂食并消化。关键动作是否足够清楚尚待完整窗口评审。

下表是计划与检查范围，不代表独立观察已通过。每个窗口同时核对阅读、动作与结果消化；必要时按实际画面细分，不能用时间表代替观察。

## 逐场设计表

以下是唯一逐场执行与验收索引。共享规则全片声明，具体窗口与行为以本行及其可编辑来源为准；修订后须实际复查，表格不代表当前已通过。

| 幕 | 全片帧 [起,止) | 秒 | 认回锚点 | 时间预算与注意力（秒） | 实现与检查 |
|---|---|---|---|---|---|
| box | 0–120 | 0.0–4.0 | 箱壁与鸽子 | 0–0.4 建立；0.4–3.8 阅读字幕并观察鸽子在箱内；3.8–4.0 消化 | [scenes/pigeon.tsx](scenes/pigeon.tsx) / scene=box，事件以 storyboard.events 为准；check-box，核对本行对象认回和动作先后 |
| feeder | 120–270 | 4.0–9.0 | 墙上计时器、右侧食槽 | 4.0–4.5 建立；4.5–8.7 阅读并观察秒针逐格与每秒发声；8.7–9.0 消化 | [scenes/pigeon.tsx](scenes/pigeon.tsx) / scene=feeder，事件以 storyboard.events 为准；check-feeder，核对本行对象认回和动作先后 |
| wander | 270–468 | 9.0–15.6 | 鸽子与右侧食槽、计时器 | 9.0–9.4 建立；9.4–15.2 阅读找食，并观察啄食 10.4、首次转圈 13.5、食槽打开 15.0；15.2–15.6 消化 | [scenes/pigeon.tsx](scenes/pigeon.tsx) / scene=wander，事件以 storyboard.events 为准；check-wander，核对本行对象认回和动作先后 |
| coincide | 468–576 | 15.6–19.2 | 食槽与落下的食物 | 15.6–15.9 建立；15.9–18.9 阅读，并观察食物到达 15.8、啄食 16.2 与 17.6；18.9–19.2 消化 | [scenes/pigeon.tsx](scenes/pigeon.tsx) / scene=coincide，事件以 storyboard.events 为准；check-coincide，核对本行对象认回和动作先后 |
| repeat | 576–795 | 19.2–26.5 | 鸽子与计时器、食槽 | 19.2–19.6 建立；19.6–22.4 阅读并观察转圈 20.2；22.4–26.2 阅读并观察转圈 23.6、26.4；26.2–26.5 消化 | [scenes/pigeon.tsx](scenes/pigeon.tsx) / scene=repeat，事件以 storyboard.events 为准；check-repeat，核对本行对象认回和动作先后 |
| again | 795–990 | 26.5–33.0 | 鸽子与计时器同框 | 26.5–26.9 建立；26.9–29.1 阅读并观察转圈 28.4 与倒计时；29.1–30.2 停顿；30.2–31.0 阅读并观察再次落粮 30.0–30.2；31.0–33.0 阅读结论“它把巧合，当成了规律” | [scenes/pigeon.tsx](scenes/pigeon.tsx) / scene=again，事件以 storyboard.events 为准；check-again，核对本行对象认回和动作先后 |

## 必要附件：制作合同

保留原周期合同和已记录的风险范围，不把文档整理当作重新制作或验收。

### 机器合同

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "pigeon-methods-2026-10-29",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "跨场对象连续、动作与结果关系需完整窗口独立观察；当前候选证据尚未登记。",
    "risks": [
      {
        "id": "core-relation",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "check-wander",
            "check-coincide",
            "check-repeat",
            "check-again"
          ]
        },
        "reason": "对象认回、过程和结果关联尚待当前候选实证",
        "requiredEvidence": [
          "完整动态窗口与独立观察"
        ]
      }
    ]
  },
  "scenes": [
    {
      "id": "box",
      "durationFrames": 120,
      "shots": [
        {
          "id": "shot-box",
          "tier": "B",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-box",
          "shotId": "shot-box",
          "frame": 60,
          "window": [
            0,
            120
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [],
          "sampleStep": 5
        }
      ]
    },
    {
      "id": "feeder",
      "durationFrames": 150,
      "shots": [
        {
          "id": "shot-feeder",
          "tier": "B",
          "window": [
            0,
            150
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-feeder",
          "shotId": "shot-feeder",
          "frame": 75,
          "window": [
            0,
            150
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [],
          "sampleStep": 5
        }
      ]
    },
    {
      "id": "wander",
      "durationFrames": 198,
      "shots": [
        {
          "id": "shot-wander",
          "tier": "A",
          "window": [
            0,
            198
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-wander",
          "shotId": "shot-wander",
          "frame": 99,
          "window": [
            0,
            198
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [],
          "sampleStep": 5
        }
      ]
    },
    {
      "id": "coincide",
      "durationFrames": 108,
      "shots": [
        {
          "id": "shot-coincide",
          "tier": "B",
          "window": [
            0,
            108
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-coincide",
          "shotId": "shot-coincide",
          "frame": 54,
          "window": [
            0,
            108
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [],
          "sampleStep": 5
        }
      ]
    },
    {
      "id": "repeat",
      "durationFrames": 219,
      "shots": [
        {
          "id": "shot-repeat",
          "tier": "B",
          "window": [
            0,
            219
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-repeat",
          "shotId": "shot-repeat",
          "frame": 109,
          "window": [
            0,
            219
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [],
          "sampleStep": 5
        }
      ]
    },
    {
      "id": "again",
      "durationFrames": 195,
      "shots": [
        {
          "id": "shot-again",
          "tier": "A",
          "window": [
            0,
            195
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-again",
          "shotId": "shot-again",
          "frame": 97,
          "window": [
            0,
            195
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [],
          "sampleStep": 5
        }
      ]
    }
  ]
}
```
