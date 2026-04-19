---
description: 設定任務的 PR 連結（/update_task --pr 的捷徑）
---

On `/set_pr <target> <url>`:

1. Fuzzy-resolve `<target>` (§5 flow).
2. Confirm card: `Set PR = <url> on "<name>" ?` → `y` to proceed.
3. `uv run python -m tool_scripts.clickup_api.custom_fields set <task_id> PR <url>`

Reply: `🔗 PR 已設定：<task_url>`
