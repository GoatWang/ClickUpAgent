# ClickUpAgent — Claude instructions

## 專案概述

ClickUp agent driven through [claude-telegram-bot (ctb)](../claude-telegram-bot). Wraps the ClickUp v2 REST API to add/update/close tasks, attach images, manage tags, and publish kanban HTML reports. Primary target project: **Oysterun**.

**Launch:** `ctb /Users/wanghsuanchung/Projects/ClickUpAgent`

## 核心原則

1. **Fail-fast** — no over-protective try/except. Let errors propagate with clear messages.
2. **Direct dict access** — `dict["key"]` by default; `.get()` only for truly optional fields.
3. **Never delete without explicit confirmation** — destructive operations require a confirm card and `y`.
4. **No over-engineering** — only build what's needed now.
5. **Every mutation is confirmed** — even on exact-id match, show a one-line confirm card before mutating. See §Fuzzy resolve + confirm.

## 語言慣例

- **Code & docs**: English
- **Telegram replies**: 繁體中文 (Traditional Chinese)
- **Command descriptions**: 繁體中文 (shown in `/help` + Telegram hints)

## Python 執行模式

All tool_scripts run via uv:
```bash
cd /Users/wanghsuanchung/Projects/ClickUpAgent
uv run python -m tool_scripts.<module>.<submodule> [args]
```

Entry points are Python `-m` modules (not bare paths) because tool_scripts is a package.

## 專案結構

```
ClickUpAgent/
├── CLAUDE.md                         # this file
├── config.json                       # secrets (gitignored); see config.json.template
├── pyproject.toml                    # uv-managed deps
├── .claude/
│   ├── commands/                     # 20 slash commands (dynamic /help scans this)
│   └── skills/                       # (optional) domain skills
├── tool_scripts/
│   ├── clickup_api/
│   │   ├── client.py                 # httpx wrapper; token from config.json
│   │   ├── lists_spaces.py           # teams / spaces / folders / lists discovery
│   │   ├── tasks.py                  # task CRUD + status + priority + comments
│   │   ├── tags.py                   # space-level tag ops + attach/detach
│   │   ├── attachments.py            # multipart upload to task
│   │   └── custom_fields.py          # field probe + set value; CAN'T CREATE in v2
│   ├── scaffold/
│   │   ├── scaffold.py               # idempotent reconcile of spec → ClickUp
│   │   └── specs/oysterun.yaml       # Oysterun Space/Lists/tags/fields spec
│   ├── resolve/fuzzy_target.py       # id / fuzzy-name target resolution
│   └── help_scan/list_commands.py    # dynamic /help scanner
├── data/
│   ├── oysterun_ids.json             # cached space_id / list_id / custom_field_id map
│   └── focus.json                    # current focused task (per chat, optional)
└── uploads/                          # incoming Telegram photos staged here (gitignored)
```

## Oysterun ClickUp 結構（Option Z — folderless）

```
Workspace: Oysterun Workspace (team_id = 90182630024)
└── Space: Oysterun (id = 901810679491)
    ├── Backend (Cloud)
    ├── Host Service
    ├── Web Client
    ├── Phone App — Chat           ← 獨立 folder for chat 相關任務
    ├── Phone App (iOS) — General
    ├── Shared / Infra
    └── Cross-Cutting
```

Each List inherits the Space's 4 statuses: `todo → in progress → pending → done`.

## Status flow

| Status (exact API string) | When to use |
|---|---|
| `todo` | Default for new tasks |
| `in progress` | Actively working (AI-era: rare; most tasks go straight to `done`) |
| `pending` | Waiting on external (PR review, merge, user input) |
| `done` | Completed |

Shortcut commands: `/done` (most common), `/to_progress`, `/pending`.
For retroactive logging use `/add_done` (creates a task already at `done`).

**Note on naming:** ClickUp's Board view column headers render uppercase (TODO, IN PROGRESS, PENDING, DONE) but the stored/API names are lowercase. Every `tasks update --status X` or `tasks create --status X` call must use the exact stored string, otherwise the API returns `400 Status does not exist` (verified).

## Priority

Native ClickUp field (NOT tags). Set via `-p0..-p3` flag on `/add_task`:

| Flag | ClickUp priority | Label |
|---|---|---|
| `-p0` | 1 | Urgent |
| `-p1` | 2 | High |
| *(default)* `-p2` | 3 | Normal |
| `-p3` | 4 | Low |

## Tags

Tags are Space-scoped. 58 seeded tags covering module identity + cross-cutting themes. See `tool_scripts/scaffold/specs/oysterun.yaml` for the full vocabulary.

