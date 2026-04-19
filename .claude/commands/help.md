---
description: 列出所有 ClickUp agent 可用指令（動態掃描）
---

On `/help`, do NOT produce a hardcoded list.

1. Run: `uv run python -m tool_scripts.help_scan.list_commands`
2. Parse the output (one `/command  description` per line).
3. Reply in Telegram in this format (繁中):

```
可用指令：
/command1 — 描述
/command2 — 描述
...

需要更多細節？直接打 /command 試試看，若參數不齊會提示你。
```

Exclude any Claude Code built-ins (`/clear`, `/compact`, `/help` itself from Claude Code, etc.) — the scanner only sees `.claude/commands/*.md`, so that's already handled. Never hardcode the list.
