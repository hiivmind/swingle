"""Manifest + models parsing/validation primitives and the pack-load bootstrap.

Extracted verbatim from the former scripts/validate-packs (stdlib only).
"""

import json
import re
from pathlib import Path

from .report import find

REQ = [
    "schema-version",
    "id",
    "cli",
    "verified-version",
    "version-argv",
    "resume-argv",
    "session-source",
    "stall-signal",
    "sandbox",
]
OPTIONAL = {
    "fork-flag",
    "session-list-argv",
    "readiness-argv",
    "readiness-timeout-seconds",
    "report-transport",
    "list-models-argv",
}
ENUMS = {
    "session-source": {"session-list", "exec-output", "conversation-id"},
    "stall-signal": {"log-age", "process+print-timeout"},
    "sandbox": {"enforced", "none"},
    "report-transport": {"report-file", "captured-output"},
}
INTERPRETERS = {
    "sh",
    "bash",
    "dash",
    "zsh",
    "ksh",
    "env",
    "python",
    "python3",
    "perl",
    "ruby",
    "node",
    "deno",
    "bun",
    "npx",
    "uv",
    "uvx",
    "xargs",
    "nice",
    "timeout",
    "sudo",
    "doas",
}
TIERS, LANES = {"cheapest", "standard", "most-capable"}, {"implement", "review", "any"}
STATUSES, ELIGIBLE = (
    {"verified", "experimental", "unavailable", "superseded", "rejected"},
    {"verified", "experimental"},
)
NAME_RE, META_RE, VER_RE = (
    re.compile(r"^[a-z0-9-]+$"),
    re.compile(r"[;|&<>$]"),
    re.compile(r"^[0-9]+(?:\.[0-9]+)+$"),
)
VERSION_TOKEN_RE = re.compile(r"[0-9]+(?:\.[0-9]+)+\S*")
VERSION_FILE_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)+\.md$")
SHARD_FILE_RE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])\.md$")
ENTRY_DATE_RE = re.compile(r"^## ([0-9]{4}-[0-9]{2}-[0-9]{2})")
HEADER_RE = re.compile(
    r"^> (?:Verified: (?P<vcli>\S+) (?P<vver>[0-9]+(?:\.[0-9]+)+), round [0-9]{4}-[0-9]{2}-[0-9]{2}\."
    r"|Distilled(?: \(log-evidenced; never round-stamped\))?: (?P<dcli>\S+) (?P<dver>[0-9]+(?:\.[0-9]+)+) truth, assembled .+)$"
)


def version_key(v):
    return tuple(int(x) for x in v.split("."))


def version_cmp_key(v, width):
    t = version_key(v)
    return t + (0,) * (width - len(t))


def registry_path_for(pack_dir, verified_version):
    if not (isinstance(verified_version, str) and VER_RE.fullmatch(verified_version)):
        find(
            f"{pack_dir / 'pack.md'}: verified-version must be dotted numeric before registry resolution: {verified_version!r}"
        )
        return None
    vdir = pack_dir / "versions"
    if vdir.is_symlink():
        find(f"{vdir}: versions/ must not be a symlink")
        return None
    path = vdir / f"{verified_version}.md"
    if path.is_symlink():
        find(f"{path}: registry file must not be a symlink")
        return None
    return path


LINE_RE = re.compile(r'^([a-z-]+):\s*(".*"|\[.*\]|[^"\[\s][^"]*)?\s*(#.*)?$')


def parse_front_matter(path):
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "---":
        find(f"{path}: no front-matter")
        return {}
    fm, closed = {}, False
    for n, line in enumerate(lines[1:], 2):
        if line == "---":
            closed = True
            break
        m = LINE_RE.match(line)
        if not m or m.group(2) is None:
            find(f"{path}:{n}: grammar violation: {line!r}")
            continue
        key, raw = m.group(1), m.group(2).strip()
        if key in fm:
            find(f"{path}:{n}: duplicate key {key}")
        if raw.startswith("["):
            if "'" in raw:
                find(f"{path}:{n}: grammar violation: single quotes in array")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                find(f"{path}:{n}: invalid JSON array for {key}")
                value = None
            if isinstance(value, list) and not value:
                find(f"{path}: {key} is an empty argv array")
            fm[key] = value if isinstance(value, list) else []
        else:
            fm[key] = raw.strip('"')
    if not closed:
        find(f"{path}: unterminated front-matter")
    return fm


