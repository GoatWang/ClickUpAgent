"""Task CRUD + status + priority helpers.

CLI:
    uv run python -m tool_scripts.clickup_api.tasks list --list-id 901817486454
    uv run python -m tool_scripts.clickup_api.tasks get <task_id>
    uv run python -m tool_scripts.clickup_api.tasks create --list-id X --name "..." [--status done] [--priority 2] [--tags a,b]
    uv run python -m tool_scripts.clickup_api.tasks update <task_id> --status done
    uv run python -m tool_scripts.clickup_api.tasks delete <task_id>
    uv run python -m tool_scripts.clickup_api.tasks comment <task_id> "text"
"""

from __future__ import annotations

import json
from typing import Any

import typer

from .client import ClickUpClient

app = typer.Typer(no_args_is_help=True, add_completion=False)


# Priority shorthand: user-facing p0..p3  →  ClickUp priority 1..4 (Urgent..Low)
PRIORITY_MAP = {0: 1, 1: 2, 2: 3, 3: 4}
DEFAULT_PRIORITY = 2  # p2 = Normal


def create_task(
    client: ClickUpClient,
    list_id: str,
    name: str,
    *,
    description: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    priority: int | None = None,
    assignees: list[int] | None = None,
    due_date_ms: int | None = None,
    parent_task_id: str | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name}
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = status
    if tags is not None:
        body["tags"] = tags
    if priority is not None:
        body["priority"] = PRIORITY_MAP[priority]
    if assignees:
        body["assignees"] = assignees
    if due_date_ms is not None:
        body["due_date"] = due_date_ms
        body["due_date_time"] = True
    if parent_task_id:
        body["parent"] = parent_task_id
    if custom_fields:
        body["custom_fields"] = custom_fields
    return client.post(f"/list/{list_id}/task", body)


def update_task(
    client: ClickUpClient,
    task_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    add_assignees: list[int] | None = None,
    rm_assignees: list[int] | None = None,
    due_date_ms: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = status
    if priority is not None:
        body["priority"] = PRIORITY_MAP[priority]
    if add_assignees or rm_assignees:
        body["assignees"] = {"add": add_assignees or [], "rem": rm_assignees or []}
    if due_date_ms is not None:
        body["due_date"] = due_date_ms
        body["due_date_time"] = True
    if not body:
        raise ValueError("update_task: no fields to update")
    return client.put(f"/task/{task_id}", body)


def get_task(client: ClickUpClient, task_id: str, include_subtasks: bool = True) -> dict[str, Any]:
    return client.get(f"/task/{task_id}", include_subtasks=str(include_subtasks).lower())


def delete_task(client: ClickUpClient, task_id: str) -> None:
    client.delete(f"/task/{task_id}")


def list_tasks(
    client: ClickUpClient,
    list_id: str,
    *,
    include_closed: bool = True,
    subtasks: bool = True,
    archived: bool = False,
    statuses: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    page = 0
    out: list[dict[str, Any]] = []
    while True:
        params: dict[str, Any] = {
            "archived": str(archived).lower(),
            "include_closed": str(include_closed).lower(),
            "subtasks": str(subtasks).lower(),
            "page": page,
        }
        if statuses:
            params["statuses[]"] = statuses
        if tags:
            params["tags[]"] = tags
        resp = client.get(f"/list/{list_id}/task", **params)
        batch = resp.get("tasks", [])
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def add_comment(client: ClickUpClient, task_id: str, text: str, notify_all: bool = False) -> dict[str, Any]:
    return client.post(
        f"/task/{task_id}/comment",
        {"comment_text": text, "notify_all": notify_all},
    )


# ---------- CLI ----------

@app.command("list")
def list_cmd(
    list_id: str = typer.Option(..., "--list-id"),
    status: list[str] = typer.Option([], "--status"),
    tag: list[str] = typer.Option([], "--tag"),
    closed: bool = typer.Option(True, "--closed/--no-closed"),
) -> None:
    with ClickUpClient() as c:
        tasks = list_tasks(
            c, list_id,
            include_closed=closed,
            statuses=status or None,
            tags=tag or None,
        )
    rows = [
        {
            "id": t["id"],
            "name": t["name"],
            "status": t["status"]["status"],
            "tags": [x["name"] for x in t.get("tags", [])],
            "priority": (t.get("priority") or {}).get("priority") if t.get("priority") else None,
            "url": t.get("url"),
        }
        for t in tasks
    ]
    typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))


@app.command()
def get(task_id: str) -> None:
    with ClickUpClient() as c:
        t = get_task(c, task_id)
    typer.echo(json.dumps(
        {
            "id": t["id"],
            "name": t["name"],
            "status": t["status"]["status"],
            "tags": [x["name"] for x in t.get("tags", [])],
            "description": t.get("description"),
            "url": t.get("url"),
        },
        indent=2, ensure_ascii=False,
    ))


@app.command()
def create(
    list_id: str = typer.Option(..., "--list-id"),
    name: str = typer.Option(..., "--name"),
    description: str | None = typer.Option(None, "--desc"),
    status: str | None = typer.Option(None, "--status"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated"),
    priority: int | None = typer.Option(None, "--priority", min=0, max=3),
) -> None:
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    with ClickUpClient() as c:
        t = create_task(
            c, list_id, name,
            description=description,
            status=status,
            tags=tag_list,
            priority=priority,
        )
    typer.echo(json.dumps({"id": t["id"], "url": t["url"], "status": t["status"]["status"]}, indent=2, ensure_ascii=False))


@app.command()
def update(
    task_id: str,
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--desc"),
    status: str | None = typer.Option(None, "--status"),
    priority: int | None = typer.Option(None, "--priority", min=0, max=3),
) -> None:
    with ClickUpClient() as c:
        t = update_task(c, task_id, name=name, description=description, status=status, priority=priority)
    typer.echo(json.dumps({"id": t["id"], "status": t["status"]["status"]}, indent=2, ensure_ascii=False))


@app.command()
def delete(task_id: str) -> None:
    with ClickUpClient() as c:
        delete_task(c, task_id)
    typer.echo(f"deleted {task_id}")


@app.command()
def comment(task_id: str, text: str) -> None:
    with ClickUpClient() as c:
        r = add_comment(c, task_id, text)
    typer.echo(json.dumps({"comment_id": r.get("id"), "hist_id": r.get("hist_id")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
