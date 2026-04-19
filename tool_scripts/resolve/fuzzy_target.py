"""Resolve a user-provided target (task id or fuzzy name) into a task dict,
producing candidates for the agent to confirm with the user.

Resolution order (per §5 of the final proposal):
  1. Looks like a ClickUp task id → fetch directly → return single exact match
  2. Fuzzy name match across all Lists in the Oysterun Space
     → 1 strong match above threshold → single match
     → multiple above threshold → multi-match
     → weak matches only → typo suggestion
     → nothing → no match

CLI:
    uv run python -m tool_scripts.resolve.fuzzy_target "fix device-link token"
    uv run python -m tool_scripts.resolve.fuzzy_target 86ex9z9hm
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rapidfuzz import fuzz, process

from tool_scripts.clickup_api.client import ClickUpClient, ClickUpError, load_config
from tool_scripts.clickup_api.tasks import get_task, list_tasks

REPO_ROOT = Path(__file__).resolve().parents[2]

# ClickUp task ids are alphanumeric, usually 7–10 chars (no dashes) — e.g. 86ex9z9hm.
# Custom task ids are like PROJ-123 (uppercase + digits, with dash).
TASK_ID_RE = re.compile(r"^[0-9a-z]{6,12}$")
CUSTOM_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,10}-\d+$")

STRONG_MATCH = 85
WEAK_MATCH = 60

app = typer.Typer(no_args_is_help=True, add_completion=False)


@dataclass
class Resolution:
    kind: str  # "exact", "single-fuzzy", "multi", "typo", "none"
    candidates: list[dict[str, Any]]
    query: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "query": self.query, "candidates": self.candidates}


def looks_like_task_id(s: str) -> bool:
    return bool(TASK_ID_RE.match(s) or CUSTOM_ID_RE.match(s))


def _load_space_id() -> str:
    cfg = load_config()
    p = Path(cfg["clickup"]["id_map_path"])
    if not p.is_absolute():
        p = REPO_ROOT / p
    return json.loads(p.read_text())["space_id"]


def _load_list_ids() -> dict[str, str]:
    cfg = load_config()
    p = Path(cfg["clickup"]["id_map_path"])
    if not p.is_absolute():
        p = REPO_ROOT / p
    return json.loads(p.read_text())["list_id_by_name"]


def _slim(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": t["id"],
        "name": t["name"],
        "status": t["status"]["status"],
        "list": t.get("list", {}).get("name"),
        "tags": [x["name"] for x in t.get("tags", [])],
        "url": t.get("url"),
    }


def _pool_all_open_tasks(client: ClickUpClient) -> list[dict[str, Any]]:
    # Fan out across every Oysterun list; subtasks=true so nested work is reachable.
    pool: list[dict[str, Any]] = []
    for _name, list_id in _load_list_ids().items():
        pool.extend(list_tasks(client, list_id, include_closed=False, subtasks=True))
    return pool


def resolve(client: ClickUpClient, target: str) -> Resolution:
    target = target.strip()

    if looks_like_task_id(target):
        try:
            t = get_task(client, target)
            return Resolution("exact", [_slim(t)], target)
        except ClickUpError:
            pass  # fall through to fuzzy

    pool = _pool_all_open_tasks(client)
    if not pool:
        return Resolution("none", [], target)

    # rapidfuzz process.extract returns (name, score, index)
    names = [t["name"] for t in pool]
    scored = process.extract(target, names, scorer=fuzz.WRatio, limit=5)

    strong = [(name, score, idx) for (name, score, idx) in scored if score >= STRONG_MATCH]
    if len(strong) == 1:
        return Resolution("single-fuzzy", [_slim(pool[strong[0][2]])], target)
    if len(strong) > 1:
        return Resolution("multi", [_slim(pool[idx]) for (_n, _s, idx) in strong], target)

    weak = [(name, score, idx) for (name, score, idx) in scored if score >= WEAK_MATCH]
    if weak:
        return Resolution("typo", [_slim(pool[idx]) for (_n, _s, idx) in weak[:3]], target)

    return Resolution("none", [], target)


@app.command()
def main(target: str) -> None:
    with ClickUpClient() as c:
        r = resolve(c, target)
    typer.echo(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
