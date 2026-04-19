---
description: 設定目前聚焦的任務（後續 /attach /comment 會預設作用在這個任務）
---

On `/focus <target>` (or `/focus --clear`):

### Set
1. Fuzzy-resolve target.
2. Confirm card: `Focus on "<name>" ?` → `y`.
3. Write `{"task_id": "...", "name": "...", "set_at": <epoch>}` to `data/focus.json`.

### Clear
`/focus --clear` → delete `data/focus.json`.

### Show
`/focus` with no arg → read `data/focus.json` and reply with current focus (or "no focus set").

Other commands (`/attach`, `/comment`, `/done`, etc.) may fall back to the focus task id when no `<target>` is given.
