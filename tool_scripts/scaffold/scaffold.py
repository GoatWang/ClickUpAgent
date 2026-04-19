"""Idempotent ClickUp workspace scaffolder.

Reads a YAML spec (default: specs/oysterun.yaml), diffs against the live
ClickUp workspace, prints a plan, and on --apply performs additive writes.
Never deletes or renames anything.

CLI:
    uv run python -m tool_scripts.scaffold.scaffold           # dry-run, prompts y/n
    uv run python -m tool_scripts.scaffold.scaffold --apply   # dry-run, then auto-apply
    uv run python -m tool_scripts.scaffold.scaffold --check   # dry-run only, exits
    uv run python -m tool_scripts.scaffold.scaffold --spec path.yaml
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
import yaml

from tool_scripts.clickup_api.client import ClickUpClient, load_config
from tool_scripts.clickup_api.lists_spaces import (
    create_folderless_list,
    create_space,
    find_folderless_list_by_name,
    find_space_by_name,
    list_folderless_lists,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = REPO_ROOT / "tool_scripts" / "scaffold" / "specs" / "oysterun.yaml"
ID_MAP_PATH = REPO_ROOT / "data" / "oysterun_ids.json"

RULE = "━" * 68

app = typer.Typer(no_args_is_help=False, add_completion=False)


# ---------- plan types ----------

@dataclass
class Plan:
    team_id: str
    space_name: str
    space_exists: bool
    space_id: str | None = None
    create_space_body: dict[str, Any] | None = None
    update_space_body: dict[str, Any] | None = None
    lists_create: list[str] = field(default_factory=list)
    lists_exists: list[str] = field(default_factory=list)
    lists_extra: list[str] = field(default_factory=list)  # in ClickUp, not in spec
    tags_create: list[dict[str, Any]] = field(default_factory=list)
    tags_exists: list[str] = field(default_factory=list)
    tags_extra: list[str] = field(default_factory=list)
    fields_create: list[dict[str, Any]] = field(default_factory=list)  # warn only (v2 API doesn't create fields)
    fields_exists: list[str] = field(default_factory=list)
    statuses_missing: list[str] = field(default_factory=list)  # warn only (v2 API doesn't create space statuses)
    statuses_exists: list[str] = field(default_factory=list)

    @property
    def total_creates(self) -> int:
        return (
            (1 if not self.space_exists else 0)
            + len(self.lists_create)
            + len(self.tags_create)
        )

    @property
    def api_call_budget(self) -> int:
        # rough estimate for dry-run display
        budget = 0
        if not self.space_exists:
            budget += 1  # create space
        if self.update_space_body:
            budget += 1  # put space for statuses/features
        budget += len(self.lists_create)
        budget += len(self.tags_create)
        return budget


# ---------- readers ----------

def load_spec(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def get_space_tags(client: ClickUpClient, space_id: str) -> list[dict[str, Any]]:
    return client.get(f"/space/{space_id}/tag").get("tags", [])


def get_list_fields(client: ClickUpClient, list_id: str) -> list[dict[str, Any]]:
    return client.get(f"/list/{list_id}/field").get("fields", [])


# ---------- plan computation ----------

def compute_plan(client: ClickUpClient, spec: dict[str, Any], team_id: str) -> Plan:
    space_name = spec["space"]["name"]
    existing_space = find_space_by_name(client, team_id, space_name)

    plan = Plan(
        team_id=team_id,
        space_name=space_name,
        space_exists=existing_space is not None,
        space_id=existing_space["id"] if existing_space else None,
    )

    # Space create body (if new) / update body for features (not statuses — see status section below)
    space_body: dict[str, Any] = {
        "name": space_name,
        "multiple_assignees": spec["space"].get("multiple_assignees", True),
        "features": spec["space"].get("features", {}),
    }

    if not existing_space:
        plan.create_space_body = space_body
    else:
        plan.update_space_body = space_body

    # Statuses — v2 API cannot create custom Space statuses; we probe and warn only.
    spec_statuses = [s["status"] for s in spec["space"].get("statuses", [])]
    if existing_space:
        existing_statuses = {s["status"] for s in existing_space.get("statuses", [])}
    else:
        existing_statuses = set()
    plan.statuses_missing = [s for s in spec_statuses if s not in existing_statuses]
    plan.statuses_exists = [s for s in spec_statuses if s in existing_statuses]

    # Lists
    spec_list_names = [l["name"] for l in spec.get("folderless_lists", [])]
    if existing_space:
        existing_lists = list_folderless_lists(client, existing_space["id"])
        existing_names = {l["name"] for l in existing_lists}
    else:
        existing_names = set()

    plan.lists_create = [n for n in spec_list_names if n not in existing_names]
    plan.lists_exists = [n for n in spec_list_names if n in existing_names]
    plan.lists_extra = sorted(existing_names - set(spec_list_names))

    # Tags
    spec_tags = spec.get("tags", [])
    spec_tag_names = [t["name"] for t in spec_tags]
    if existing_space:
        existing_tag_names = {t["name"] for t in get_space_tags(client, existing_space["id"])}
    else:
        existing_tag_names = set()

    plan.tags_create = [t for t in spec_tags if t["name"] not in existing_tag_names]
    plan.tags_exists = [n for n in spec_tag_names if n in existing_tag_names]
    plan.tags_extra = sorted(existing_tag_names - set(spec_tag_names))

    # Custom fields — v2 API cannot create these, so we only probe + warn
    spec_fields = spec["space"].get("custom_fields", [])
    spec_field_names = [f["name"] for f in spec_fields]
    existing_field_names: set[str] = set()
    if existing_space:
        lists_in_space = list_folderless_lists(client, existing_space["id"])
        if lists_in_space:
            fields = get_list_fields(client, lists_in_space[0]["id"])
            existing_field_names = {f["name"] for f in fields}

    plan.fields_create = [f for f in spec_fields if f["name"] not in existing_field_names]
    plan.fields_exists = [n for n in spec_field_names if n in existing_field_names]

    return plan


# ---------- plan rendering ----------

def render_plan(plan: Plan) -> str:
    lines: list[str] = []
    lines.append(RULE)
    lines.append(f"ClickUp Scaffold Plan — {plan.space_name}")
    lines.append(f"Workspace: team_id = {plan.team_id}")
    lines.append(RULE)
    lines.append("")

    lines.append("SPACE")
    if not plan.space_exists:
        lines.append(f'  + CREATE Space "{plan.space_name}"')
        if plan.create_space_body and plan.create_space_body.get("features"):
            enabled = [
                k for k, v in plan.create_space_body["features"].items()
                if isinstance(v, dict) and v.get("enabled")
            ]
            lines.append(f"      features:  {', '.join(enabled)}")
    else:
        lines.append(f'  = EXISTS Space "{plan.space_name}" (id={plan.space_id})')
        if plan.update_space_body:
            lines.append("      → will PUT to reconcile features")

    # Statuses (informational; v2 can't create)
    if plan.statuses_missing:
        lines.append(
            f'  ! STATUSES MISSING: {", ".join(plan.statuses_missing)} — '
            "configure in ClickUp UI (Space settings → Statuses); scaffold cannot create statuses in v2"
        )
    if plan.statuses_exists:
        lines.append(f'  = EXISTS statuses: {", ".join(plan.statuses_exists)}')

    # Custom fields (informational; v2 can't create)
    if plan.fields_create:
        for f in plan.fields_create:
            lines.append(
                f'  ! MISSING custom field "{f["name"]}" ({f["type"]}) — '
                "create via ClickUp UI (Space → Custom Fields); scaffold cannot create fields in v2"
            )
    for n in plan.fields_exists:
        lines.append(f'  = EXISTS custom field "{n}"')

    lines.append("")
    lines.append(f"LISTS ({len(plan.lists_create) + len(plan.lists_exists)} in spec)")
    for n in plan.lists_create:
        lines.append(f'  + CREATE list "{n}"')
    for n in plan.lists_exists:
        lines.append(f'  = EXISTS list "{n}"')
    for n in plan.lists_extra:
        lines.append(f'  ! PRESENT IN CLICKUP, NOT IN SPEC: "{n}" (will not delete)')

    lines.append("")
    total_tags = len(plan.tags_create) + len(plan.tags_exists)
    lines.append(f"TAGS ({total_tags} in spec)")
    if plan.tags_create:
        names = ", ".join(t["name"] for t in plan.tags_create)
        lines.append(f"  + CREATE {len(plan.tags_create)}: {names}")
    if plan.tags_exists:
        lines.append(f"  = EXISTS {len(plan.tags_exists)} tags")
    for n in plan.tags_extra:
        lines.append(f'  ! PRESENT IN CLICKUP, NOT IN SPEC: "{n}" (will not delete)')

    lines.append("")
    lines.append(RULE)
    lines.append("SUMMARY")
    parts = []
    if not plan.space_exists:
        parts.append("1 Space")
    if plan.update_space_body and plan.space_exists:
        parts.append("Space reconcile (statuses/features)")
    if plan.lists_create:
        parts.append(f"{len(plan.lists_create)} Lists")
    if plan.tags_create:
        parts.append(f"{len(plan.tags_create)} tags")
    lines.append("  Creates: " + (" · ".join(parts) if parts else "nothing"))
    lines.append("  Updates: 0   (except Space PUT for reconcile)")
    lines.append("  Deletes: 0   (scaffold never deletes)")
    lines.append("")
    lines.append(f"  API call budget: ≈{plan.api_call_budget} requests · rate-limit 100/min → safe")
    lines.append(RULE)

    return "\n".join(lines)


# ---------- apply ----------

def apply_plan(client: ClickUpClient, plan: Plan, spec: dict[str, Any]) -> dict[str, Any]:
    id_map: dict[str, Any] = {
        "team_id": plan.team_id,
        "space_id": None,
        "space_name": plan.space_name,
        "list_id_by_name": {},
        "custom_field_id_by_name": {},
        "tag_colors": {},
    }

    # 1. Create or locate space
    if not plan.space_exists:
        assert plan.create_space_body is not None
        typer.echo(f"  → POST /team/{plan.team_id}/space  (creating {plan.space_name})")
        created = create_space(client, plan.team_id, plan.create_space_body)
        space_id = created["id"]
        id_map["space_id"] = space_id
        time.sleep(0.3)
    else:
        space_id = plan.space_id
        id_map["space_id"] = space_id
        # PUT to reconcile statuses + features on existing space
        if plan.update_space_body:
            typer.echo(f"  → PUT /space/{space_id}  (reconcile statuses/features)")
            client.put(f"/space/{space_id}", plan.update_space_body)
            time.sleep(0.3)

    # 2. Lists
    for name in plan.lists_create:
        typer.echo(f'  → POST /space/{space_id}/list  (creating "{name}")')
        created = create_folderless_list(client, space_id, name)
        id_map["list_id_by_name"][name] = created["id"]
        time.sleep(0.2)

    # Cache ids for lists that already existed
    for existing_list in list_folderless_lists(client, space_id):
        if existing_list["name"] in [l["name"] for l in spec.get("folderless_lists", [])]:
            id_map["list_id_by_name"].setdefault(existing_list["name"], existing_list["id"])

    # 3. Tags
    for tag in plan.tags_create:
        body: dict[str, Any] = {"tag": {"name": tag["name"]}}
        if "color" in tag:
            body["tag"]["tag_fg"] = tag["color"]
            body["tag"]["tag_bg"] = tag["color"]
        typer.echo(f'  → POST /space/{space_id}/tag  (creating "{tag["name"]}")')
        client.post(f"/space/{space_id}/tag", body)
        id_map["tag_colors"][tag["name"]] = tag.get("color")
        time.sleep(0.15)

    # 4. Custom fields — probe to cache IDs (can't create via v2)
    if plan.lists_create or plan.lists_exists:
        any_list_id = next(iter(id_map["list_id_by_name"].values()))
        for field_def in get_list_fields(client, any_list_id):
            id_map["custom_field_id_by_name"][field_def["name"]] = field_def["id"]

    # 5. Persist id map
    ID_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ID_MAP_PATH.write_text(json.dumps(id_map, indent=2, ensure_ascii=False))
    typer.echo(f"\n  Wrote {ID_MAP_PATH.relative_to(REPO_ROOT)}")

    return id_map


# ---------- CLI ----------

@app.command()
def main(
    spec: Path = typer.Option(DEFAULT_SPEC, help="Path to YAML spec"),
    apply: bool = typer.Option(False, "--apply", help="Apply without y/n prompt after dry-run"),
    check: bool = typer.Option(False, "--check", help="Dry-run only, exit"),
) -> None:
    cfg = load_config()
    team_id = cfg["clickup"]["team_id"]
    spec_data = load_spec(spec)

    with ClickUpClient() as client:
        plan = compute_plan(client, spec_data, team_id)
        typer.echo(render_plan(plan))

        if check:
            return

        if plan.total_creates == 0 and not (plan.update_space_body and plan.space_exists):
            typer.echo("\nNothing to do.")
            return

        if plan.fields_create:
            typer.echo(
                "\n⚠  Missing custom fields will NOT be created (v2 API limitation). "
                "Create them in the ClickUp UI, then re-run to cache IDs."
            )
        if plan.statuses_missing:
            typer.echo(
                "\n⚠  Missing statuses will NOT be created (v2 API limitation). "
                "Configure them in the ClickUp UI (Space settings → Statuses)."
            )

        if not apply:
            typer.echo("")
            answer = typer.prompt("Reply 'y' to apply, or 'n' to abort", default="n")
            if answer.strip().lower() != "y":
                typer.echo("Aborted.")
                raise typer.Exit(0)

        typer.echo("\nApplying…")
        apply_plan(client, plan, spec_data)
        typer.echo("\nDone.")


if __name__ == "__main__":
    app()
