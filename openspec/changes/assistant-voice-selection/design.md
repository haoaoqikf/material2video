## Context

共享 tts.resolve 当前返回默认晓晓；三个有配音类型都调用它，但文章没有把音色参数写入 inputs。成片溯源已经保存 inputs，可沿用此通路。

## Goals / Non-Goals

共享离线门禁与实际参数记录，助手负责联网查询和语义判断。程序不新增模型调用、试听确认、主观自然度评分或后端。

## Decisions

- 用 tts.selection={mode:assistant,rationale,narrationSha256} 描述助手选择；摘要为 fingerprint(按播放顺序的非空旁白字符串数组)，保留分段边界，不含视觉或子作品旁白。沿用共享规范 JSON SHA256 算法，提供可直接调用的摘要帮助函数。
- tts.resolve 保持二元返回接口但不再回落默认音色；增加共享 preparation 解析接口，输入自身旁白列表，输出实际参数及来源记录，无旁白则不解析音色门禁。
- 来源记录含 backend、voice、rate、source(command-line/project/assistant)，助手记录仅在没有命令行 voice 时带入；保持语速与停顿独立，逐幕覆盖沿用现有 speech 输入。
- 三个适配器把共享实际记录写入 inputs.tts；成片已有 inputs 通路直接携带，不增加第二处事实。助手选择结果写入 project.json，配置变化由现有 materialFingerprint 检测。
- 仅在 prepare 强制选音，init/validate 可处理尚未完成选音的材料；明确音色格式仍由配置校验检查。有效手动覆盖不继承旧助手理由。

## Risks / Trade-offs

- 缺少音色的旧有声作品需要迁移 → 错误给出 --voice 与作品配置提示，更新固定示例与受影响测试。
- 音色标签不代表听感 → 文档明确选择依据而非听感保证，支持用户覆盖。
- 旁白摘要只检测选择上下文变化，不证明助手实际阅读 → Skill 明确要求真实阅读与选择理由，不伪造试听。

## Migration Plan

先实现共享规则和测试，再同步文档与三个固定示例；读取在线音色列表，对三个当前作品保存助手判断并真实生成预演、成片。实施提交通过后同步主规格、归档并单独提交。回滚代码时既有明确 voice 仍兼容，新增 selection 需随回滚移除。
