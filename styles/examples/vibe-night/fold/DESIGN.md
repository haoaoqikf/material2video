# 本轮示例设计

珠串、第 6 颗与细胞是贯穿对象；尺度变化从局部进入整体，回场用于理解由黏点到长杆再到细胞变形的关系。

切镜理由：`mutation` 局部建立第 6 颗的玫红身份，`sickle` 拉远展示细胞结果，`fold` 回到珠链解释内部过程；`sticky` 与 `rod` 保持同一黏点／团块关系，`push` 回到细胞让结果获得因果含义。颜色和细胞轮廓是跨镜锚点，是否足够可辨仍须实际观察。

核心时间预算（秒，允许重叠）：4.4–8.4 建立并阅读突变，8.4–12.6 观察拉远与结果，15–19.2 阅读和观察折叠，19.2–22.8 留意黏点，22.8–26 观察团块接合，26–29.2 观察细胞变化与回场，29.2–33 消化结论。关键接触能否看清尚待完整窗口评审。

下表是计划与检查范围，不代表独立观察已通过。每个窗口同时核对阅读、动作与结果消化；必要时按实际画面细分，不能用时间表代替观察。

| 幕 | 全片帧 [起,止) | 秒 | 认回锚点 | 时间预算与注意力（秒） |
|---|---|---|---|---|
| chain | 0–132 | 0.0–4.4 | 珠链整体与第 6 颗 | 0–0.5 建立；0.5–4.2 阅读并观察珠子逐颗出现 0.2–2.0；4.2–4.4 消化 |
| mutation | 132–252 | 4.4–8.4 | 第 6 颗的玫红身份 | 4.4–4.9 建立；4.9–6.0 观察翻面 5.73；6.0–8.2 阅读并观察突变结果；8.2–8.4 消化 |
| sickle | 252–378 | 8.4–12.6 | 细胞轮廓 | 8.4–8.9 建立；8.9–10.7 阅读并观察拉远；10.7–12.3 观察细胞弯曲 10.73；12.3–12.6 消化 |
| question | 378–450 | 12.6–15.0 | 同一细胞轮廓 | 12.6–12.9 建立；12.9–14.8 阅读并观察细胞全貌；14.8–15.0 消化 |
| fold | 450–576 | 15.0–19.2 | 第 6 颗与黏点 | 15.0–15.5 建立；15.0–17.0 阅读并观察折叠 17.00；17.0–18.9 观察氧分子落点 18.33；18.9–19.2 消化 |
| sticky | 576–684 | 19.2–22.8 | 同一黏点与鼓出的玫红珠子 | 19.2–19.7 建立；19.7–20.2 阅读；20.2–22.5 观察鼓出与脉冲 20.20；22.5–22.8 消化 |
| rod | 684–780 | 22.8–26.0 | 主团与接合部位 | 22.8–23.2 建立；23.2–23.7 阅读；23.7–25.1 观察八次接合 23.73–25.13；25.1–26.0 观察长杆成形 |
| push | 780–876 | 26.0–29.2 | 同一细胞轮廓 | 26.0–26.4 建立；26.4–28.0 阅读并观察顶弯 28.00；28.0–28.9 观察细胞变形；28.9–29.2 消化 |
| closing | 876–990 | 29.2–33.0 | 同一细胞与长杆 | 29.2–29.5 建立；29.5–32.8 阅读并观察回到全貌 29.53；32.8–33.0 消化 |

## 机器合同

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "fold-methods-2026-10-29",
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
            "check-mutation",
            "check-sickle",
            "check-fold",
            "check-sticky",
            "check-rod",
            "check-push"
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
      "id": "chain",
      "durationFrames": 132,
      "shots": [
        {
          "id": "shot-chain",
          "tier": "B",
          "window": [
            0,
            132
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-chain",
          "shotId": "shot-chain",
          "frame": 66,
          "window": [
            0,
            132
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
      "id": "mutation",
      "durationFrames": 120,
      "shots": [
        {
          "id": "shot-mutation",
          "tier": "A",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-mutation",
          "shotId": "shot-mutation",
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
      "id": "sickle",
      "durationFrames": 126,
      "shots": [
        {
          "id": "shot-sickle",
          "tier": "B",
          "window": [
            0,
            126
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-sickle",
          "shotId": "shot-sickle",
          "frame": 63,
          "window": [
            0,
            126
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
      "id": "question",
      "durationFrames": 72,
      "shots": [
        {
          "id": "shot-question",
          "tier": "B",
          "window": [
            0,
            72
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-question",
          "shotId": "shot-question",
          "frame": 36,
          "window": [
            0,
            72
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
      "id": "fold",
      "durationFrames": 126,
      "shots": [
        {
          "id": "shot-fold",
          "tier": "B",
          "window": [
            0,
            126
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-fold",
          "shotId": "shot-fold",
          "frame": 63,
          "window": [
            0,
            126
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
      "id": "sticky",
      "durationFrames": 108,
      "shots": [
        {
          "id": "shot-sticky",
          "tier": "A",
          "window": [
            0,
            108
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-sticky",
          "shotId": "shot-sticky",
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
      "id": "rod",
      "durationFrames": 96,
      "shots": [
        {
          "id": "shot-rod",
          "tier": "A",
          "window": [
            0,
            96
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-rod",
          "shotId": "shot-rod",
          "frame": 48,
          "window": [
            0,
            96
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
      "id": "push",
      "durationFrames": 96,
      "shots": [
        {
          "id": "shot-push",
          "tier": "A",
          "window": [
            0,
            96
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-push",
          "shotId": "shot-push",
          "frame": 48,
          "window": [
            0,
            96
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
      "id": "closing",
      "durationFrames": 114,
      "shots": [
        {
          "id": "shot-closing",
          "tier": "B",
          "window": [
            0,
            114
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "check-closing",
          "shotId": "shot-closing",
          "frame": 57,
          "window": [
            0,
            114
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
