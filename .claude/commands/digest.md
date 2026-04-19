---
description: 今日摘要 — 待辦、逾期、進行中
---

On `/digest`:

Fan out across all 7 Lists in parallel via `tasks list`. Compute:
- 今日到期: due today (same Y-M-D)
- 逾期: due < today, not done
- 進行中: status == "in progress"
- Pending waiting: status == "pending"

Reply in a single Telegram message (繁中):
```
📅 今日摘要 (YYYY-MM-DD)
  ⚠ 逾期        N 筆
  📆 今日到期   N 筆
  🔵 進行中     N 筆
  ⏳ Pending   N 筆

前 3 件需要關注:
  • <name>  (<list>, ⚠/📆 標籤)
  ...
```
