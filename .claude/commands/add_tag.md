---
description: 建立新 tag（可指定 --color），可直接附加到任務
---

On `/add_tag <name> [--color #hex] [--task <target>]`:

1. `uv run python -m tool_scripts.clickup_api.tags add <name> --color <hex>`
2. If `--task <target>`: fuzzy-resolve then `tags attach <task_id> <name>`.

Reply:
- No `--task`: `🏷 Tag '<name>' 已建立`
- With `--task`: `🏷 Tag '<name>' 已建立並附加到 "<task name>"`
