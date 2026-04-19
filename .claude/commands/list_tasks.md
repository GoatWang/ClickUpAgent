---
description: 列出指定 List 的任務（可加 --status / --tag 過濾）
---

On `/list_tasks [--list X] [--status s] [--tag t] [--open-only]`:

1. If `--list` missing → prompt 1–7 like `/add_task`.
2. Resolve list id from `data/oysterun_ids.json`.
3. `uv run python -m tool_scripts.clickup_api.tasks list --list-id <id> [--status s] [--tag t] [--no-closed if open-only]`

Telegram reply (terse — keep under 20 lines):
```
📋 <List name> (n open / m total)
  • <status emoji> <name>   #tag1 #tag2   (p1, due 04-25)
  ...
```

Status emoji: ⭕ to do · 🔵 in progress · ⏳ pending · ✅ done
