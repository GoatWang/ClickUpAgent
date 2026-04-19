---
description: 顯示指定 List 的看板進度（Telegram 文字訊息，分狀態分組）
---

On `/kanban [--list X] [--all]`:

Produce a **text-based** kanban summary sent directly in Telegram. No HTML, no URL, no web server.

### Step 1 — resolve list(s)

- `--all` → iterate all 7 Lists in `data/oysterun_ids.json`
- `--list X` → resolve by fuzzy name against the 7 Lists
- omitted → reply with the numbered 1–7 menu (same as `/add_task`); wait for the user's pick

### Step 2 — fetch tasks

For each target list:
`uv run python -m tool_scripts.clickup_api.tasks list --list-id <id>`

### Step 3 — group + render

Group tasks by status in the order: `todo → in progress → pending → done`. Render each List as a code block:

```
📊 Backend (Cloud) (n open / m total)

⭕ todo (3)
  • Fix device-link token expires too fast       p1  #auth #bug #devices
  • Add 2fa for admin panel                      p2  #auth #security
  • Migrate password hashing to Argon2id         p2  #crypto #tech-debt

🔵 in progress (1)
  • Rework device heartbeat retry policy         p1  #devices #reliability

⏳ pending (0)
  — empty —

✅ done (5)                                     (latest 3 shown)
  • Rotate service-account tokens
  • Fix email template escaping
  • ...
```

Rules:
- Show **all** open tasks (todo / in progress / pending) — truncate with `… +N more` if >10 per column
- For `done`: only show the **3 most recent** by `date_updated` (older done tasks clutter the message)
- Status emoji: ⭕ todo · 🔵 in progress · ⏳ pending · ✅ done
- Priority pill: `p0`/`p1`/`p2`/`p3` (red/orange/yellow/gray in Telegram monospace — just the text label)
- Tags: `#tag-name` comma-joined

Keep the whole message under Telegram's 4096-char limit. If `--all` would overflow, split per List across multiple messages.

### Step 4 — header totals

First line of the message for any single list:
```
📊 <List name> (n open / m total)
```

For `--all`, begin with a combined one-liner:
```
📊 Oysterun 看板 (todo:N / in-prog:N / pending:N / done:N 之中最近 3 筆)
```
then one block per List.
