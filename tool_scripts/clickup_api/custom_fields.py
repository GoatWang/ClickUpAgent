"""Custom-field helpers.

v2 API note: fields CANNOT be created programmatically. They must be
added via the ClickUp UI, then this module queries + caches their IDs.

CLI:
    uv run python -m tool_scripts.clickup_api.custom_fields list --list-id X
    uv run python -m tool_scripts.clickup_api.custom_fields set <task_id> <field_name_or_id> <value>
    uv run python -m tool_scripts.clickup_api.custom_fields clear <task_id> <field_name_or_id>
    uv run python -m tool_scripts.clickup_api.custom_fields refresh-map
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from .client import ClickUpClient, load_config
from .lists_spaces import list_folderless_lists

app = typer.Typer(no_args_is_help=True, add_completion=False)

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_list_fields(client: ClickUpClient, list_id: str) -> list[dict[str, Any]]:
    return client.get(f"/list/{list_id}/field").get("fields", [])


def set_custom_field(
    client: ClickUpClient,
    task_id: str,
    field_id: str,
    value: Any,
) -> None:
    client.post(f"/task/{task_id}/field/{field_id}", {"value": value})


def clear_custom_field(client: ClickUpClient, task_id: str, field_id: str) -> None:
    client.delete(f"/task/{task_id}/field/{field_id}")


def load_id_map() -> dict[str, Any]:
    cfg = load_config()
    p = Path(cfg["clickup"]["id_map_path"])
    if not p.is_absolute():
        p = REPO_ROOT / p
    return json.loads(p.read_text())


def save_id_map(m: dict[str, Any]) -> None:
    cfg = load_config()
    p = Path(cfg["clickup"]["id_map_path"])
    if not p.is_absolute():
        p = REPO_ROOT / p
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False))


def resolve_field_id(name_or_id: str) -> str:
    m = load_id_map()
    by_name = m.get("custom_field_id_by_name", {})
    if name_or_id in by_name:
        return by_name[name_or_id]
    # if it looks like a UUID, pass through
    return name_or_id


# ---------- CLI ----------

@app.command("list")
def list_cmd(list_id: str = typer.Option(..., "--list-id")) -> None:
    with ClickUpClient() as c:
        fields = get_list_fields(c, list_id)
    rows = [
        {"id": f["id"], "name": f["name"], "type": f["type"]}
        for f in fields
    ]
    typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@app.command()
def set(task_id: str, field: str, value: str) -> None:
    fid = resolve_field_id(field)
    with ClickUpClient() as c:
        set_custom_field(c, task_id, fid, value)
    typer.echo(f"set {field}={value!r} on {task_id}")


@app.command()
def clear(task_id: str, field: str) -> None:
    fid = resolve_field_id(field)
    with ClickUpClient() as c:
        clear_custom_field(c, task_id, fid)
    typer.echo(f"cleared {field} on {task_id}")


@app.command("refresh-map")
def refresh_map() -> None:
    """Probe fields visible on the first list and cache field ids into oysterun_ids.json."""
    m = load_id_map()
    list_ids = list(m["list_id_by_name"].values())
    if not list_ids:
        typer.echo("No lists cached. Run scaffold first.")
        raise typer.Exit(1)
    with ClickUpClient() as c:
        fields = get_list_fields(c, list_ids[0])
    m["custom_field_id_by_name"] = {f["name"]: f["id"] for f in fields}
    save_id_map(m)
    typer.echo(json.dumps(m["custom_field_id_by_name"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
