---
description: 更新任務的名稱/描述/狀態/tags/priority/PR
---

On `/update_task <target> [--name …] [--desc …] [--status …] [--add-tags a,b] [--rm-tags c] [--priority 0-3] [--pr URL]`:

### Step 1 — resolve target (fuzzy)
Same as `/done` — use `tool_scripts.resolve.fuzzy_target`. Confirm card shows the *diff*:

```
🔧 Update "<name>" (<list>):
  status:   to do → in progress       (if changed)
  +tags:    streaming, bug             (if any)
  -tags:    wip                        (if any)
  priority: p2 → p1                    (if changed)
  PR:       <url>                      (if changed)
Reply y.
```

### Step 2 — apply
- Status / name / desc / priority: `tasks update <id> --status … --name … …`
- Tag add: for each name, `uv run python -m tool_scripts.clickup_api.tags attach <id> <name>` (ensure exists first via `tags ensure`)
- Tag remove: `tags detach <id> <name>`
- PR: `custom_fields set <id> PR <url>`

Reply: short summary of what changed + task URL.
