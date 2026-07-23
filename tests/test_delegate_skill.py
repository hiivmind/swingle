import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "delegate" / "SKILL.md"
YAML = ROOT / "skills" / "delegate" / "agents" / "openai.yaml"
READER = ROOT / "contracts" / "reader-contract.md"

def _model_ids():
    """Every model id declared in any provider's models.md Resolvable table."""
    ids = set()
    for models in (ROOT / "providers").glob("*/models.md"):
        for line in models.read_text().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Tier | Lane | Priority | Model id | Status | ...
            if len(cells) >= 5 and cells[2].isdigit():
                ids.add(cells[3].strip("`"))
    return ids

def _pack_clis():
    """The validated cli name from every provider pack manifest."""
    clis = set()
    for pack in (ROOT / "providers").glob("*/pack.md"):
        m = re.search(r"^cli: (\S+)", pack.read_text(), re.M)
        if m:
            clis.add(m.group(1))
    return clis

def test_skill_exists_with_frontmatter():
    text = SKILL.read_text()
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    assert re.search(r"^name: delegate$", front, re.M)
    assert re.search(r"^description: .{40,}", front, re.M)

def _skill_files():
    """Every skill-authored file whose content the purity boundary binds."""
    files = list((ROOT / "skills").glob("*/SKILL.md"))
    files += [p for p in (ROOT / "skills").glob("*/agents/*.yaml")]
    return files

def test_purity_no_model_ids_in_any_skill():
    ids = _model_ids()
    assert ids, "expected provider model tables to parse"
    for skill in _skill_files():
        text = skill.read_text()
        leaked = {m for m in ids if m in text}
        assert not leaked, f"{skill}: model ids leaked: {leaked}"

# Leading markdown furniture that can precede a command on a line: list bullets,
# ordered-list markers, blockquotes, and shell prompts.
_MARKER = re.compile(r"^(?:[-*+>]\s+|\d+[.)]\s+|[$#]\s+)")

def _cli_invocation(line, clis):
    """A command-shaped use of a pack cli, or None.

    Command-shaped means: a pack cli name in leading position (after stripping
    markdown/prompt furniture and code-span backticks) carrying at least one flag
    argument. Requiring a flag is what separates a real invocation
    ("agy --model X ...", "- codex exec --json") from prose that merely opens with
    the name ("codex is the default when active").
    """
    stripped = line.strip()
    while True:
        m = _MARKER.match(stripped)
        if not m:
            break
        stripped = stripped[m.end():]
    stripped = stripped.strip("`").strip()
    parts = stripped.split()
    if len(parts) < 2 or parts[0] not in clis:
        return None
    if not any(p.startswith("-") for p in parts[1:]):
        return None
    return stripped

def test_purity_no_cli_invocations_anywhere():
    # Invocation strings live in provider packs only. No line ANYWHERE in a skill
    # (fenced or prose) may be a command-shaped use of a pack cli. Prose mentions
    # like "(codex/opencode/agy)", "via codex", or "codex is active" do not match;
    # bullets and shell prompts ("- codex exec --json", "$ agy -p ...") do.
    clis = _pack_clis()
    assert clis, "expected pack manifests to declare cli names"
    for skill in _skill_files():
        for n, line in enumerate(skill.read_text().splitlines(), 1):
            leaked = _cli_invocation(line, clis)
            assert not leaked, f"{skill}:{n}: cli invocation leaked into skill: {leaked}"

def test_cli_invocation_detector_discriminates():
    # Guards the heuristic itself: the detector must fire on real invocations
    # (including ones dressed in markdown) and stay silent on prose.
    clis = {"codex", "agy", "opencode"}
    for bad in ("agy --model X -p \"t\"", "- codex exec --json", "$ agy -p 'x'",
                "1. opencode run --model m", "`codex exec --cd .`", "> agy --version"):
        assert _cli_invocation(bad, clis), f"should have flagged: {bad}"
    for ok in ("codex is active", "via codex", "(codex/opencode/agy)",
               "- codex, opencode, and agy are the packs", "the agy pack", "codex"):
        assert _cli_invocation(ok, clis) is None, f"false positive: {ok}"

def test_superpowers_operational_independence():
    # Normative rule: no operational dependency or invocation. The skill NAMES
    # superpowers and its workspace exactly once each — in the negative disclaimer.
    text = SKILL.read_text()
    assert "no superpowers dependency" in text.lower()
    assert text.count("scripts/sdd-workspace") == 1
    assert text.count(".superpowers/sdd") == 1

def test_root_resolution_stated():
    assert "grandparent" in SKILL.read_text()

def test_status_vocabulary_present():
    text = SKILL.read_text()
    for status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
        assert status in text

def test_openai_yaml_disables_implicit_invocation():
    assert "allow_implicit_invocation: false" in YAML.read_text()

def test_reader_contract_protocol():
    text = READER.read_text()
    for token in ("STATUS:", "ANSWER:", "REPORT:", "NEEDS_CONTEXT", "Read-only",
                  "cannot write files"):
        assert token in text