On `/add_task`:
- `--tags a,b,c` → exact tags (auto-created in Space if missing)
- `--notags` → empty
- *(default)* → **auto-infer** 1–3 most compatible tags from the description. Always show them in the confirm card.

## PR linking

`PR` is a Space-level custom field (type `url`). Set via:
- `/add_task … --pr https://github.com/…`
- `/done <target> --pr https://github.com/…`
- `/set_pr <target> <url>`

On the `/kanban` card, a 🔗 PR chip appears for tasks with a PR set (clickable via ClickUp).

## Fuzzy resolve + confirm

Every command that takes `<target>` runs this resolution through `tool_scripts.resolve.fuzzy_target`:

1. Looks like a task id (e.g. `86ex9z9hm` or `PROJ-123`) → fetch directly
2. Fuzzy name match with rapidfuzz across all Oysterun List tasks:
   - 1 strong match (score ≥ 85) → single match
   - Multi strong → list numbered candidates, user picks
   - Weak (60 ≤ score < 85) → "did you mean…?" suggestions
   - None → abort with closest 3

Every mutation command (even on exact id) prints a confirm card:
```
🔍 Found: "<name>"  (<list>, <status>)
  tags: <…>
About to: status → done
Reply y to proceed.
```

Override: `--yes` skips confirmation (scripting only).

## `/kanban` 產生規範

Text-only Telegram message grouping tasks by status. No HTML, no web server.

1. Resolve target List (or `--all`)
2. `uv run python -m tool_scripts.clickup_api.tasks list --list-id <id>` per list
3. Group client-side by status in order: `todo → in progress → pending → done`
4. Render text blocks per §`/kanban` command (`.claude/commands/kanban.md`)
5. Reply directly in Telegram under 4096 chars; split across messages if `--all` overflows

For a live board with thumbnails + per-card edits, open ClickUp's native Board view directly. Enable "Customize cards → Cover image" once per List to see attachment thumbnails on cards there.

## Scaffold (`/init_oysterun`)

Idempotent. Never deletes. Operates from `tool_scripts/scaffold/specs/oysterun.yaml`.

```bash
uv run python -m tool_scripts.scaffold.scaffold            # dry-run + prompt
uv run python -m tool_scripts.scaffold.scaffold --apply    # dry-run + auto-apply
uv run python -m tool_scripts.scaffold.scaffold --check    # dry-run only
```

**v2 API limitations the scaffold cannot overcome** — these need one-time UI setup:
- **Custom Space statuses** cannot be created via API. Configure in ClickUp UI → Space settings → Statuses.
- **Custom fields** cannot be created via API. Configure in ClickUp UI → Space settings → Custom Fields, then re-run scaffold with `--check` to cache IDs into `data/oysterun_ids.json`.

Scaffold reports `! STATUSES MISSING` / `! MISSING custom field` when these are needed.

## Rate limits

ClickUp 100 req/min on Free/Unlimited. `client.py` handles 429 with `X-RateLimit-Reset`-aware backoff. Parallelize carefully; a whole-workspace kanban (`/kanban --all`) fans out ~100 calls — budget-tight.

## 工具路徑表

| Tool | Entry | Purpose |
|---|---|---|
| ClickUp client | `tool_scripts.clickup_api.client` | httpx wrapper + rate-limit |
| Discovery | `tool_scripts.clickup_api.lists_spaces` | teams / spaces / folders / lists |
| Tasks | `tool_scripts.clickup_api.tasks` | CRUD + comment |
| Tags | `tool_scripts.clickup_api.tags` | space tags + attach/detach |
| Attachments | `tool_scripts.clickup_api.attachments` | multipart upload |
| Custom fields | `tool_scripts.clickup_api.custom_fields` | set value + refresh-map |
| Scaffold | `tool_scripts.scaffold.scaffold` | reconcile spec → ClickUp |
| Fuzzy resolver | `tool_scripts.resolve.fuzzy_target` | id or fuzzy-name → task |
| Help scanner | `tool_scripts.help_scan.list_commands` | dynamic /help |

## Known limitations (as of 2026-04-18)

- v2 API cannot create/update: Space statuses, custom fields, task cover image. All three managed via UI.
- `GET /list/{id}/task` omits attachments + custom field values. For detailed views fetch each task with `tool_scripts.clickup_api.tasks get` (costs 1 extra API call per task).
- Tag name match is exact. `auth` and `Auth` are different tags; be consistent.
- macOS screenshot filenames contain U+202F (narrow no-break space); curl `-F` fails on these. `attachments.py` uses httpx which handles them correctly.
