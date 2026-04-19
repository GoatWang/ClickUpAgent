---
description: 列出 Space 裡所有 tags（含使用次數）
---

On `/ls_tags`:

1. `uv run python -m tool_scripts.clickup_api.tags list` → get 58+ tag names.
2. Optionally: for a usage count, fan out `tasks list` and tally (expensive; skip unless user passes `--counts`).

Reply in a grouped list:
```
🏷 Tags (N):
[Backend] auth, devices, agents, users, onboarding, email, db, crypto
[Host] session, providers, ...
[Type] bug, feature, enhancement, tech-debt, ...
[Quality] security, performance, a11y, ...
[Workflow] needs-design, needs-repro, ...
```

Group by matching the tag name against the Space tag seed groupings in `tool_scripts/scaffold/specs/oysterun.yaml`.
