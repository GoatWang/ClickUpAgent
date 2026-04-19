---
description: 從任務移除 tag（預設），加 --from-space 會從 Space 整個刪掉
---

On `/rm_tag <name> [--task <target>] [--from-space]`:

### Remove from task (default)
1. Require `--task`. Fuzzy-resolve.
2. Confirm card: `Remove tag '<name>' from "<task name>" ?` → `y`.
3. `uv run python -m tool_scripts.clickup_api.tags detach <task_id> <name>`

### Delete from Space (destructive; affects all tasks using it)
`--from-space`:
1. Extra-strong confirm: `⚠ 這會從整個 Space 移除 tag '<name>'，所有用到這個 tag 的任務都會失去它。確定？reply CONFIRM`
2. Only proceed if user replies exactly `CONFIRM` (case-sensitive).
3. `curl DELETE /space/<id>/tag/<name>` (or via tags module when added).
