## 背景

示例作品的源材料在 `examples/<slug>/`，但 `delivery.outputs`、`qa.delivered_video`、general 的
preview/render 与 render 后清理都把示例重定向到 `videos/examples/<slug>/outputs/`。用户要求把
产物归入示例目录，本次一并迁移已有产物。

## 决策

- **单一输出根**：示例与正式作品都使用作品根下的 `outputs/`，删除四处 `parent.name == "examples"`
  分支，减少路径推导的分叉。
- **忽略规则不变**：`.gitignore` 的 `outputs/` 已覆盖 `examples/*/outputs/`，示例源仍入库，
  产物仍不入库，无需新增忽略规则。
- **迁移策略**：按文件合并，同名同内容跳过；内容不同时保留修改时间较新者；被较新目标版本取代的
  旧源文件另存到 `outputs/.superseded-from-videos/`，避免评审证据直接消失。
- **无兼容层**：不保留旧位置探测或回退写入，`videos/examples/` 不再接收新产物。

## 限制

- `videos/examples/compound-interest/outputs/` 下两个内容目录（`candidates/m2v-explainer-uq6bx0g6`、
  `qa/sequence-avtdbj4i`）在迁移时拒绝访问；当前会话无管理员权限，`takeown`/`icacls` 也无法接管。
  其中可读的同级文件已全部确认在目标中，内容一致的副本；两个目录的内容未能迁移，保留原位并在交付说明中披露。
- 已迁移的 `delivery.json` 等记录仍保存旧路径，属于既有运行产物；下次 render 会按新位置重建。
