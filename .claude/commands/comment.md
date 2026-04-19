---
description: 在任務底下留言
---

On `/comment <target> <text>`:

1. Fuzzy-resolve target.
2. Confirm card: `Comment on "<name>": "<text>"` → `y`.
3. `uv run python -m tool_scripts.clickup_api.tasks comment <task_id> "<text>"`

Reply: `💬 已留言：<task_url>`
