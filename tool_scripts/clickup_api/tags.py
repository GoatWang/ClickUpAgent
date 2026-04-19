"""Tag operations at Space level + per-task add/remove.

Tags must exist in the Space before they can be attached to a task;
create_if_missing() covers that in one call.

CLI:
    uv run python -m tool_scripts.clickup_api.tags list --space-id X
    uv run python -m tool_scripts.clickup_api.tags add <tag_name> [--space-id X] [--color #hex]
    uv run python -m tool_scripts.clickup_api.tags attach <task_id> <tag_name>
    uv run python -m tool_scripts.clickup_api.tags detach <task_id> <tag_name>
    uv run python -m tool_scripts.clickup_api.tags ensure <space_id> <tag1,tag2,...>
"""

from __future__ import annotations

import json
from typing import Any

import typer

from .client import ClickUpClient, load_config
from pathlib import Path

app = typer.Typer(no_args_is_help=True, add_completion=False)


def list_space_tags(client: ClickUpClient, space_id: str) -> list[dict[str, Any]]:
    return client.get(f"/space/{space_id}/tag").get("tags", [])


def create_space_tag(
    client: ClickUpClient,
    space_id: str,
    name: str,
    tag_fg: str | None = None,
    tag_bg: str | None = None,
) -> None:
    tag: dict[str, Any] = {"name": name}
    if tag_fg:
        tag["tag_fg"] = tag_fg
    if tag_bg:
        tag["tag_bg"] = tag_bg
    client.post(f"/space/{space_id}/tag", {"tag": tag})


def delete_space_tag(client: ClickUpClient, space_id: str, name: str) -> None:
    client.delete(f"/space/{space_id}/tag/{name}")


def attach_tag(client: ClickUpClient, task_id: str, name: str) -> None:
    client.post(f"/task/{task_id}/tag/{name}")


def detach_tag(client: ClickUpClient, task_id: str, name: str) -> None:
    client.delete(f"/task/{task_id}/tag/{name}")


def ensure_tags_exist(
    client: ClickUpClient,
    space_id: str,
    names: list[str],
) -> list[str]:
    """Make sure every tag in `names` exists in the Space. Returns list of names that were newly created."""
    existing = {t["name"] for t in list_space_tags(client, space_id)}
    created: list[str] = []
    for n in names:
        if n not in existing:
            create_space_tag(client, space_id, n)
            created.append(n)
    return created


# ---------- CLI ----------

def _default_space_id() -> str:
    cfg = load_config()
    id_map_path = Path(cfg["clickup"]["id_map_path"])
    if not id_map_path.is_absolute():
        id_map_path = Path(__file__).resolve().parents[2] / id_map_path
    id_map = json.loads(id_map_path.read_text())
    return id_map["space_id"]


@app.command("list")
def list_cmd(space_id: str | None = typer.Option(None, "--space-id")) -> None:
    sid = space_id or _default_space_id()
    with ClickUpClient() as c:
        tags = list_space_tags(c, sid)
    rows = [
        {"name": t["name"], "fg": t.get("tag_fg"), "bg": t.get("tag_bg")}
        for t in tags
    ]
    typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@app.command()
def add(
    name: str,
    space_id: str | None = typer.Option(None, "--space-id"),
    color: str | None = typer.Option(None, "--color", help="Hex, e.g. #e53935"),
) -> None:
    sid = space_id or _default_space_id()
    with ClickUpClient() as c:
        create_space_tag(c, sid, name, color, color)
    typer.echo(f"created tag '{name}' in space {sid}")


@app.command()
def attach(task_id: str, name: str) -> None:
    with ClickUpClient() as c:
        attach_tag(c, task_id, name)
    typer.echo(f"attached '{name}' to {task_id}")


@app.command()
def detach(task_id: str, name: str) -> None:
    with ClickUpClient() as c:
        detach_tag(c, task_id, name)
    typer.echo(f"detached '{name}' from {task_id}")


@app.command()
def ensure(
    names: str,
    space_id: str | None = typer.Option(None, "--space-id"),
) -> None:
    sid = space_id or _default_space_id()
    tag_list = [n.strip() for n in names.split(",") if n.strip()]
    with ClickUpClient() as c:
        created = ensure_tags_exist(c, sid, tag_list)
    typer.echo(json.dumps({"checked": tag_list, "created": created}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