def check_manifest(pack):
    fm, path = parse_front_matter(pack / "pack.md"), pack / "pack.md"
    for key in REQ:
        if key not in fm:
            find(f"{path}: missing field {key}")
    for key in fm:
        if key not in REQ and key not in OPTIONAL and key != "detect":
            find(f"{path}: unknown field {key}")
    if str(fm.get("schema-version", "")) != "1":
        find(f"{path}: unknown schema-version {fm.get('schema-version')}")
    if "detect" in fm:
        find(f"{path}: shell 'detect' forbidden — use *-argv arrays")
    for key, allowed in ENUMS.items():
        if key in fm and fm[key] not in allowed:
            find(f"{path}: bad enum {key}={fm[key]}")
    for key in ("id", "cli"):
        if key in fm and not NAME_RE.match(str(fm[key])):
            find(f"{path}: {key} fails [a-z0-9-]+")
    if fm.get("cli") in INTERPRETERS:
        find(f"{path}: cli is an interpreter/launcher: {fm['cli']}")
    if fm.get("id") and fm["id"] != pack.name:
        find(f"{path}: id != dirname")
    for key, value in fm.items():
        if not key.endswith("-argv"):
            continue
        if not isinstance(value, list) or not all(
            isinstance(token, str) for token in value
        ):
            find(f"{path}: {key} must be a JSON array of strings")
            continue
        if not value:
            find(f"{path}: {key} is an empty argv array")
            continue
        if fm.get("cli") and value[0] != fm["cli"]:
            find(f"{path}: {key} argv[0] must equal cli ({value[0]} != {fm['cli']})")
        for token in value[1:]:
            if META_RE.search(token):
                find(f"{path}: {key} shell metacharacter: {token}")
            if token.startswith("/"):
                find(f"{path}: {key} absolute path: {token}")
            for placeholder in re.findall(r"\{([a-z_]+)\}", token):
                if placeholder != "session_id":
                    find(f"{path}: unknown placeholder {{{placeholder}}}")
    if fm.get("session-source") == "session-list" and "session-list-argv" not in fm:
        find(f"{path}: session-list-argv required for session-source: session-list")
    return fm


MODEL_ROW_KEYS = {"tier", "lane", "priority", "model", "status", "pricing", "rationale"}
MODEL_ROW_REQ = ("tier", "lane", "priority", "model", "status")
Y_TOP_RE = re.compile(r"^([a-z]+):\s*(.*)$")
Y_FIRST_RE = re.compile(r"^  - ([a-z]+):\s*(.*)$")
Y_CONT_RE = re.compile(r"^    ([a-z]+):\s*(.*)$")


def yaml_scalar(path, n, raw):
    """One restricted-grammar scalar: bare or double-quoted, optional trailing comment."""
    raw = raw.strip()
    if raw.startswith("'"):
        find(
            f"{path}:{n}: single-quoted scalars not supported — use double quotes or bare"
        )
        return None
    if raw.startswith('"'):
        end = raw.find('"', 1)
        if end == -1:
            find(f"{path}:{n}: unterminated quote")
            return None
        trailing = raw[end + 1 :].strip()
        if trailing and not trailing.startswith("#"):
            find(f"{path}:{n}: trailing content after quote")
            return None
        return raw[1:end]
    return raw.split("#", 1)[0].strip()


