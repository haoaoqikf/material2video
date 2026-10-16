
## MODIFIED Requirements

### Requirement: 仅自身旁白要求明确音色
general 自身旁白 MUST 共用明确音色门禁。有效命令行 voice 优先于作品 voice；两者均缺失时 prepare MUST 失败并给出操作提示。语速与停顿保持独立。无自身旁白的作品 MUST 不因缺少音色失败。

#### Scenario: 缺失音色
- **WHEN** 直接 prepare 有自身旁白但未指定音色的作品
- **THEN** 在合成前失败，提示由助手选择或使用 --voice

#### Scenario: 静音与纯嵌入
- **WHEN** 通用作品没有旁白
- **THEN** 不要求选择音色，保留本地音床或静音

### Requirement: 实际配音参数可追溯
准备记录与成片溯源 MUST 保存实际音色、语速、来源及有效助手记录；general 的逐幕停顿声明 MUST 随准备画面参数保存；逐幕 speech.rate 当前不渲染，实际语速取作品或命令行设置。实际参数 MUST 参与准备指纹；修改配置后 MUST 重新准备与完整预演。音色变化 MUST 使用独立的合成缓存。

#### Scenario: 覆盖与缓存
- **WHEN** 用不同音色重新准备并导出
- **THEN** 缓存键改变，准备及溯源记录实际参数，旧预演不能授权新导出
