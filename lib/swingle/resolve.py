"""Model resolution: layered models.yaml walk, roles table, candidate ordering.

Extracted verbatim from the former scripts/validate-packs (stdlib only).
"""

import os
from pathlib import Path

from .report import find
from .packs import parse_models_yaml, check_rows, TIERS, LANES, ELIGIBLE


def resolve_models(provider_id, root, project):
    """Layered models.yaml walk (spec 2026-07-24): env -> project -> user -> default.
    First file found is the whole table; a found-but-malformed file is a STOP, never
    a fall-through."""
    env_dir = os.environ.get("SWINGLE_MODELS")
    if env_dir and not Path(env_dir).is_dir():
        find(f"SWINGLE_MODELS set but not a readable directory: {env_dir}")
        return None, None, []
    layers = []
    if env_dir:
        layers.append(("env", Path(env_dir) / f"{provider_id}.yaml"))
    if project:
        layers.append(
            ("project", Path(project) / ".swingle" / "models" / f"{provider_id}.yaml")
        )
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    layers.append(("user", Path(xdg) / "swingle" / "models" / f"{provider_id}.yaml"))
    layers.append(("default", root / "providers" / provider_id / "models.yaml"))
    for layer, path in layers:
        if path.exists():
            rows = parse_models_yaml(path, provider_id)
            check_rows(f"{path}", rows)
            return layer, path, rows
    return None, None, []


def parse_roles(root):
    roles, path = {}, root / "core" / "roles.md"
    if not path.exists():
        find(f"{path}: missing")
        return roles
    for line in path.read_text().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[1] in TIERS and cells[2] in LANES - {"any"}:
            roles[cells[0].lower()] = (cells[1], cells[2])
    return roles


def candidate_order(rows, tier, lane, excluded):
    eligible = [
        row
        for row in rows
        if row["status"] in ELIGIBLE and row["model"] not in excluded
    ]
    exact = sorted(
        (row for row in eligible if (row["tier"], row["lane"]) == (tier, lane)),
        key=lambda row: row["prio"],
    )
    any_lane = sorted(
        (row for row in eligible if (row["tier"], row["lane"]) == (tier, "any")),
        key=lambda row: row["prio"],
    )
    return exact + any_lane


def run_resolve(root, rows_by_id, role_arg, provider, project, excluded):
    role = role_arg.lower()
    roles = parse_roles(root)
    tier_lane = next((value for key, value in roles.items() if role in key), None)
    if not tier_lane:
        find(f"unknown role: {role}")
    elif provider not in rows_by_id:
        find(f"unknown provider: {provider}")
    else:
        layer, layer_path, rows = resolve_models(provider, root, project)
        if layer_path is not None:
            print(f"layer: {layer} path={layer_path.resolve()}")
        order = candidate_order(rows, *tier_lane, excluded.get(provider, set()))
        if order:
            print(
                f"{role} -> {tier_lane} -> {order[0]['model']} (P{order[0]['prio']}, {order[0]['status']}); fallback order: {', '.join(row['model'] for row in order)}"
            )
        elif layer in ("env", "project", "user"):
            find(
                f"no eligible model for {tier_lane} in {provider} — override at {layer_path} does not cover {tier_lane}"
            )
        else:
            find(f"no eligible model for {tier_lane} in {provider}")
