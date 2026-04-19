"""Scan .claude/commands/*.md and return a fresh list of agent commands.

Used by the /help command to produce a dynamic reply — never hardcoded.

Format of each .md file (frontmatter is YAML):

    ---
    description: "One-line description shown in /help"
    ---
    <body: instructions for Claude>

CLI:
    uv run python -m tool_scripts.help_scan.list_commands           # table output
    uv run python -m tool_scripts.help_scan.list_commands --json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
import yaml

app = typer.Typer(no_args_is_help=False, add_completion=False)

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    raw = text[3:end].strip()
    try:
        parsed = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def scan(commands_dir: Path = COMMANDS_DIR) -> list[dict[str, str]]:
    if not commands_dir.is_dir():
        return []
    out: list[dict[str, str]] = []
    for md in sorted(commands_dir.glob("*.md")):
        meta = parse_frontmatter(md.read_text())
        out.append(
            {
                "name": "/" + md.stem,
                "description": str(meta.get("description", "")).strip(),
                "path": str(md.relative_to(REPO_ROOT)),
            }
        )
    return out


@app.command()
def main(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    rows = scan()
    if json_out:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        typer.echo("(no commands found in .claude/commands/)")
        return
    width = max(len(r["name"]) for r in rows)
    for r in rows:
        desc = r["description"] or "(no description)"
        typer.echo(f"  {r['name']:<{width}}  {desc}")


if __name__ == "__main__":
    app()
