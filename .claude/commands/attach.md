---
description: 把最近收到的 Telegram 照片/檔案附加到任務
---

On `/attach <target>`:

The ctb host writes incoming Telegram media into `uploads/<timestamp>_<hash>.<ext>`.
Find the **most recent** such file (by mtime) in `uploads/`.

1. If `uploads/` is empty or newest file is older than 10 minutes → abort with "找不到最近的照片，請先傳一張".
2. Fuzzy-resolve `<target>` (§5 flow).
3. Confirm card:
   ```
   📎 Attach <filename> (NKB) to "<task name>" ?
   Reply y.
   ```
4. On `y`: `uv run python -m tool_scripts.clickup_api.attachments upload <task_id> <file_path>`
5. Reply with the thumbnail URL from the response: `✅ 已附加：<thumbnail_medium_url>`
