---
description: 初始化或同步 Oysterun ClickUp 工作區結構（idempotent）
---

On `/init_oysterun [--apply] [--check]`:

- Default → dry-run: `uv run python -m tool_scripts.scaffold.scaffold`
  Scaffold prints the full plan and prompts `y` at the shell. In Telegram, show the plan output verbatim (in a code block), tell the user to reply `y` to apply, then on `y` run `--apply`.
- `--apply` → `uv run python -m tool_scripts.scaffold.scaffold --apply`
- `--check` → `uv run python -m tool_scripts.scaffold.scaffold --check`

Behavior:
- Additive only — scaffold never deletes anything.
- New Lists/tags appear on apply; removed items from YAML produce a `! PRESENT IN CLICKUP, NOT IN SPEC` warning and stay in ClickUp.
- Custom fields can't be created via v2 API — if any are missing, instruct the user to create them via ClickUp UI (Space settings → Custom Fields), then re-run so the field id gets cached into `data/oysterun_ids.json`.

Reply in 繁中 with a one-line summary plus the Telegram code block of the plan.
