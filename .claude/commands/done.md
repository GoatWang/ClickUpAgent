---
description: 將任務移到 done 狀態（可同時設定 --pr）
---

On `/done <target> [--pr URL]`:

### Step 1 — resolve target
`uv run python -m tool_scripts.resolve.fuzzy_target "<target>"`

Handle the `kind`:
- `exact` → **skip confirm** and apply immediately (user already gave an unambiguous id). Jump to Step 3.
- `single-fuzzy` → show confirm card with the single candidate
- `multi` → list candidates numbered, user replies with index
- `typo` → "你是指這個嗎? …" + top matches, user confirms
- `none` → abort with "找不到符合的任務"

### Step 2 — confirm (skipped when `kind == exact`)

```
🔍 Found: "<name>"  (<list>, <current status>)
  tags: <…>
About to: status → done
<+ if --pr: set PR field → <url>>
Reply y to proceed.
```

### Step 3 — apply
- `uv run python -m tool_scripts.clickup_api.tasks update <task_id> --status done`
- If `--pr`: `uv run python -m tool_scripts.clickup_api.custom_fields set <task_id> PR <url>`

Reply: `✅ 已完成：<url>` (short).
