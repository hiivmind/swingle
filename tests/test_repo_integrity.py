"""Repo-consistency checks: CI/authoring concerns, never invoked by a shipped skill.

These validate that *this repo's own* Markdown is internally consistent (links resolve,
provider directories are well-formed). No skill or dispatch reads this file or its logic;
it exists only for `pytest` to catch a broken cross-reference before it ships.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ID_RE = re.compile(r"^[a-z0-9-]+$")
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
    for path in (root / "README.md", root / "CLAUDE.md"):
        if path.is_file():
            paths.append(path)
    for directory in ("skills", "contracts", "providers", "references", "docs"):
        base = root / directory
        if base.is_dir():
            paths.extend(path for path in base.rglob("*.md") if path.is_file())
    return sorted(paths)


def _living_markdown(root: Path) -> list[Path]:
    return [
        path
        for path in (root / "README.md", root / "CLAUDE.md")
        if path.is_file()
    ]

OBSOLETE_LIVING_GUIDANCE = (
    "ledger init",
    "ledger append",
    ".swingle/delegate/ledger.md",
    "<root>/scripts/swingle",
    "<project>/.swingle",
    "dispatch render",
    "result extract",
    "selector program",
    "runnable recipe",
)


def _check_obsolete_living_guidance(root: Path) -> list[str]:
    findings: list[str] = []
    for path in _living_markdown(root):
        text = path.read_text(encoding="utf-8")
        for phrase in OBSOLETE_LIVING_GUIDANCE:
            if phrase in text:
                findings.append(f"{path}: obsolete guidance {phrase}")
    return findings


def _check_links(root: Path) -> list[str]:
    findings: list[str] = []
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
                            f"{path}:{number}: broken anchor #{anchor} -> {pathpart or path.name}"
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
    return findings


def _check_provider_directories(root: Path) -> list[str]:
    findings: list[str] = []
    providers = root / "providers"
    if not providers.is_dir():
        return findings
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
        dispatch_headings = sum(
            line.strip() == "## Dispatch guidance"
            for line in note_path.read_text().splitlines()
        )
        if dispatch_headings != 1:
            findings.append(
                f"{note_path}: expected exactly one ## Dispatch guidance heading "
                f"(found {dispatch_headings})"
            )
    return findings


def write_note(root: Path, body: str = "# Alpha provider notes\n") -> Path:
    path = root / "providers" / "alpha" / "pack.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def test_dispatch_guidance_heading_is_required_exactly_once(tmp_path):
    write_note(tmp_path, "# Alpha provider notes\n")
    findings = _check_provider_directories(tmp_path)
    assert any("exactly one ## Dispatch guidance heading" in finding for finding in findings)

    write_note(
        tmp_path,
        "# Alpha provider notes\n\n## Dispatch guidance\n\n## Dispatch guidance\n",
    )
    findings = _check_provider_directories(tmp_path)
    assert any("exactly one ## Dispatch guidance heading" in finding for finding in findings)

    write_note(tmp_path, "# Alpha provider notes\n\n## Dispatch guidance\n")
    assert _check_provider_directories(tmp_path) == []


def test_free_form_note_has_no_findings(tmp_path):
    write_note(tmp_path, """# Alpha provider notes

## Dispatch guidance

Whatever shape the author chooses: prose, one table, several tables under
different headings. Nothing here parses the content back out.
""")
    assert _check_provider_directories(tmp_path) == []


def test_missing_provider_note_is_a_finding(tmp_path):
    (tmp_path / "providers" / "alpha").mkdir(parents=True)

    findings = _check_provider_directories(tmp_path)

    assert any("missing provider note" in finding for finding in findings)


def test_provider_directory_rejects_certification_assets(tmp_path):
    write_note(tmp_path)
    (tmp_path / "providers" / "alpha" / "models.yaml").write_text("models: []\n")

    findings = _check_provider_directories(tmp_path)

    assert any("unexpected provider asset" in finding for finding in findings)


def test_broken_relative_link_is_a_finding(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "one.md").write_text("[missing](nowhere.md)\n")

    findings = _check_links(tmp_path)

    assert any("broken link" in finding for finding in findings)


def test_this_repos_provider_directories_are_well_formed():
    assert _check_provider_directories(ROOT) == []


def test_this_repos_owned_markdown_links_resolve():
    assert _check_links(ROOT) == []
def test_owned_markdown_includes_repository_documents():
    owned = set(_owned_markdown(ROOT))
    assert {ROOT / "README.md", ROOT / "CLAUDE.md"} <= owned
    assert any(path.parent == ROOT / "references" for path in owned)
    assert any(path.parent == ROOT / "docs" for path in owned)


def test_this_repos_living_documents_have_no_obsolete_guidance():
    assert _check_obsolete_living_guidance(ROOT) == []
