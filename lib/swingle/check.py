from __future__ import annotations

from pathlib import Path
import re

from .providers import PROVIDER_ID_RE, load_provider_note

LINK_RE = re.compile(r"\]\(([^)]+)\)")
CONTRACT_PATH_RE = re.compile(r"(?:<root>/)?contracts/([A-Za-z0-9_.-]+\.md)")
CONTRACT_NAME_RE = re.compile(r"\b([a-z][A-Za-z0-9_-]*-contract\.md)\b")


def _heading_slugs(text: str) -> set[str]:
    slugs: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"#{1,6}\s+(.*)", line)
        if match:
            heading = re.sub(r"[^\w\s-]", "", match.group(1).strip().lower())
            slugs.add(re.sub(r"\s+", "-", heading))
    return slugs


def _owned_markdown(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in ("skills", "contracts", "providers"):
        base = root / directory
        if base.is_dir():
            paths.extend(path for path in base.rglob("*.md") if path.is_file())
    return sorted(paths)


def _check_links(root: Path, findings: list[str]) -> None:
    slug_cache: dict[Path, set[str] | None] = {}

    def slugs_for(path: Path) -> set[str] | None:
        if path not in slug_cache:
            if not path.exists() or not path.is_file():
                slug_cache[path] = None
            else:
                try:
                    slug_cache[path] = _heading_slugs(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError):
                    slug_cache[path] = None
        return slug_cache[path]

    for path in _owned_markdown(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            findings.append(f"{path}: unreadable documentation ({error})")
            continue
        for number, line in enumerate(lines, 1):
            for target in LINK_RE.findall(line):
                target = target.strip()
                if target.startswith(("http://", "https://", "/", "mailto:")):
                    continue
                pathpart, _, anchor = target.partition("#")
                destination = path if not pathpart else (path.parent / pathpart)
                if pathpart and not destination.exists():
                    findings.append(f"{path}:{number}: broken link {target}")
                    continue
                if anchor and destination.suffix == ".md":
                    known = slugs_for(destination)
                    if known is not None and anchor not in known:
                        findings.append(
                            f"{path}:{number}: broken anchor #{anchor} → {pathpart or path.name}"
                        )

            for match in CONTRACT_PATH_RE.finditer(line):
                contract = root / "contracts" / match.group(1)
                if not contract.is_file():
                    findings.append(
                        f"{path}:{number}: broken contract reference {match.group(1)}"
                    )
            for match in CONTRACT_NAME_RE.finditer(line):
                contract = root / "contracts" / match.group(1)
                if not contract.is_file():
                    findings.append(
                        f"{path}:{number}: broken contract reference {match.group(1)}"
                    )


def check_repository(root: Path) -> list[str]:
    root = Path(root)
    findings: list[str] = []
    providers = root / "providers"
    if providers.is_dir():
        for provider in sorted(path for path in providers.iterdir() if path.is_dir()):
            if not PROVIDER_ID_RE.fullmatch(provider.name):
                findings.append(f"{provider}: invalid provider id")
            for asset in sorted(provider.iterdir()):
                if asset.name != "pack.md":
                    findings.append(f"{asset}: unexpected provider asset")
            note_path = provider / "pack.md"
            if not note_path.is_file():
                findings.append(f"{note_path}: missing provider note")
                continue
            try:
                note = load_provider_note(note_path)
            except (OSError, UnicodeError, ValueError) as error:
                findings.append(str(error))
                continue
            heading_text = note_path.read_text(encoding="utf-8").splitlines()[0][2:-7]
            heading_id = re.sub(r"[^a-z0-9]+", "-", heading_text.lower()).strip("-")
            if heading_id != provider.name:
                findings.append(
                    f"{note_path}: provider heading does not match directory {provider.name}"
                )
            if note.cli != provider.name:
                findings.append(
                    f"{note_path}: CLI identity does not match directory {provider.name}"
                )

    _check_links(root, findings)
    return findings
