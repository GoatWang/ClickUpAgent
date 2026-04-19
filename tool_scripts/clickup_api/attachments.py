"""Task attachment upload (multipart).

Known gotchas (verified live):
- Field name must be `attachment`
- Filenames with U+202F (macOS screenshot narrow-no-break space) break curl `-F`;
  the httpx-based implementation here handles arbitrary unicode filenames correctly.

CLI:
    uv run python -m tool_scripts.clickup_api.attachments upload <task_id> /path/to/file
"""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

import typer

from .client import ClickUpClient

app = typer.Typer(no_args_is_help=True, add_completion=False)


def upload_attachment(client: ClickUpClient, task_id: str, file_path: Path) -> dict[str, Any]:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    mime, _ = mimetypes.guess_type(path.name)
    with path.open("rb") as fh:
        files = {"attachment": (path.name, fh.read(), mime or "application/octet-stream")}
    return client.post_multipart(f"/task/{task_id}/attachment", files=files)


@app.command()
def upload(
    task_id: str = typer.Argument(..., help="ClickUp task id, e.g. 86ex9z9hm"),
    file_path: Path = typer.Argument(..., help="Local file to upload"),
) -> None:
    with ClickUpClient() as c:
        r = upload_attachment(c, task_id, file_path)
    typer.echo(json.dumps(
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "url": r.get("url"),
            "thumbnail_medium": r.get("thumbnail_medium"),
            "width": r.get("width"),
            "height": r.get("height"),
        },
        indent=2, ensure_ascii=False,
    ))


if __name__ == "__main__":
    app()
