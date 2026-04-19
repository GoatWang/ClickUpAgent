---
description: 列出逾期任務（due_date < 現在且未完成）
---

On `/overdue`:

`uv run python -m tool_scripts.clickup_api.tasks list --list-id <each list>` → filter client-side
where `due_date` is set, `< int(time.time()*1000)`, and status not `done`.

Reply:
```
⚠ 逾期 (n 筆):
  • <name>  (<list>, 逾期 N 天)
  ...
```
