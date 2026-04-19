---
description: 將任務移到 in progress 狀態（AI era 裡比較少用）
---

On `/to_progress <target>`:

Same fuzzy-resolve + confirm flow as `/done`, then:
`uv run python -m tool_scripts.clickup_api.tasks update <task_id> --status "in progress"`

Reply: `🔵 進行中：<url>`
