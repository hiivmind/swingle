from dataclasses import dataclass
from pathlib import Path
import re

TITLE_RE = re.compile(r"^# .+ gotchas$")
PROVIDER_ID_RE = re.compile(r"^[a-z0-9-]+$")
CLI_RE = re.compile(r"^CLI: `([a-z0-9-]+)`$")
TABLE_HEADER = "| Failure signature | Impact | Recovery | Evidence |"
TABLE_RULE = "| --- | --- | --- | --- |"


@dataclass(frozen=True)
class Gotcha:
    signature: str
    impact: str
    recovery: str
    evidence: str


@dataclass(frozen=True)
class ProviderNote:
    provider_id: str
    cli: str
    gotchas: tuple[Gotcha, ...]


def _table_cells(line: str) -> tuple[str, ...]:
    if not line.startswith("|") or not line.endswith("|"):
        raise ValueError("gotcha row must start and end with |")
    return tuple(cell.strip() for cell in line[1:-1].split("|"))


def load_provider_note(path: Path) -> ProviderNote:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not TITLE_RE.fullmatch(lines[0]):
        raise ValueError(f"{path}: first line must be '# <Provider> gotchas'")
    cli_lines = [CLI_RE.fullmatch(line) for line in lines]
    cli_values = [match.group(1) for match in cli_lines if match]
    if len(cli_values) != 1:
        raise ValueError(f"{path}: expected one CLI identity")
    if cli_values[0] != path.parent.name:
        raise ValueError(f"{path}: CLI identity must match provider directory")
    if lines.count(TABLE_HEADER) != 1:
        raise ValueError(f"{path}: expected the gotcha-table columns")
    header = lines.index(TABLE_HEADER)
    if header + 1 >= len(lines) or lines[header + 1] != TABLE_RULE:
        raise ValueError(f"{path}: invalid gotcha-table separator")
    gotchas = []
    for number, line in enumerate(lines[header + 2:], header + 3):
        if not line.strip():
            continue
        cells = _table_cells(line)
        if len(cells) != 4 or any(not cell for cell in cells):
            raise ValueError(f"{path}:{number}: invalid gotcha row")
        gotchas.append(Gotcha(*cells))
    return ProviderNote(path.parent.name, cli_values[0], tuple(gotchas))


def load_provider_notes(root: Path) -> dict[str, ProviderNote]:
    return {
        path.parent.name: load_provider_note(path)
        for path in sorted((root / "providers").glob("*/pack.md"))
    }


def discover_provider_ids(root: Path) -> set[str]:
    return {
        path.name
        for path in (root / "providers").iterdir()
        if path.is_dir() and PROVIDER_ID_RE.fullmatch(path.name)
    }
