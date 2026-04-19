---
description: 顯示工作區 → Space → List 結構
---

On `/spaces`:

1. `uv run python -m tool_scripts.clickup_api.lists_spaces teams`
2. For each team, `uv run python -m tool_scripts.clickup_api.lists_spaces spaces --team <id>`
3. For each Space, `uv run python -m tool_scripts.clickup_api.lists_spaces lists --space <id>` (folderless Lists)

Reply in Telegram in a compact nested tree:

```
Oysterun Workspace (90182630024)
├── Team Space
└── Oysterun
    ├── Backend (Cloud)        (n tasks)
    ├── Host Service           (n tasks)
    ├── Web Client             (n tasks)
    ├── Phone App — Chat       (n tasks)
    ├── Phone App (iOS) — General
    ├── Shared / Infra
    └── Cross-Cutting
```
