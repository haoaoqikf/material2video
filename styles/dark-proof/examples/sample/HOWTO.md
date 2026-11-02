# 《样本》练习：移动 3 个金点

这个练习改一处点阵坐标，观察“同一画面、不同理解”的构图如何变化；不改变数学、时长、声音或字幕。

## 改哪里

打开 `scenes/sample.tsx`，找到：

```tsx
const GOLD_INDEX = [524, 525, 526];
```

1000 个点按 50 列 × 20 行排列，下标 = 行 × 50 + 列。`524/525/526` 是第 10 行相邻三点，位于点阵中央。把它改成：

```tsx
const GOLD_INDEX = [258, 259, 260];
```

这是第 5 行、第 8–10 列，三个金点会一起移到点阵左上区域。

## 预期变化

- 开场与结尾的 3 个金点一起移动，仍是相邻三点、仍是 1000 点中的 3 点。
- `3 / 1000 = 0.3%`、字幕、声音事件、硬切时间都不变。
- 点阵密度不变，只是强调位置改变。

## 验证

```powershell
uv run m2v validate --project styles/dark-proof/examples/sample
uv run m2v prepare --project styles/dark-proof/examples/sample
uv run m2v lookdev --project styles/dark-proof/examples/sample --sheet 4 55
```

打开 `outputs/lookdev/still-000120.png` 与 `still-001650.png`：三个金点应在点阵左上角，而不是中央。

## 恢复

```powershell
git checkout -- styles/dark-proof/examples/sample/scenes/sample.tsx
uv run m2v prepare --project styles/dark-proof/examples/sample
```

练习只在工作区进行；不要把改过的 `GOLD_INDEX` 提交。若想保留一个新构图，先更新 `DESIGN.md` 的视觉母题说明与代表帧记录，再重新评审。
