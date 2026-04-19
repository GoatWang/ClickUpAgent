---
description: 將任務移到 pending（等 review/merge/外部）
---

On `/pending <target> [--reason text]`:

Same fuzzy-resolve + confirm flow as `/done`. On apply:
- `uv run python -m tool_scripts.clickup_api.tasks update <task_id> --status pending`
- If `--reason` given: `uv run python -m tool_scripts.clickup_api.tasks comment <task_id> "<reason>"`

Reply: `⏳ Pending：<url>`