def parse_models_yaml(path, provider_id):
    """Restricted-YAML models file (spec 2026-07-24): flat header + fixed-shape row list."""
    header, raw_rows, current = {}, [], None
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m_first, m_cont = Y_FIRST_RE.match(line), Y_CONT_RE.match(line)
        m_top = Y_TOP_RE.match(line) if not line.startswith(" ") else None
        if m_first:
            if current is not None:
                raw_rows.append(current)
            current, key, value = (
                {},
                m_first.group(1),
                yaml_scalar(path, n, m_first.group(2)),
            )
        elif m_cont and current is not None:
            key, value = m_cont.group(1), yaml_scalar(path, n, m_cont.group(2))
        elif m_top:
            key, raw = m_top.group(1), m_top.group(2)
            if key == "models":
                bare = raw.split("#", 1)[0].strip()
                if bare not in ("", "[]"):
                    find(f"{path}:{n}: models must be a block list or []")
                continue
            if key in header:
                find(f"{path}:{n}: duplicate key {key}")
            header[key] = yaml_scalar(path, n, raw)
            continue
        else:
            find(f"{path}:{n}: grammar violation: {line!r}")
            continue
        if key not in MODEL_ROW_KEYS:
            find(f"{path}:{n}: unknown row key {key}")
            continue
        if key in current:
            find(f"{path}:{n}: duplicate row key {key}")
            continue
        current[key] = value
    if current is not None:
        raw_rows.append(current)
    if str(header.get("schema")) != "1":
        find(f"{path}: schema must be 1 (got {header.get('schema')})")
    if header.get("provider") != provider_id:
        find(f"{path}: provider must be {provider_id} (got {header.get('provider')})")
    for key in header:
        if key not in {"schema", "provider"}:
            find(f"{path}: unknown key {key}")
    rows = []
    for row in raw_rows:
        missing = [k for k in MODEL_ROW_REQ if k not in row]
        if missing:
            find(f"{path}: row missing {' '.join(missing)}")
            continue
        if row["tier"] not in TIERS:
            find(f"{path}: bad tier {row['tier']}")
            continue
        if row["lane"] not in LANES:
            find(f"{path}: bad lane {row['lane']}")
        if row["status"] not in STATUSES:
            find(f"{path}: bad status {row['status']}")
        if not str(row["priority"]).isdigit() or int(row["priority"]) < 1:
            find(f"{path}: bad priority {row['priority']}")
        else:
            rows.append(
                {
                    "tier": row["tier"],
                    "lane": row["lane"],
                    "prio": int(row["priority"]),
                    "model": row["model"],
                    "status": row["status"],
                }
            )
    return rows


def check_rows(label, rows):
    seen = set()
    for row in rows:
        key = row["tier"], row["lane"], row["prio"]
        if key in seen:
            find(f"{label}: duplicate priority {key}")
        seen.add(key)
    for tier_lane in {(row["tier"], row["lane"]) for row in rows}:
        if not any(
            row["prio"] == 1 for row in rows if (row["tier"], row["lane"]) == tier_lane
        ):
            find(f"{label}: {tier_lane} has no priority 1 row")


def check_md_has_no_eligible_rows(pack):
    """Eligible-row guard: once models.yaml is the table of record, models.md may keep
    prose and documentary tables but never an eligible-status tier row (table rows only —
    prose mentions are out of scope by design)."""
    for n, line in enumerate((pack / "models.md").read_text().splitlines(), 1):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if (
            len(cells) >= 5
            and line.lstrip().startswith("|")
            and cells[0] in TIERS
            and cells[4] in ELIGIBLE
        ):
            find(
                f"{pack}/models.md:{n}: eligible-row guard: eligible status row belongs in models.yaml"
            )


def load_packs(root):
    """Discover packs, validate manifests + model tables. Returns (manifests, rows_by_id, packs)."""
    packs = (
        sorted((root / "providers").glob("*/")) if (root / "providers").exists() else []
    )
    for pack in packs:
        if not (pack / "pack.md").exists():
            find(f"{pack}: missing pack.md")
    packs = [pack for pack in packs if (pack / "pack.md").exists()]
    if not packs:
        find(f"{root}: no packs found")
    manifests, rows_by_id = {}, {}
    for pack in packs:
        manifests[pack.name] = check_manifest(pack)
        for filename in ("models.yaml", "models.md", "verification-log.md"):
            if not (pack / filename).exists():
                find(f"{pack}: missing {filename}")
        if (pack / "models.yaml").exists():
            rows = parse_models_yaml(pack / "models.yaml", pack.name)
            check_rows(f"{pack}/models.yaml", rows)
            rows_by_id[pack.name] = rows
            if (pack / "models.md").exists():
                check_md_has_no_eligible_rows(pack)
    return manifests, rows_by_id, packs
