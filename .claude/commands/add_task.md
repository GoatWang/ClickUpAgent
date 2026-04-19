---
description: 新增任務到指定 List（list 必填，可帶 --tags/--notags/-p0..-p3/--pr）
---

On `/add_task <description> [--list X] [--tags a,b] [--notags] [-p0..-p3] [--pr URL]`:

### Step 1 — resolve list (REQUIRED)

If `--list` is missing, reply in Telegram with the 7 Oysterun Lists from `data/oysterun_ids.json`:
```
Which list?
  1. Backend (Cloud)
  2. Host Service
  3. Web Client
  4. Phone App — Chat
  5. Phone App (iOS) — General
  6. Shared / Infra
  7. Cross-Cutting
Reply 1–7.
```
Wait for the user's reply. No fallback / no default.

If `--list` is a fuzzy name, match case-insensitively against the keys in `oysterun_ids.json > list_id_by_name`. Ambiguous → same 1–7 prompt.

### Step 2 — tags

- `--tags a,b,c` → use exactly these
- `--notags` → empty tags list
- neither flag → **auto-infer**: read the task description, pick the 1–3 most compatible tags from the Space's tag list (loaded from `data/oysterun_ids.json` or `uv run python -m tool_scripts.clickup_api.tags list`). Prefer module tags relevant to the chosen List + any obvious cross-cutting tags (`bug`, `feature`, `security`, etc.). Show your picks in the confirm card (step 4).

Before attaching, ensure every tag exists in the Space:
`uv run python -m tool_scripts.clickup_api.tags ensure "a,b,c"`

### Step 3 — priority

`-p0 / -p1 / -p2 / -p3` → ClickUp priority 1 / 2 / 3 / 4. Default `-p2` (Normal) if not given.

### Step 4 — confirm card (always)

Before creating, reply in Telegram:
```
🆕 Create in "<list name>":
  "<description>"
  tags:     <tag list, or "(none)">
  priority: p<0-3>
  PR:       <url, or "(none)">
Reply y to create.
```
Wait for `y`. Anything else = abort.

### Step 5 — create

`uv run python -m tool_scripts.clickup_api.tasks create --list-id <id> --name "<desc>" --tags "..." --priority <0-3>`

If `--pr URL` was given, chain:
`uv run python -m tool_scripts.clickup_api.custom_fields set <task_id> PR <url>`

Reply with the resulting ClickUp URL (short 繁中: `✅ 任務已新增：<url>`).

### Example

`/add_task 修 chat streaming 取消按鈕重複點會 crash --list "Phone App — Chat" -p1 --pr https://github.com/.../pull/812`
→ auto-infers tags `streaming, chat-ui, bug` → confirm → create.
