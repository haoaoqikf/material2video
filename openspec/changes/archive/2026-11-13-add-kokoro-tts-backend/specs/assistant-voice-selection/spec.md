## MODIFIED Requirements

### Requirement: 实际配音参数可追溯

准备记录与成片溯源 MUST 保存实际后端、音色、语速、来源及有效助手记录；音色格式与可用候选 MUST 按后端校验和查询。五类作品的逐幕停顿声明 MUST 随准备画面参数保存；逐幕 speech.rate 当前不渲染，实际语速取作品或命令行设置。实际参数 MUST 参与准备指纹；修改配置后 MUST 重新准备与完整预演。音色或后端变化 MUST 使用独立的合成缓存。

#### Scenario: 覆盖与缓存
- **WHEN** 用不同音色或不同后端重新准备并导出
- **THEN** 缓存键改变，准备及溯源记录实际参数，旧预演不能授权新导出

#### Scenario: 按后端查询音色
- **WHEN** 作品声明 `backend=kokoro`
- **THEN** 音色查询与选择在 Kokoro 中文音色范围内进行，不混用 edge-tts 音色名
