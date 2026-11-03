# 《接》练习：把第 100 刀调到字幕之后

这个练习只改时间，不改数学、场次、画面结构或声音：把 S3 的刀数计数器拉长到 20.0 秒，观察计数、字幕与下一页交接是否仍然同步。

## 改哪里

打开 `scenes/compound-connect.tsx`，找到：

```tsx
cuts: [{start: 426, end: 560, from: 1, to: 100}],
```

把 `end` 从 `560` 改成 `600`。计数器会在 20.0 秒（S3 末帧）才落到 100 刀。

再打开 `storyboard.json`，找到第 3 条屏幕字幕（`100 刀，一把凿子；第 37 刀滑了。`），把它的 `endFrame` 从 `592` 改成 `600`，让字幕与计数同时收束。

## 预期变化

- 第 37 刀仍在帧 500 发生，滑刀标记与事件音不变。
- 第 100 刀从 18.7 秒推迟到 20.0 秒，金色落点与 `cut-100` 事件音不再对齐；这是练习故意留下的可见问题。
- S4 在帧 600 开始，计数会在页面边界前才落定，页面交接变紧。
- 时长、硬切（帧 1230）、总场数、字幕条数都不变。

## 验证

```powershell
uv run m2v validate --project styles/dark-proof/examples/compound-connect
uv run m2v prepare --project styles/dark-proof/examples/compound-connect
uv run m2v lookdev --project styles/dark-proof/examples/compound-connect --sheet 18.6 19.9 20.1
```

打开 `outputs/lookdev/still-000558.png`、`still-000597.png` 与 `still-000603.png`：第 100 刀应在 S3 最后一帧附近落定，S4 已经进入回环页。

## 恢复

```powershell
git checkout -- styles/dark-proof/examples/compound-connect/scenes/compound-connect.tsx
git checkout -- styles/dark-proof/examples/compound-connect/storyboard.json
uv run m2v prepare --project styles/dark-proof/examples/compound-connect
```

练习只在工作区进行；不要把推迟后的时间提交。若确实要改节奏，须同步更新 `DESIGN.md` 的场次表、检查点窗口与 `VERIFICATION.md`，再重新评审。
