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
    if len(lines) < 6:
        raise ValueError(f"{path}: incomplete gotcha-note preamble")
    if lines[1] != "":
        raise ValueError(f"{path}: expected one blank line after title")
    cli_match = CLI_RE.fullmatch(lines[2])
    if cli_match is None:
        raise ValueError(f"{path}: expected one CLI identity after title")
    if lines[3] != "":
        raise ValueError(f"{path}: expected one blank line after CLI identity")
    if lines[4] != TABLE_HEADER:
        raise ValueError(f"{path}: expected the gotcha-table columns")
    if lines[5] != TABLE_RULE:
        raise ValueError(f"{path}: invalid gotcha-table separator")
    cli = cli_match.group(1)
    if cli != path.parent.name:
        raise ValueError(f"{path}: CLI identity must match provider directory")
    gotchas = []
    for number, line in enumerate(lines[6:], 7):
        if not line.strip():
            continue
        if line in (TABLE_HEADER, TABLE_RULE):
            raise ValueError(f"{path}:{number}: unexpected gotcha-table preamble line")
        cells = _table_cells(line)
        if len(cells) != 4 or any(not cell for cell in cells):
            raise ValueError(f"{path}:{number}: invalid gotcha row")
        gotchas.append(Gotcha(*cells))
    return ProviderNote(path.parent.name, cli, tuple(gotchas))


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
