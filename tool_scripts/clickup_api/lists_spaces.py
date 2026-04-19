"""Workspace/Space/Folder/List discovery + find-or-create helpers.

Also provides a CLI:
    uv run python -m tool_scripts.clickup_api.lists_spaces teams
    uv run python -m tool_scripts.clickup_api.lists_spaces spaces --team 90182630024
    uv run python -m tool_scripts.clickup_api.lists_spaces folders --space 901810675992
    uv run python -m tool_scripts.clickup_api.lists_spaces lists --space 901810675992
    uv run python -m tool_scripts.clickup_api.lists_spaces get-list --list 901817481142
"""

from __future__ import annotations

import json
from typing import Any

import typer

from .client import ClickUpClient, load_config

app = typer.Typer(no_args_is_help=True, add_completion=False)


def list_teams(client: ClickUpClient) -> list[dict[str, Any]]:
    return client.get("/team")["teams"]


def list_spaces(client: ClickUpClient, team_id: str, archived: bool = False) -> list[dict[str, Any]]:
    return client.get(f"/team/{team_id}/space", archived=str(archived).lower())["spaces"]


def list_folders(client: ClickUpClient, space_id: str, archived: bool = False) -> list[dict[str, Any]]:
    return client.get(f"/space/{space_id}/folder", archived=str(archived).lower())["folders"]


def list_folderless_lists(client: ClickUpClient, space_id: str, archived: bool = False) -> list[dict[str, Any]]:
    return client.get(f"/space/{space_id}/list", archived=str(archived).lower())["lists"]


def list_lists_in_folder(client: ClickUpClient, folder_id: str, archived: bool = False) -> list[dict[str, Any]]:
    return client.get(f"/folder/{folder_id}/list", archived=str(archived).lower())["lists"]


def get_list(client: ClickUpClient, list_id: str) -> dict[str, Any]:
    return client.get(f"/list/{list_id}")


def get_space(client: ClickUpClient, space_id: str) -> dict[str, Any]:
    return client.get(f"/space/{space_id}")


def find_space_by_name(client: ClickUpClient, team_id: str, name: str) -> dict[str, Any] | None:
    for s in list_spaces(client, team_id):
        if s["name"] == name:
            return s
    return None


def find_folderless_list_by_name(client: ClickUpClient, space_id: str, name: str) -> dict[str, Any] | None:
    for l in list_folderless_lists(client, space_id):
        if l["name"] == name:
            return l
    return None


def create_space(client: ClickUpClient, team_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return client.post(f"/team/{team_id}/space", body)


def create_folderless_list(client: ClickUpClient, space_id: str, name: str) -> dict[str, Any]:
    return client.post(f"/space/{space_id}/list", {"name": name})


@app.command()
def teams() -> None:
    """List workspaces (teams)."""
    with ClickUpClient() as c:
        rows = [{"id": t["id"], "name": t["name"]} for t in list_teams(c)]
    typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@app.command()
def spaces(team: str | None = typer.Option(None, help="team_id; defaults to config.clickup.team_id")) -> None:
    """List spaces in a workspace."""
    cfg = load_config()
    team_id = team or cfg["clickup"]["team_id"]
    with ClickUpClient() as c:
        rows = [
            {"id": s["id"], "name": s["name"], "private": s["private"]}
            for s in list_spaces(c, team_id)
        ]
    typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@app.command()
def folders(space: str = typer.Option(..., help="space_id")) -> None:
    """List folders in a space."""
    with ClickUpClient() as c:
        rows = [{"id": f["id"], "name": f["name"]} for f in list_folders(c, space)]
    typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@app.command()
def lists(
    space: str = typer.Option(..., help="space_id"),
    folder: str | None = typer.Option(None, help="folder_id; if omitted, list folderless lists"),
) -> None:
    """List lists (folderless by default, or inside a folder)."""
    with ClickUpClient() as c:
        items = list_lists_in_folder(c, folder) if folder else list_folderless_lists(c, space)
        rows = [{"id": l["id"], "name": l["name"], "task_count": l.get("task_count")} for l in items]
    typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@app.command("get-list")
def get_list_cmd(list_id: str = typer.Option(..., "--list")) -> None:
    """Show a single list with its statuses."""
    with ClickUpClient() as c:
        l = get_list(c, list_id)
    typer.echo(json.dumps(
        {
            "id": l["id"],
            "name": l["name"],
            "statuses": [x["status"] for x in l.get("statuses", [])],
            "task_count": l.get("task_count"),
        },
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    app()
