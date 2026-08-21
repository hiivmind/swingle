from __future__ import annotations

from pathlib import Path
import re

TITLE_RE = re.compile(r"^# (.+) gotchas$")
PROVIDER_ID_RE = re.compile(r"^[a-z0-9-]+$")
CLI_RE = re.compile(r"^CLI: `([a-z0-9-]+)`$")
TABLE_HEADER = "| Failure signature | Impact | Recovery | Evidence |"
TABLE_RULE = "| --- | --- | --- | --- |"


def _table_cells(line: str) -> tuple[str, ...]:
    if not line.startswith("|") or not line.endswith("|"):
        raise ValueError("gotcha row must start and end with |")
    return tuple(cell.strip() for cell in line[1:-1].split("|"))


def check_provider_note(path: Path) -> list[str]:
    """Validate one provider gotcha-note's structure; return findings (empty = valid).

    Authoring/CI integrity only. The LLM reads the note as Markdown on the
    healthy delegation path; nothing here parses a value back out for it.
    """
    provider_id = path.parent.name
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        return [f"{path}: unreadable provider note ({error})"]

    if not lines:
        return [f"{path}: empty provider note"]

    findings: list[str] = []

    def bad(message: str) -> None:
        findings.append(f"{path}: {message}")

    title = TITLE_RE.fullmatch(lines[0])
    if title is None:
        bad("first line must be '# <Provider> gotchas'")
    else:
        heading_id = re.sub(r"[^a-z0-9]+", "-", title.group(1).lower()).strip("-")
        if heading_id != provider_id:
            bad(f"provider heading does not match directory {provider_id}")

    if len(lines) < 6:
        bad("incomplete gotcha-note preamble")
        return findings

    if lines[1] != "":
        bad("expected one blank line after title")
    cli_match = CLI_RE.fullmatch(lines[2])
    if cli_match is None:
        bad("expected one CLI identity after title")
    elif cli_match.group(1) != provider_id:
        bad("CLI identity must match provider directory")
    if lines[3] != "":
        bad("expected one blank line after CLI identity")
    if lines[4] != TABLE_HEADER:
        bad("expected the gotcha-table columns")
    if lines[5] != TABLE_RULE:
        bad("invalid gotcha-table separator")

    for number, line in enumerate(lines[6:], 7):
        if not line.strip():
            continue
        if line in (TABLE_HEADER, TABLE_RULE):
            bad(f"{number}: unexpected gotcha-table preamble line")
            continue
        try:
            cells = _table_cells(line)
        except ValueError:
            bad(f"{number}: invalid gotcha row")
            continue
        if len(cells) != 4 or any(not cell for cell in cells):
            bad(f"{number}: invalid gotcha row")

    return findings


def discover_provider_ids(root: Path) -> set[str]:
    return {
        path.name
        for path in (root / "providers").iterdir()
        if path.is_dir() and PROVIDER_ID_RE.fullmatch(path.name)
    }